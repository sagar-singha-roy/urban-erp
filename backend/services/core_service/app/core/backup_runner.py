"""Runs real pg_dump backups and pg_restore recoveries into new scratch databases."""
import asyncio
import datetime
import hashlib
import logging
import os
import uuid
from pathlib import Path
from typing import Coroutine, List, Set, Tuple

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db.models import BackupJobModel, RestoreJobModel
from app.db.session import AsyncWriteSessionLocal

logger = logging.getLogger(__name__)

_running: Set[asyncio.Task] = set()


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
            size = path.stat().st_size
            job.database_name = database
            job.file_size_bytes = size
            job.file_size_formatted = _format_size(size)
            job.storage_location = str(path)
            job.checksum_sha256 = await asyncio.to_thread(_sha256, path)
            job.execution_status = "Completed"
            job.verification_status = "File Readable"
            job.verification_result = "pg_restore read the archive contents. Run a restore to prove recovery."
        except Exception as exc:
            logger.exception("Backup %s failed", job.job_id)
            job.execution_status = "Failed"
            job.verification_status = "Not Verified"
            job.verification_result = str(exc)[:255]
        now = datetime.datetime.utcnow()
        job.completion_time = now
        job.duration_seconds = int((now - started).total_seconds())
        await db.commit()


async def run_restore(restore_pk: str) -> None:
    """Restores into a new database only. Existing databases are never overwritten."""
    started = datetime.datetime.utcnow()
    async with AsyncWriteSessionLocal() as db:
        restore = await db.scalar(select(RestoreJobModel).where(RestoreJobModel.id == restore_pk))
        if not restore:
            return
        try:
            job = await db.scalar(select(BackupJobModel).where(BackupJobModel.job_id == restore.source_backup_id))
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
            restore.target_database = target
            code, error = await _run("pg_restore", *args, "--no-owner", "--no-privileges", "-d", target, str(path), env=env)
            # pg_restore exits non-zero on warnings too, so report them rather than claim a clean restore.
            restore.execution_status = "Completed" if code == 0 else "Completed With Errors"
            restore.restore_destination = f"Scratch database {target}" if code == 0 else f"{target}: {error[:200]}"
        except Exception as exc:
            logger.exception("Restore %s failed", restore_pk)
            restore.execution_status = "Failed"
            restore.restore_destination = str(exc)[:255]
        restore.duration_seconds = int((datetime.datetime.utcnow() - started).total_seconds())
        await db.commit()
