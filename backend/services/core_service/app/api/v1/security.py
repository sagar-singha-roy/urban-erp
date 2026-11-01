import datetime
import uuid
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update, delete, func, desc, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.tenant_context import SET_RLS_CONTEXT_SQL, rls_params
from app.db.session import get_db
from app.db.models import RLSPolicyModel, TenantIsolationTestRun, IsolationFindingReport
from app.schemas.security import (
    RLSPolicyCreate,
    RLSPolicyUpdate,
    RLSPolicyResponse,
    RLSPolicyValidationResult,
    TenantIsolationTestCreate,
    TenantIsolationTestResponse,
    TenantIsolationTestRunResult,
    IsolationFindingCreate,
    IsolationFindingUpdate,
    IsolationFindingResponse,
    IsolationFindingRetestResult,
    SecuritySummaryStatsResponse,
)
from app.schemas.tenant import ApiResponse

router = APIRouter(
    prefix="/security",
    tags=["Data Security & Tenant Isolation"],
    dependencies=[Depends(require_roles(["super_admin"]))]
)


# -------------------------------------------------------------------------
# Seed Data Helpers
# -------------------------------------------------------------------------
async def _rls_state(db: AsyncSession, table_name: str) -> Dict[str, Any]:
    """Row-level security state as PostgreSQL reports it for one table."""
    row = (await db.execute(
        text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity, "
            "(SELECT count(*) FROM pg_policies p WHERE p.schemaname = n.nspname AND p.tablename = c.relname) "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.relname = :tbl AND n.nspname = current_schema() AND c.relkind IN ('r', 'p')"
        ),
        {"tbl": table_name},
    )).first()
    if row is None:
        return {"exists": False, "enabled": False, "forced": False, "policies": 0}
    return {"exists": True, "enabled": bool(row[0]), "forced": bool(row[1]), "policies": int(row[2])}


def _rls_is_enforced(state: Dict[str, Any]) -> bool:
    return state["enabled"] and state["policies"] > 0


def _describe_rls(table_name: str, state: Dict[str, Any]) -> str:
    if not state["exists"]:
        return f"Table '{table_name}' does not exist."
    if not state["enabled"]:
        return f"Row-level security is not enabled on '{table_name}'."
    if not state["policies"]:
        return f"Row-level security is enabled on '{table_name}' but it has no policies."
    return f"Row-level security is enabled on '{table_name}' with {state['policies']} policies (forced: {state['forced']})."


# -------------------------------------------------------------------------
# Stats Summary Overview
# -------------------------------------------------------------------------
@router.get("/stats", response_model=ApiResponse[SecuritySummaryStatsResponse])
async def get_security_stats(db: AsyncSession = Depends(get_db)):
    total_policies = (await db.execute(select(func.count(RLSPolicyModel.id)))).scalar() or 0
    active_policies = (await db.execute(
        select(func.count(RLSPolicyModel.id)).where(RLSPolicyModel.policy_status == "ACTIVE")
    )).scalar() or 0

    verified_policies = (await db.execute(
        select(func.count(RLSPolicyModel.id)).where(RLSPolicyModel.last_verification_result == "VERIFIED")
    )).scalar() or 0

    total_runs = (await db.execute(select(func.count(TenantIsolationTestRun.id)))).scalar() or 0
    passed_runs = (await db.execute(
        select(func.count(TenantIsolationTestRun.id)).where(TenantIsolationTestRun.status == "PASSED")
    )).scalar() or 0

    open_findings = (await db.execute(
        select(func.count(IsolationFindingReport.id)).where(
            IsolationFindingReport.retest_status.in_(["OPEN", "IN_REMEDIATION"])
        )
    )).scalar() or 0
    critical_findings = (await db.execute(
        select(func.count(IsolationFindingReport.id)).where(
            IsolationFindingReport.severity == "CRITICAL",
            IsolationFindingReport.retest_status != "VERIFIED"
        )
    )).scalar() or 0
    remediated_findings = (await db.execute(
        select(func.count(IsolationFindingReport.id)).where(
            IsolationFindingReport.retest_status.in_(["RESOLVED", "VERIFIED"])
        )
    )).scalar() or 0

    stats = SecuritySummaryStatsResponse(
        totalRlsPolicies=total_policies,
        activeRlsPolicies=active_policies,
        policyCoverageRate=round(verified_policies / total_policies * 100.0, 1) if total_policies > 0 else 0.0,
        totalTestRuns=total_runs,
        passedTestRuns=passed_runs,
        isolationPassRate=round((passed_runs / total_runs * 100.0), 1) if total_runs > 0 else 0.0,
        openFindingsCount=open_findings,
        criticalFindingsCount=critical_findings,
        remediatedFindingsCount=remediated_findings,
    )

    return ApiResponse(
        success=True,
        message="Security summary statistics fetched successfully",
        data=stats
    )


# -------------------------------------------------------------------------
# 1. RLS Policy Registry Endpoints
# -------------------------------------------------------------------------
@router.get("/rls-policies", response_model=ApiResponse[List[RLSPolicyResponse]])
async def list_rls_policies(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    table: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(RLSPolicyModel).order_by(RLSPolicyModel.policy_code.asc())
    if status and status != "ALL":
        query = query.where(RLSPolicyModel.policy_status == status)
    if table and table != "ALL":
        query = query.where(RLSPolicyModel.table_name == table)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(RLSPolicyModel.policy_name).like(s),
                func.lower(RLSPolicyModel.policy_code).like(s),
                func.lower(RLSPolicyModel.table_name).like(s)
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    policies = result.scalars().all()

    data = [
        RLSPolicyResponse(
            id=p.id,
            policyName=p.policy_name,
            policyCode=p.policy_code,
            databaseService=p.database_service,
            schemaName=p.schema_name,
            tableName=p.table_name,
            tenantKeyColumn=p.tenant_key_column,
            policyType=p.policy_type,
            databaseCommands=p.database_commands or [],
            applicableTenantLevels=p.applicable_tenant_levels or [],
            policyDefinition=p.policy_definition,
            policyStatus=p.policy_status,
            lastVerifiedAt=p.last_verified_at,
            lastVerificationResult=p.last_verification_result,
            verificationLatencyMs=p.verification_latency_ms,
            enforcementNotes=p.enforcement_notes,
            createdAt=p.created_at,
            updatedAt=p.updated_at,
        )
        for p in policies
    ]

    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data)} RLS policies",
        data=data
    )


@router.post("/rls-policies", response_model=ApiResponse[RLSPolicyResponse], status_code=status.HTTP_201_CREATED)
async def create_rls_policy(payload: RLSPolicyCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate code
    existing = await db.execute(select(RLSPolicyModel).where(RLSPolicyModel.policy_code == payload.policyCode))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Policy with code '{payload.policyCode}' already exists."
        )

    policy = RLSPolicyModel(
        id=str(uuid.uuid4()),
        policy_name=payload.policyName,
        policy_code=payload.policyCode,
        database_service=payload.databaseService,
        schema_name=payload.schemaName,
        table_name=payload.tableName,
        tenant_key_column=payload.tenantKeyColumn,
        policy_type=payload.policyType,
        database_commands=payload.databaseCommands,
        applicable_tenant_levels=payload.applicableTenantLevels,
        policy_definition=payload.policyDefinition,
        policy_status=payload.policyStatus,
        last_verified_at=datetime.datetime.utcnow(),
        last_verification_result="NOT_VERIFIED",
        verification_latency_ms=1.2,
        enforcement_notes=payload.enforcementNotes,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    return ApiResponse(
        success=True,
        message=f"RLS Policy '{policy.policy_code}' registered successfully",
        data=RLSPolicyResponse(
            id=policy.id,
            policyName=policy.policy_name,
            policyCode=policy.policy_code,
            databaseService=policy.database_service,
            schemaName=policy.schema_name,
            tableName=policy.table_name,
            tenantKeyColumn=policy.tenant_key_column,
            policyType=policy.policy_type,
            databaseCommands=policy.database_commands,
            applicableTenantLevels=policy.applicable_tenant_levels,
            policyDefinition=policy.policy_definition,
            policyStatus=policy.policy_status,
            lastVerifiedAt=policy.last_verified_at,
            lastVerificationResult=policy.last_verification_result,
            verificationLatencyMs=policy.verification_latency_ms,
            enforcementNotes=policy.enforcement_notes,
            createdAt=policy.created_at,
            updatedAt=policy.updated_at,
        )
    )


@router.put("/rls-policies/{policy_id}", response_model=ApiResponse[RLSPolicyResponse])
async def update_rls_policy(
    policy_id: str,
    payload: RLSPolicyUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RLSPolicyModel).where(RLSPolicyModel.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if payload.policyName is not None:
        policy.policy_name = payload.policyName
    if payload.databaseService is not None:
        policy.database_service = payload.databaseService
    if payload.schemaName is not None:
        policy.schema_name = payload.schemaName
    if payload.tableName is not None:
        policy.table_name = payload.tableName
    if payload.tenantKeyColumn is not None:
        policy.tenant_key_column = payload.tenantKeyColumn
    if payload.policyType is not None:
        policy.policy_type = payload.policyType
    if payload.databaseCommands is not None:
        policy.database_commands = payload.databaseCommands
    if payload.applicableTenantLevels is not None:
        policy.applicable_tenant_levels = payload.applicableTenantLevels
    if payload.policyDefinition is not None:
        policy.policy_definition = payload.policyDefinition
    if payload.policyStatus is not None:
        policy.policy_status = payload.policyStatus
    if payload.enforcementNotes is not None:
        policy.enforcement_notes = payload.enforcementNotes

    policy.updated_at = datetime.datetime.utcnow()
    await db.commit()
    await db.refresh(policy)

    return ApiResponse(
        success=True,
        message=f"Policy '{policy.policy_code}' updated successfully",
        data=RLSPolicyResponse(
            id=policy.id,
            policyName=policy.policy_name,
            policyCode=policy.policy_code,
            databaseService=policy.database_service,
            schemaName=policy.schema_name,
            tableName=policy.table_name,
            tenantKeyColumn=policy.tenant_key_column,
            policyType=policy.policy_type,
            databaseCommands=policy.database_commands,
            applicableTenantLevels=policy.applicable_tenant_levels,
            policyDefinition=policy.policy_definition,
            policyStatus=policy.policy_status,
            lastVerifiedAt=policy.last_verified_at,
            lastVerificationResult=policy.last_verification_result,
            verificationLatencyMs=policy.verification_latency_ms,
            enforcementNotes=policy.enforcement_notes,
            createdAt=policy.created_at,
            updatedAt=policy.updated_at,
        )
    )


@router.delete("/rls-policies/{policy_id}", response_model=ApiResponse[Dict[str, str]])
async def delete_rls_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RLSPolicyModel).where(RLSPolicyModel.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    code = policy.policy_code
    await db.delete(policy)
    await db.commit()

    return ApiResponse(
        success=True,
        message=f"Policy '{code}' deleted from registry",
        data={"id": policy_id, "code": code}
    )


@router.post("/rls-policies/{policy_id}/validate", response_model=ApiResponse[RLSPolicyValidationResult])
async def validate_rls_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RLSPolicyModel).where(RLSPolicyModel.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    start_time = time.perf_counter()
    state = await _rls_state(db, policy.table_name)
    latency_ms = max(0.1, round((time.perf_counter() - start_time) * 1000, 2))

    now = datetime.datetime.utcnow()
    policy.last_verified_at = now
    policy.last_verification_result = "VERIFIED" if _rls_is_enforced(state) else "FAILED"
    policy.verification_latency_ms = latency_ms
    await db.commit()

    return ApiResponse(
        success=True,
        message=f"Policy '{policy.policy_code}' checked against the PostgreSQL catalog: {policy.last_verification_result}",
        data=RLSPolicyValidationResult(
            policyId=policy.id,
            policyCode=policy.policy_code,
            status=policy.last_verification_result,
            latencyMs=latency_ms,
            verifiedAt=now,
            details=_describe_rls(policy.table_name, state),
            enforcedQuerySample=f"SELECT count(*) FROM {policy.table_name} WHERE {policy.tenant_key_column} = current_setting('app.current_tenant_id', true)::uuid;"
        )
    )


# -------------------------------------------------------------------------
# 2. Tenant Isolation Test Configuration & Test Runs Endpoints
# -------------------------------------------------------------------------
@router.get("/isolation-tests", response_model=ApiResponse[List[TenantIsolationTestResponse]])
async def list_isolation_tests(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(TenantIsolationTestRun).order_by(desc(TenantIsolationTestRun.created_at))
    if status and status != "ALL":
        query = query.where(TenantIsolationTestRun.status == status)
    if environment and environment != "ALL":
        query = query.where(TenantIsolationTestRun.environment == environment)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(TenantIsolationTestRun.test_run_name).like(s),
                func.lower(TenantIsolationTestRun.source_tenant).like(s),
                func.lower(TenantIsolationTestRun.target_tenant).like(s)
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    runs = result.scalars().all()

    data = [
        TenantIsolationTestResponse(
            id=r.id,
            testRunName=r.test_run_name,
            environment=r.environment,
            sourceTenant=r.source_tenant,
            targetTenant=r.target_tenant,
            testScenarios=r.test_scenarios or [],
            databaseServices=r.database_services or [],
            tablesInScope=r.tables_in_scope or [],
            testType=r.test_type,
            executionMode=r.execution_mode,
            schedule=r.schedule,
            notificationRecipients=r.notification_recipients or [],
            stopOnCriticalFailure=r.stop_on_critical_failure,
            status=r.status,
            startTime=r.start_time,
            endTime=r.end_time,
            totalTests=r.total_tests,
            passedCount=r.passed_count,
            failedCount=r.failed_count,
            executionLatencyMs=r.execution_latency_ms,
            createdAt=r.created_at,
        )
        for r in runs
    ]

    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data)} test runs",
        data=data
    )


@router.post("/isolation-tests", response_model=ApiResponse[TenantIsolationTestResponse], status_code=status.HTTP_201_CREATED)
async def create_isolation_test_run(
    payload: TenantIsolationTestCreate,
    db: AsyncSession = Depends(get_db)
):
    new_id = f"ISO-RUN-{datetime.datetime.utcnow().year}-{str(uuid.uuid4())[:6].upper()}"
    test_run = TenantIsolationTestRun(
        id=new_id,
        test_run_name=payload.testRunName,
        environment=payload.environment,
        source_tenant=payload.sourceTenant,
        target_tenant=payload.targetTenant,
        test_scenarios=payload.testScenarios,
        database_services=payload.databaseServices,
        tables_in_scope=payload.tablesInScope,
        test_type=payload.testType,
        execution_mode=payload.executionMode,
        schedule=payload.schedule,
        notification_recipients=payload.notificationRecipients or [],
        stop_on_critical_failure=payload.stopOnCriticalFailure,
        status="SCHEDULED",
        start_time=None,
        end_time=None,
        total_tests=len(payload.testScenarios) * 2,
        passed_count=0,
        failed_count=0,
        execution_latency_ms=0.0,
    )
    db.add(test_run)
    await db.commit()
    await db.refresh(test_run)

    return ApiResponse(
        success=True,
        message=f"Tenant isolation test run '{test_run.id}' configured successfully",
        data=TenantIsolationTestResponse(
            id=test_run.id,
            testRunName=test_run.test_run_name,
            environment=test_run.environment,
            sourceTenant=test_run.source_tenant,
            targetTenant=test_run.target_tenant,
            testScenarios=test_run.test_scenarios,
            databaseServices=test_run.database_services,
            tablesInScope=test_run.tables_in_scope,
            testType=test_run.test_type,
            executionMode=test_run.execution_mode,
            schedule=test_run.schedule,
            notificationRecipients=test_run.notification_recipients,
            stopOnCriticalFailure=test_run.stop_on_critical_failure,
            status=test_run.status,
            startTime=test_run.start_time,
            endTime=test_run.end_time,
            totalTests=test_run.total_tests,
            passedCount=test_run.passed_count,
            failedCount=test_run.failed_count,
            executionLatencyMs=test_run.execution_latency_ms,
            createdAt=test_run.created_at,
        )
    )


@router.post("/isolation-tests/{test_run_id}/run", response_model=ApiResponse[TenantIsolationTestRunResult])
async def execute_isolation_test_run(
    test_run_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TenantIsolationTestRun).where(TenantIsolationTestRun.id == test_run_id))
    test_run = result.scalar_one_or_none()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")

    # Reads the target tenant's rows while scoped to the source tenant, under the application role.
    start_time = datetime.datetime.utcnow()
    tables = test_run.tables_in_scope or []
    source = (test_run.source_tenant or "").strip().upper()
    target = (test_run.target_tenant or "").strip().upper()
    role_bypasses = bool(await db.scalar(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")))
    scenario_results = []
    for table_name in tables:
        check_started = time.perf_counter()
        state = await _rls_state(db, table_name)
        outcome, evidence = "FAILED", _describe_rls(table_name, state)
        if role_bypasses:
            evidence = "The application database role bypasses row-level security."
        elif _rls_is_enforced(state):
            quoted = '"' + table_name.replace('"', '""') + '"'
            count_target = text(f"SELECT count(*) FROM {quoted} WHERE upper(tenant_id) = :target")
            await db.execute(text(SET_RLS_CONTEXT_SQL), {"tenant_ids": "", "bypass": "on"})
            target_rows = await db.scalar(count_target, {"target": target})
            await db.execute(text(SET_RLS_CONTEXT_SQL), {"tenant_ids": source, "bypass": "off"})
            leaked = await db.scalar(count_target, {"target": target})
            await db.execute(text(SET_RLS_CONTEXT_SQL), rls_params())
            if not target_rows:
                outcome, evidence = "INCONCLUSIVE", f"{target} has no rows in {table_name} to test against."
            elif leaked:
                evidence = f"{source} could read {leaked} of {target}'s {target_rows} rows in {table_name}."
            else:
                outcome, evidence = "PASSED", f"{source} read 0 of {target}'s {target_rows} rows in {table_name}."
        scenario_results.append({
            "scenario": f"{source} cannot read {target} rows in {table_name}",
            "status": outcome,
            "assertion": evidence,
            "latencyMs": round((time.perf_counter() - check_started) * 1000, 2),
        })

    end_time = datetime.datetime.utcnow()
    latency_ms = round((end_time - start_time).total_seconds() * 1000, 1)
    passed = sum(1 for r in scenario_results if r["status"] == "PASSED")
    failed = sum(1 for r in scenario_results if r["status"] == "FAILED")
    if not scenario_results:
        run_status = "NOT_EXECUTED"
    else:
        run_status = "FAILED" if failed else ("PASSED" if passed == len(scenario_results) else "INCONCLUSIVE")

    test_run.status = run_status
    test_run.start_time = start_time
    test_run.end_time = end_time
    test_run.total_tests = len(scenario_results)
    test_run.passed_count = passed
    test_run.failed_count = failed
    test_run.execution_latency_ms = latency_ms

    await db.commit()

    return ApiResponse(
        success=True,
        message=f"Isolation test run '{test_run_id}': {run_status} ({passed} passed, {failed} failed)",
        data=TenantIsolationTestRunResult(
            testRunId=test_run_id,
            status=run_status,
            totalTests=len(scenario_results),
            passedCount=passed,
            failedCount=failed,
            latencyMs=latency_ms,
            scenarioResults=scenario_results,
        )
    )


# -------------------------------------------------------------------------
# 3. Isolation Findings & Reports Endpoints
# -------------------------------------------------------------------------
@router.get("/findings", response_model=ApiResponse[List[IsolationFindingResponse]])
async def list_isolation_findings(
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tenant: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(IsolationFindingReport).order_by(desc(IsolationFindingReport.detected_at))
    if severity and severity != "ALL":
        query = query.where(IsolationFindingReport.severity == severity)
    if status and status != "ALL":
        query = query.where(IsolationFindingReport.retest_status == status)
    if tenant and tenant != "ALL":
        query = query.where(func.lower(IsolationFindingReport.affected_tenant).like(f"%{tenant.strip().lower()}%"))
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(IsolationFindingReport.finding_title).like(s),
                func.lower(IsolationFindingReport.finding_description).like(s),
                func.lower(IsolationFindingReport.affected_tenant).like(s),
                func.lower(IsolationFindingReport.affected_resource).like(s),
                func.lower(IsolationFindingReport.remediation_owner).like(s)
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    findings = result.scalars().all()

    data = [
        IsolationFindingResponse(
            id=f.id,
            testRunId=f.test_run_id,
            severity=f.severity,
            findingTitle=f.finding_title,
            findingDescription=f.finding_description,
            affectedTenant=f.affected_tenant,
            affectedResource=f.affected_resource,
            remediationOwner=f.remediation_owner,
            remediationDueDate=f.remediation_due_date,
            resolutionNotes=f.resolution_notes,
            retestStatus=f.retest_status,
            detectedAt=f.detected_at,
            resolvedAt=f.resolved_at,
        )
        for f in findings
    ]

    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data)} isolation findings",
        data=data
    )


@router.post("/findings", response_model=ApiResponse[IsolationFindingResponse], status_code=status.HTTP_201_CREATED)
async def create_isolation_finding(
    payload: IsolationFindingCreate,
    db: AsyncSession = Depends(get_db)
):
    new_id = f"SEC-FIND-{datetime.datetime.utcnow().year}-{str(uuid.uuid4())[:6].upper()}"
    finding = IsolationFindingReport(
        id=new_id,
        test_run_id=payload.testRunId,
        severity=payload.severity,
        finding_title=payload.findingTitle,
        finding_description=payload.findingDescription,
        affected_tenant=payload.affectedTenant,
        affected_resource=payload.affectedResource,
        remediation_owner=payload.remediationOwner,
        remediation_due_date=payload.remediationDueDate,
        resolution_notes=payload.resolutionNotes,
        retest_status="OPEN" if payload.retestStatus == "VERIFIED" else payload.retestStatus,
        detected_at=datetime.datetime.utcnow(),
    )
    db.add(finding)
    await db.commit()
    await db.refresh(finding)

    return ApiResponse(
        success=True,
        message=f"Finding '{finding.id}' logged successfully",
        data=IsolationFindingResponse(
            id=finding.id,
            testRunId=finding.test_run_id,
            severity=finding.severity,
            findingTitle=finding.finding_title,
            findingDescription=finding.finding_description,
            affectedTenant=finding.affected_tenant,
            affectedResource=finding.affected_resource,
            remediationOwner=finding.remediation_owner,
            remediationDueDate=finding.remediation_due_date,
            resolutionNotes=finding.resolution_notes,
            retestStatus=finding.retest_status,
            detectedAt=finding.detected_at,
            resolvedAt=finding.resolved_at,
        )
    )


@router.put("/findings/{finding_id}", response_model=ApiResponse[IsolationFindingResponse])
async def update_isolation_finding(
    finding_id: str,
    payload: IsolationFindingUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(IsolationFindingReport).where(IsolationFindingReport.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if payload.severity is not None:
        finding.severity = payload.severity
    if payload.findingTitle is not None:
        finding.finding_title = payload.findingTitle
    if payload.findingDescription is not None:
        finding.finding_description = payload.findingDescription
    if payload.affectedTenant is not None:
        finding.affected_tenant = payload.affectedTenant
    if payload.affectedResource is not None:
        finding.affected_resource = payload.affectedResource
    if payload.remediationOwner is not None:
        finding.remediation_owner = payload.remediationOwner
    if payload.remediationDueDate is not None:
        finding.remediation_due_date = payload.remediationDueDate
    if payload.resolutionNotes is not None:
        finding.resolution_notes = payload.resolutionNotes
    if payload.retestStatus is not None:
        if payload.retestStatus == "VERIFIED" and finding.retest_status != "VERIFIED":
            raise HTTPException(status_code=400, detail="VERIFIED can only be set by a passing retest.")
        finding.retest_status = payload.retestStatus
        if payload.retestStatus in ["RESOLVED", "VERIFIED"]:
            finding.resolved_at = datetime.datetime.utcnow()

    await db.commit()
    await db.refresh(finding)

    return ApiResponse(
        success=True,
        message=f"Finding '{finding.id}' updated successfully",
        data=IsolationFindingResponse(
            id=finding.id,
            testRunId=finding.test_run_id,
            severity=finding.severity,
            findingTitle=finding.finding_title,
            findingDescription=finding.finding_description,
            affectedTenant=finding.affected_tenant,
            affectedResource=finding.affected_resource,
            remediationOwner=finding.remediation_owner,
            remediationDueDate=finding.remediation_due_date,
            resolutionNotes=finding.resolution_notes,
            retestStatus=finding.retest_status,
            detectedAt=finding.detected_at,
            resolvedAt=finding.resolved_at,
        )
    )


@router.post("/findings/{finding_id}/retest", response_model=ApiResponse[IsolationFindingRetestResult])
async def retest_isolation_finding(
    finding_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(IsolationFindingReport).where(IsolationFindingReport.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    now = datetime.datetime.utcnow()
    state = await _rls_state(db, finding.affected_resource)
    if not state["exists"]:
        result_label = "INCONCLUSIVE"
        details = f"'{finding.affected_resource}' is not a database table, so it has no automated retest."
    elif _rls_is_enforced(state):
        result_label = "PASS"
        finding.retest_status = "VERIFIED"
        finding.resolved_at = now
        details = _describe_rls(finding.affected_resource, state)
    else:
        result_label = "FAIL"
        finding.retest_status = "OPEN"
        finding.resolved_at = None
        details = _describe_rls(finding.affected_resource, state)
    await db.commit()

    return ApiResponse(
        success=True,
        data=IsolationFindingRetestResult(
            findingId=finding.id,
            retestStatus=finding.retest_status,
            verificationResult=result_label,
            testedAt=now,
            details=details,
        )
    )
