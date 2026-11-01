import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, null, text

from sqlalchemy.engine import make_url

from app.core.auth import get_current_user, require_roles
from app.core.backup_runner import new_backup_job, run_backup, run_drill, run_restore, start_background
from app.core.config import settings
from app.db.session import get_db
from app.db.models import BackupPolicyModel, BackupJobModel, RestoreJobModel, DrillExecutionModel
from app.schemas.backup_dr import (
    BackupDrOverviewStats,
    BackupPolicyPayload,
    BackupPolicyResponse,
    BackupJobResponse,
    RestoreJobPayload,
    RestoreJobResponse,
    PitrWindowStatus,
    DrillExecutionPayload,
    DrillExecutionResponse,
)
from app.schemas.tenant import ApiResponse

router = APIRouter(prefix="/fleet/backup-dr", tags=["Platform Fleet & Operations - Backup & DR"], dependencies=[Depends(require_roles(["super_admin"]))])

PENDING_APPROVER = "Pending second administrator"


def _operator(user: dict) -> str:
    return str(user.get("email") or user.get("preferred_username") or user.get("sub") or "unknown")


@router.get("/stats", response_model=ApiResponse[BackupDrOverviewStats])
async def get_backup_dr_stats(db: AsyncSession = Depends(get_db)):
    # Calculate live stats
    total_bkp_res = await db.execute(select(func.count(BackupJobModel.id)))
    total_backups = total_bkp_res.scalar() or 0

    succ_bkp_res = await db.execute(
        select(func.count(BackupJobModel.id)).where(BackupJobModel.execution_status.in_(["Completed", "Verified"]))
    )
    successful_backups = succ_bkp_res.scalar() or 0

    failed_bkp_res = await db.execute(
        select(func.count(BackupJobModel.id)).where(BackupJobModel.execution_status == "Failed")
    )
    failed_backups = failed_bkp_res.scalar() or 0

    # Total stored bytes
    size_res = await db.execute(select(func.sum(BackupJobModel.file_size_bytes)))
    total_bytes = size_res.scalar() or 0
    total_tb = round(total_bytes / (1024 ** 4), 2)
    if total_tb == 0.0 and total_bytes > 0:
        total_tb = round(total_bytes / (1000 ** 4), 3)

    # Last backup time
    last_bkp_res = await db.execute(
        select(BackupJobModel.completion_time)
        .where(BackupJobModel.execution_status.in_(["Completed", "Verified"]))
        .order_by(desc(BackupJobModel.completion_time))
        .limit(1)
    )
    last_time = last_bkp_res.scalar_one_or_none()
    last_time_str = last_time.strftime("%d %b %Y, %H:%M UTC") if last_time else None

    # Active policies
    pol_res = await db.execute(select(func.count(BackupPolicyModel.id)).where(BackupPolicyModel.policy_status == "Active"))
    active_policies = pol_res.scalar() or 0

    return ApiResponse(
        success=True,
        code=2000,
        data=BackupDrOverviewStats(
            totalBackups=total_backups,
            successfulBackups=successful_backups,
            failedBackups=failed_backups,
            totalStoredDataTb=total_tb,
            lastBackupTime=last_time_str,
            activePoliciesCount=active_policies,
        ),
    )


@router.get("/policies", response_model=ApiResponse[List[BackupPolicyResponse]])
async def list_backup_policies(
    status: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    backup_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(BackupPolicyModel).order_by(desc(BackupPolicyModel.created_at))
    if status and status != "ALL":
        query = query.where(BackupPolicyModel.policy_status == status)
    if environment and environment != "ALL":
        query = query.where(BackupPolicyModel.environment == environment)
    if backup_type and backup_type != "ALL":
        query = query.where(BackupPolicyModel.backup_type == backup_type)

    res = await db.execute(query)
    policies = res.scalars().all()

    return ApiResponse(
        success=True,
        code=2000,
        data=[
            BackupPolicyResponse(
                id=p.id,
                policyName=p.policy_name,
                policyCode=p.policy_code,
                backupType=p.backup_type,
                backupScope=p.backup_scope,
                environment=p.environment,
                databaseCluster=p.database_cluster,
                databaseName=p.database_name,
                tenantScope=p.tenant_scope,
                backupDestination=p.backup_destination,
                storageBucketPath=p.storage_bucket_path,
                backupFrequency=p.backup_frequency,
                backupSchedule=p.backup_schedule,
                timeZone=p.time_zone,
                retentionPeriod=p.retention_period,
                retentionUnit=p.retention_unit,
                encryptionEnabled=p.encryption_enabled,
                compressionEnabled=p.compression_enabled,
                backupVerification=p.backup_verification,
                notificationRecipients=p.notification_recipients or [],
                policyStatus=p.policy_status,
                createdAt=p.created_at,
                updatedAt=p.updated_at,
            )
            for p in policies
        ],
    )


@router.post("/policies", response_model=ApiResponse[BackupPolicyResponse], status_code=status.HTTP_201_CREATED)
async def create_backup_policy(
    payload: BackupPolicyPayload,
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate code
    existing = await db.execute(select(BackupPolicyModel).where(BackupPolicyModel.policy_code == payload.policyCode))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Backup policy code '{payload.policyCode}' already registered.",
        )

    policy = BackupPolicyModel(
        policy_name=payload.policyName,
        policy_code=payload.policyCode.upper(),
        backup_type=payload.backupType,
        backup_scope=payload.backupScope,
        environment=payload.environment,
        database_cluster=payload.databaseCluster,
        database_name=payload.databaseName,
        tenant_scope=payload.tenantScope,
        backup_destination=payload.backupDestination,
        storage_bucket_path=payload.storageBucketPath,
        backup_frequency=payload.backupFrequency,
        backup_schedule=payload.backupSchedule,
        time_zone=payload.timeZone,
        retention_period=payload.retentionPeriod,
        retention_unit=payload.retentionUnit,
        encryption_enabled=payload.encryptionEnabled,
        compression_enabled=payload.compressionEnabled,
        backup_verification=payload.backupVerification,
        notification_recipients=payload.notificationRecipients,
        policy_status=payload.policyStatus,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    return ApiResponse(
        success=True,
        code=2001,
        message=f"Policy '{policy.policy_code}' created successfully.",
        data=BackupPolicyResponse(
            id=policy.id,
            policyName=policy.policy_name,
            policyCode=policy.policy_code,
            backupType=policy.backup_type,
            backupScope=policy.backup_scope,
            environment=policy.environment,
            databaseCluster=policy.database_cluster,
            databaseName=policy.database_name,
            tenantScope=policy.tenant_scope,
            backupDestination=policy.backup_destination,
            storageBucketPath=policy.storage_bucket_path,
            backupFrequency=policy.backup_frequency,
            backupSchedule=policy.backup_schedule,
            timeZone=policy.time_zone,
            retentionPeriod=policy.retention_period,
            retentionUnit=policy.retention_unit,
            encryptionEnabled=policy.encryption_enabled,
            compressionEnabled=policy.compression_enabled,
            backupVerification=policy.backup_verification,
            notificationRecipients=policy.notification_recipients or [],
            policyStatus=policy.policy_status,
            createdAt=policy.created_at,
            updatedAt=policy.updated_at,
        ),
    )


@router.get("/jobs", response_model=ApiResponse[List[BackupJobResponse]])
async def list_backup_jobs(
    search: Optional[str] = Query(None),
    policy_code: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    database: Optional[str] = Query(None),
    backup_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(BackupJobModel).order_by(desc(BackupJobModel.start_time))

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(BackupJobModel.job_id).like(s)
            | func.lower(BackupJobModel.policy_name).like(s)
            | func.lower(BackupJobModel.storage_location).like(s)
        )
    if policy_code and policy_code != "ALL":
        query = query.where(BackupJobModel.policy_code == policy_code)
    if environment and environment != "ALL":
        query = query.where(BackupJobModel.environment == environment)
    if database and database != "ALL":
        query = query.where(BackupJobModel.database_name == database)
    if backup_type and backup_type != "ALL":
        query = query.where(BackupJobModel.backup_type == backup_type)
    if status and status != "ALL":
        query = query.where(BackupJobModel.execution_status == status)

    query = query.offset(skip).limit(limit)
    res = await db.execute(query)
    jobs = res.scalars().all()

    return ApiResponse(
        success=True,
        code=2000,
        data=[
            BackupJobResponse(
                id=j.id,
                jobId=j.job_id,
                policyCode=j.policy_code,
                policyName=j.policy_name,
                environment=j.environment,
                databaseCluster=j.database_cluster,
                databaseName=j.database_name,
                backupType=j.backup_type,
                executionStatus=j.execution_status,
                startTime=j.start_time,
                completionTime=j.completion_time,
                durationSeconds=j.duration_seconds,
                fileSizeBytes=j.file_size_bytes,
                fileSizeFormatted=j.file_size_formatted,
                storageLocation=j.storage_location,
                checksumSha256=j.checksum_sha256,
                verificationStatus=j.verification_status,
                verificationResult=j.verification_result,
                createdAt=j.created_at,
            )
            for j in jobs
        ],
    )


@router.post("/jobs/trigger", response_model=ApiResponse[BackupJobResponse])
async def trigger_on_demand_backup(
    policy_code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    pol_res = await db.execute(select(BackupPolicyModel).where(BackupPolicyModel.policy_code == policy_code))
    pol = pol_res.scalar_one_or_none()
    if not pol:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_code}' not found.")

    now = datetime.datetime.utcnow()
    job_id = f"BKP-ONDEMAND-{now.strftime('%Y%m%d-%H%M%S')}"
    new_job = new_backup_job(pol, job_id, now)
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    start_background(run_backup(new_job.id))

    return ApiResponse(
        success=True,
        code=2001,
        message=f"Backup job '{new_job.job_id}' started.",
        data=BackupJobResponse(
            id=new_job.id,
            jobId=new_job.job_id,
            policyCode=new_job.policy_code,
            policyName=new_job.policy_name,
            environment=new_job.environment,
            databaseCluster=new_job.database_cluster,
            databaseName=new_job.database_name,
            backupType=new_job.backup_type,
            executionStatus=new_job.execution_status,
            startTime=new_job.start_time,
            completionTime=new_job.completion_time,
            durationSeconds=new_job.duration_seconds,
            fileSizeBytes=new_job.file_size_bytes,
            fileSizeFormatted=new_job.file_size_formatted,
            storageLocation=new_job.storage_location,
            checksumSha256=new_job.checksum_sha256,
            verificationStatus=new_job.verification_status,
            verificationResult=new_job.verification_result,
            createdAt=new_job.created_at,
        ),
    )


@router.get("/restores", response_model=ApiResponse[List[RestoreJobResponse]])
async def list_restore_jobs(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(RestoreJobModel).order_by(desc(RestoreJobModel.created_at)))
    restores = res.scalars().all()

    return ApiResponse(
        success=True,
        code=2000,
        data=[
            RestoreJobResponse(
                id=r.id,
                restoreJobName=r.restore_job_name,
                sourceBackupId=r.source_backup_id,
                sourceDatabase=r.source_database,
                targetEnvironment=r.target_environment,
                targetDatabase=r.target_database,
                restoreType=r.restore_type,
                restoreDestination=r.restore_destination,
                restoreTimestamp=r.restore_timestamp,
                includeTransactionLogs=r.include_transaction_logs,
                validationRequired=r.validation_required,
                approvalAuthority=r.approval_authority,
                changeReference=r.change_reference,
                restoreReason=r.restore_reason,
                executionStatus=r.execution_status,
                durationSeconds=r.duration_seconds,
                initiatedBy=r.initiated_by,
                createdAt=r.created_at,
            )
            for r in restores
        ],
    )


@router.post("/restores", response_model=ApiResponse[RestoreJobResponse], status_code=status.HTTP_201_CREATED)
async def initiate_restore_operation(
    payload: RestoreJobPayload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not payload.finalConfirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Final compliance confirmation checkbox must be explicitly acknowledged.",
        )

    source = await db.scalar(select(BackupJobModel).where(BackupJobModel.job_id == payload.sourceBackupId))
    if not source or source.execution_status != "Completed":
        raise HTTPException(status_code=400, detail="Choose a completed backup to restore from.")

    restore = RestoreJobModel(
        restore_job_name=payload.restoreJobName,
        source_backup_id=payload.sourceBackupId,
        source_database=payload.sourceDatabase,
        target_environment=payload.targetEnvironment,
        target_database=payload.targetDatabase,
        restore_type=payload.restoreType,
        restore_destination=payload.restoreDestination,
        restore_timestamp=payload.restoreTimestamp or datetime.datetime.utcnow(),
        include_transaction_logs=payload.includeTransactionLogs,
        validation_required=payload.validationRequired,
        approval_authority=PENDING_APPROVER,
        change_reference=payload.changeReference,
        restore_reason=payload.restoreReason,
        execution_status="Pending Approval",
        duration_seconds=0,
        initiated_by=_operator(user),
    )
    db.add(restore)
    await db.commit()
    await db.refresh(restore)

    return ApiResponse(
        success=True,
        code=2001,
        message=f"Restore request '{restore.restore_job_name}' recorded and awaiting approval by a second administrator.",
        data=RestoreJobResponse(
            id=restore.id,
            restoreJobName=restore.restore_job_name,
            sourceBackupId=restore.source_backup_id,
            sourceDatabase=restore.source_database,
            targetEnvironment=restore.target_environment,
            targetDatabase=restore.target_database,
            restoreType=restore.restore_type,
            restoreDestination=restore.restore_destination,
            restoreTimestamp=restore.restore_timestamp,
            includeTransactionLogs=restore.include_transaction_logs,
            validationRequired=restore.validation_required,
            approvalAuthority=restore.approval_authority,
            changeReference=restore.change_reference,
            restoreReason=restore.restore_reason,
            executionStatus=restore.execution_status,
            durationSeconds=restore.duration_seconds,
            initiatedBy=restore.initiated_by,
            createdAt=restore.created_at,
        ),
    )


@router.post("/restores/{restore_id}/approve", response_model=ApiResponse[dict])
async def approve_restore_request(
    restore_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    restore = await db.scalar(select(RestoreJobModel).where(RestoreJobModel.id == restore_id))
    if not restore:
        raise HTTPException(status_code=404, detail="Restore request not found.")
    if restore.execution_status != "Pending Approval":
        raise HTTPException(status_code=409, detail="This restore request is not awaiting approval.")
    approver = _operator(user)
    if approver.lower() == (restore.initiated_by or "").lower():
        raise HTTPException(status_code=403, detail="A restore must be approved by a different administrator.")
    restore.approval_authority = approver
    restore.execution_status = "Running"
    await db.commit()
    start_background(run_restore(restore.id))
    return ApiResponse(
        success=True,
        code=2000,
        message="Restore approved and started in a new scratch database.",
        data={"id": restore.id, "executionStatus": restore.execution_status, "approvedBy": approver},
    )


@router.get("/pitr-status", response_model=ApiResponse[PitrWindowStatus])
async def get_pitr_status(db: AsyncSession = Depends(get_db)):
    row = (await db.execute(text("SELECT current_database(), pg_current_wal_lsn()::text, current_setting('archive_mode')"))).one()
    replicas = await db.scalar(text("SELECT count(*) FROM pg_stat_replication")) or 0
    archiving = row[2] != "off"
    return ApiResponse(
        success=True,
        code=2000,
        data=PitrWindowStatus(
            databaseCluster=settings.write_db_url.rsplit("@", 1)[-1].split("/", 1)[0],
            databaseName=row[0],
            currentWalLsn=row[1],
            walArchiveLocation=None if not archiving else "See archive_command on the database server",
            streamingReplicationStatus=f"{replicas} streaming replica(s); WAL archiving {'on' if archiving else 'off'}",
        ),
    )


@router.get("/drills", response_model=ApiResponse[List[DrillExecutionResponse]])
async def list_drills(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(DrillExecutionModel).order_by(desc(DrillExecutionModel.planned_start_date)))
    drills = res.scalars().all()

    return ApiResponse(
        success=True,
        code=2000,
        data=[
            DrillExecutionResponse(
                id=d.id,
                drillName=d.drill_name,
                drillCode=d.drill_code,
                drillType=d.drill_type,
                environment=d.environment,
                primaryRegion=d.primary_region,
                secondaryRegion=d.secondary_region,
                servicesInScope=d.services_in_scope or [],
                databasesInScope=d.databases_in_scope or [],
                plannedStartDate=d.planned_start_date,
                plannedEndDate=d.planned_end_date,
                expectedRpoMinutes=d.expected_rpo_minutes,
                expectedRtoMinutes=d.expected_rto_minutes,
                actualRpoMinutes=d.actual_rpo_minutes,
                actualRtoMinutes=d.actual_rto_minutes,
                recoverySuccessRatePct=d.recovery_success_rate_pct,
                serviceAvailabilityPct=d.service_availability_pct,
                dataIntegrityResult=d.data_integrity_result,
                completionStatus=d.completion_status,
                drillCoordinator=d.drill_coordinator,
                approvalAuthority=d.approval_authority,
                notificationRecipients=d.notification_recipients or [],
                drillObjective=d.drill_objective,
                rollbackPlan=d.rollback_plan,
                findings=d.findings,
                createdAt=d.created_at,
            )
            for d in drills
        ],
    )


@router.post("/drills/{drill_id}/run", response_model=ApiResponse[dict])
async def start_dr_drill(drill_id: str, db: AsyncSession = Depends(get_db)):
    drill = await db.scalar(select(DrillExecutionModel).where(DrillExecutionModel.id == drill_id))
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found.")
    if drill.completion_status != "Scheduled":
        raise HTTPException(status_code=409, detail="This drill has already run.")
    drill.completion_status = "Running"
    await db.commit()
    start_background(run_drill(drill.id))
    return ApiResponse(data={"id": drill.id, "completionStatus": "Running"})


@router.post("/drills", response_model=ApiResponse[DrillExecutionResponse], status_code=status.HTTP_201_CREATED)
async def schedule_dr_drill(
    payload: DrillExecutionPayload,
    db: AsyncSession = Depends(get_db),
):
    drill = DrillExecutionModel(
        drill_name=payload.drillName,
        drill_code=payload.drillCode.upper(),
        drill_type=payload.drillType,
        environment=payload.environment,
        primary_region=payload.primaryRegion,
        secondary_region=payload.secondaryRegion,
        services_in_scope=payload.servicesInScope,
        databases_in_scope=payload.databasesInScope,
        planned_start_date=payload.plannedStartDate,
        planned_end_date=payload.plannedEndDate,
        expected_rpo_minutes=payload.expectedRpoMinutes,
        expected_rto_minutes=payload.expectedRtoMinutes,
        actual_rpo_minutes=null(),
        actual_rto_minutes=null(),
        recovery_success_rate_pct=null(),
        service_availability_pct=null(),
        data_integrity_result="Not executed",
        completion_status="Scheduled",
        drill_coordinator=payload.drillCoordinator,
        approval_authority=payload.approvalAuthority,
        notification_recipients=payload.notificationRecipients,
        drill_objective=payload.drillObjective,
        rollback_plan=payload.rollbackPlan,
        findings="Not executed. No pre-flight checks have been run.",
    )
    db.add(drill)
    await db.commit()
    await db.refresh(drill)

    return ApiResponse(
        success=True,
        code=2001,
        message=f"Disaster Recovery Drill '{drill.drill_code}' scheduled successfully.",
        data=DrillExecutionResponse(
            id=drill.id,
            drillName=drill.drill_name,
            drillCode=drill.drill_code,
            drillType=drill.drill_type,
            environment=drill.environment,
            primaryRegion=drill.primary_region,
            secondaryRegion=drill.secondary_region,
            servicesInScope=drill.services_in_scope or [],
            databasesInScope=drill.databases_in_scope or [],
            plannedStartDate=drill.planned_start_date,
            plannedEndDate=drill.planned_end_date,
            expectedRpoMinutes=drill.expected_rpo_minutes,
            expectedRtoMinutes=drill.expected_rto_minutes,
            actualRpoMinutes=drill.actual_rpo_minutes,
            actualRtoMinutes=drill.actual_rto_minutes,
            recoverySuccessRatePct=drill.recovery_success_rate_pct,
            serviceAvailabilityPct=drill.service_availability_pct,
            dataIntegrityResult=drill.data_integrity_result,
            completionStatus=drill.completion_status,
            drillCoordinator=drill.drill_coordinator,
            approvalAuthority=drill.approval_authority,
            notificationRecipients=drill.notification_recipients or [],
            drillObjective=drill.drill_objective,
            rollbackPlan=drill.rollback_plan,
            findings=drill.findings,
            createdAt=drill.created_at,
        ),
    )

