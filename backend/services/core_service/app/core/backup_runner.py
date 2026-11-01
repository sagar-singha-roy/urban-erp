"""Runs pg_dump backups, schedules, encrypted storage, restores and recovery drills."""
import asyncio
import base64
import datetime
import hashlib
import logging
import os
import uuid
from pathlib import Path
from typing import Coroutine, List, Optional, Set, Tuple

from cryptography.fernet import Fernet
from sqlalchemy import func, null, select, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.retention import enforce_audit_retention
from app.db.models import BackupJobModel, BackupPolicyModel, DrillExecutionModel, RestoreJobModel
from app.db.session import AsyncWriteSessionLocal

logger = logging.getLogger(__name__)

_running: Set[asyncio.Task] = set()
FREQUENCY_HOURS = {"Hourly": 1, "Daily": 24, "Weekly": 24 * 7, "Monthly": 24 * 30}
RETENTION_UNIT_DAYS = {"Days": 1, "Months": 30, "Years": 365}
SCHEDULER_LOCK_ID = 7214001
CHUNK_BYTES = 1024 * 1024


def _fernet() -> Optional[Fernet]:
    key = settings.BACKUP_ENCRYPTION_KEY
    if not key:
        return None
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest()))


def _encrypt_file(source: Path, target: Path, fernet: Fernet) -> None:
    with source.open("rb") as reader, target.open("wb") as writer:
        for chunk in iter(lambda: reader.read(CHUNK_BYTES), b""):
            writer.write(fernet.encrypt(chunk) + b"\n")
    target.chmod(0o600)


def _decrypt_file(source: Path, target: Path, fernet: Fernet) -> None:
    with source.open("rb") as reader, target.open("wb") as writer:
        for line in reader:
            writer.write(fernet.decrypt(line.strip()))
    target.chmod(0o600)


def new_backup_job(policy: BackupPolicyModel, job_id: str, now: datetime.datetime) -> BackupJobModel:
    database = make_url(settings.admin_db_url)
    return BackupJobModel(
        job_id=job_id,
        policy_code=policy.policy_code,
        policy_name=policy.policy_name,
        environment=settings.ENVIRONMENT,
        database_cluster=database.host or "",
        database_name=database.database or "",
        backup_type="Full Backup (pg_dump)",
        execution_status="Running",
        start_time=now,
        completion_time=null(),
        duration_seconds=0,
        file_size_bytes=0,
        file_size_formatted="0 B",
        storage_location="Not written yet",
        checksum_sha256="",
        verification_status="Not Verified",
        verification_result="Backup in progress.",
    )


def start_background(work: Coroutine) -> None:
    task = asyncio.create_task(work)
    _running.add(task)
    task.add_done_callback(_running.discard)


def _connection() -> Tuple[List[str], dict, str]:
    url = make_url(settings.admin_db_url)
    args = ["-h", url.host or "localhost", "-p", str(url.port or 5432), "-U", url.username or ""]
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    return args, env, url.database or ""


async def _run(*command: str, env: dict) -> Tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        *command, env=env, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    return process.returncode or 0, stderr.decode("utf-8", "replace").strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


async def run_backup(job_pk: str) -> None:
    started = datetime.datetime.utcnow()
    async with AsyncWriteSessionLocal() as db:
        job = await db.scalar(select(BackupJobModel).where(BackupJobModel.id == job_pk))
        if not job:
            return
        try:
            args, env, database = _connection()
            directory = Path(settings.BACKUP_DIR).resolve()
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = directory / f"{job.job_id}.dump"
            code, error = await _run("pg_dump", *args, "-Fc", "-f", str(path), database, env=env)
            if code != 0:
                raise RuntimeError(error or f"pg_dump exited with code {code}")
            path.chmod(0o600)
            code, error = await _run("pg_restore", "--list", str(path), env=env)
            if code != 0:
                raise RuntimeError(error or "The backup file could not be read by pg_restore")
            fernet = _fernet()
            if fernet:
                encrypted = path.with_suffix(".dump.enc")
                await asyncio.to_thread(_encrypt_file, path, encrypted, fernet)
                path.unlink()
                path = encrypted
            elif not settings.is_development:
                path.unlink()
                raise RuntimeError("BACKUP_ENCRYPTION_KEY must be set, so the backup file was removed.")
            size = path.stat().st_size
            job.database_name = database
            job.file_size_bytes = size
            job.file_size_formatted = _format_size(size)
            job.storage_location = str(path)
            job.checksum_sha256 = await asyncio.to_thread(_sha256, path)
            job.execution_status = "Completed"
            job.verification_status = "File Readable"
            encryption_note = "Encrypted at rest." if fernet else "Not encrypted (development)."
            job.verification_result = f"pg_restore read the archive contents. {encryption_note} Run a restore to prove recovery."
        except Exception as exc:
            logger.exception("Backup %s failed", job.job_id)
            job.execution_status = "Failed"
            job.verification_status = "Not Verified"
            job.verification_result = str(exc)[:255]
        now = datetime.datetime.utcnow()
        job.completion_time = now
        job.duration_seconds = int((now - started).total_seconds())
        await db.commit()


async def _restore_to_scratch(db, source_backup_id: str) -> Tuple[str, int, str]:
    job = await db.scalar(select(BackupJobModel).where(BackupJobModel.job_id == source_backup_id))
    if not job or job.execution_status != "Completed":
        raise RuntimeError("The source backup is not a completed backup.")
    path = Path(job.storage_location)
    if not path.is_file():
        raise RuntimeError("The backup file is missing.")
    if await asyncio.to_thread(_sha256, path) != job.checksum_sha256:
        raise RuntimeError("The backup file failed its checksum.")
    args, env, _ = _connection()
    target = f"restore_{uuid.uuid4().hex[:12]}"
    code, error = await _run("createdb", *args, target, env=env)
    if code != 0:
        raise RuntimeError(error or "The scratch database could not be created.")
    archive = path
    plain = None
    if path.suffix == ".enc":
        fernet = _fernet()
        if not fernet:
            raise RuntimeError("BACKUP_ENCRYPTION_KEY is needed to read this backup.")
        plain = path.with_name(f"{target}.dump")
        await asyncio.to_thread(_decrypt_file, path, plain, fernet)
        archive = plain
    try:
        code, error = await _run("pg_restore", *args, "--no-owner", "--no-privileges", "-d", target, str(archive), env=env)
    finally:
        if plain:
            plain.unlink(missing_ok=True)
    return target, code, error


async def _table_count(database: str, table: str, args: List[str], env: dict) -> Optional[int]:
    process = await asyncio.create_subprocess_exec(
        "psql", *args, "-d", database, "-Atc", f"SELECT count(*) FROM {table}",
        env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await process.communicate()
    return int(stdout.strip()) if process.returncode == 0 and stdout.strip() else None


async def run_drill(drill_pk: str) -> None:
    """Restores the latest backup into a scratch database, measures it, compares row counts and removes it."""
    started = datetime.datetime.utcnow()
    async with AsyncWriteSessionLocal() as db:
        drill = await db.scalar(select(DrillExecutionModel).where(DrillExecutionModel.id == drill_pk))
        if not drill:
            return
        target = None
        args, env, source_db = _connection()
        try:
            job = await db.scalar(
                select(BackupJobModel)
                .where(BackupJobModel.execution_status == "Completed")
                .order_by(BackupJobModel.start_time.desc())
                .limit(1)
            )
            if not job:
                raise RuntimeError("No completed backup exists to restore from.")
            target, code, error = await _restore_to_scratch(db, job.job_id)
            finished = datetime.datetime.utcnow()
            matched = mismatched = 0
            for table in ("tenants", "users", "modules"):
                restored = await _table_count(target, table, args, env)
                if restored is not None and restored == await _table_count(source_db, table, args, env):
                    matched += 1
                else:
                    mismatched += 1
            rto = round((finished - started).total_seconds() / 60, 2)
            rpo = round((started - job.start_time).total_seconds() / 60, 2)
            passed = code == 0 and mismatched == 0
            drill.actual_rto_minutes = rto
            drill.actual_rpo_minutes = rpo
            drill.recovery_success_rate_pct = 100.0 if passed else 0.0
            drill.data_integrity_result = f"{matched} of {matched + mismatched} tables matched row counts"[:100]
            within = rto <= drill.expected_rto_minutes and rpo <= drill.expected_rpo_minutes
            drill.completion_status = ("Passed" if within else "Passed - SLA Missed") if passed else "Failed"
            drill.findings = f"Restored backup {job.job_id}." + (f" pg_restore reported: {error[:300]}" if code else "")
        except Exception as exc:
            logger.exception("Drill %s failed", drill_pk)
            drill.completion_status = "Failed"
            drill.recovery_success_rate_pct = 0.0
            drill.findings = str(exc)[:500]
        finally:
            if target:
                await _run("dropdb", *args, target, env=env)
        await db.commit()


async def _purge_expired_backups(db, policy: BackupPolicyModel, now: datetime.datetime) -> None:
    days = policy.retention_period * RETENTION_UNIT_DAYS.get(policy.retention_unit, 1)
    expired = (await db.scalars(
        select(BackupJobModel).where(
            BackupJobModel.policy_code == policy.policy_code,
            BackupJobModel.execution_status == "Completed",
            BackupJobModel.start_time < now - datetime.timedelta(days=days),
        )
    )).all()
    for job in expired:
        Path(job.storage_location).unlink(missing_ok=True)
        job.execution_status = "Expired"
        job.verification_result = "Removed by the policy's retention period."


async def run_due_backups() -> int:
    """Starts a backup for each active policy whose frequency has elapsed."""
    started = []
    now = datetime.datetime.utcnow()
    async with AsyncWriteSessionLocal() as db:
        # Only one worker schedules at a time.
        if not await db.scalar(text("SELECT pg_try_advisory_xact_lock(:id)"), {"id": SCHEDULER_LOCK_ID}):
            return 0
        policies = (await db.scalars(select(BackupPolicyModel).where(BackupPolicyModel.policy_status == "Active"))).all()
        for policy in policies:
            await _purge_expired_backups(db, policy, now)
            hours = FREQUENCY_HOURS.get(policy.backup_frequency)
            if not hours:
                continue
            last = await db.scalar(select(func.max(BackupJobModel.start_time)).where(BackupJobModel.policy_code == policy.policy_code))
            if (last or policy.created_at) + datetime.timedelta(hours=hours) > now:
                continue
            job = new_backup_job(policy, f"BKP-SCHED-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}", now)
            db.add(job)
            await db.flush()
            started.append(job.id)
        await db.commit()
    for job_pk in started:
        start_background(run_backup(job_pk))
    return len(started)


async def scheduler_loop() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            await run_due_backups()
            await enforce_audit_retention()
        except Exception:
            logger.exception("Scheduled maintenance failed")


async def run_restore(restore_pk: str) -> None:
    """Restores into a new database only. Existing databases are never overwritten."""
    started = datetime.datetime.utcnow()
    async with AsyncWriteSessionLocal() as db:
        restore = await db.scalar(select(RestoreJobModel).where(RestoreJobModel.id == restore_pk))
        if not restore:
            return
        try:
            target, code, error = await _restore_to_scratch(db, restore.source_backup_id)
            restore.target_database = target
            # pg_restore exits non-zero on warnings too, so report them rather than claim a clean restore.
            restore.execution_status = "Completed" if code == 0 else "Completed With Errors"
            restore.restore_destination = f"Scratch database {target}" if code == 0 else f"{target}: {error[:200]}"
        except Exception as exc:
            logger.exception("Restore %s failed", restore_pk)
            restore.execution_status = "Failed"
            restore.restore_destination = str(exc)[:255]
        restore.duration_seconds = int((datetime.datetime.utcnow() - started).total_seconds())
        await db.commit()
