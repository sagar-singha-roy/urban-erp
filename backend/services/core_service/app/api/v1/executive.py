"""Executive analytics computed only from platform records.

Metrics without a source table are returned as null and listed in unavailableMetrics,
so a missing number can never be read as a real one.
"""
import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.config import PLATFORM_ULB_TYPE
from app.db.models import Building, ModuleModel, PropertyParcel, PropertyUnit, StateTenant, Tenant, User
from app.db.session import get_read_db
from app.schemas.executive import (
    CitizenAdoptionStats,
    CityComparisonResponse,
    DcbRecoveryResponse,
    ExecutiveFilterOptions,
    FinancialSummaryStats,
    GlobalOverviewStats,
    GrantAllocationCreate,
    GrantAllocationItem,
    GrantAllocationResponse,
    GrantsOverviewStats,
    GrievanceOverviewStats,
    ParcelStatisticsStats,
    ReconciliationResponse,
    RevenueAnalyticsStats,
    SlaComplianceResponse,
    StateComparisonResponse,
    SwachhRankingsResponse,
    TenantLedgerResponse,
)
from app.schemas.tenant import ApiResponse

router = APIRouter(prefix="/executive", tags=["Executive Intelligence (ADM-A01)"], dependencies=[Depends(require_roles(["super_admin"]))])

NO_PAYMENTS = "No payment records exist yet, so collection, arrears and recovery figures are not available."
NO_GRIEVANCES = "The Citizen Grievance module has no records yet, so grievance and SLA figures are not available."
NO_ADOPTION = "No digital service usage is recorded yet, so adoption figures are not available."
NO_SWACHH = "No verified Swachh Survekshan import exists, so official rankings are not available."
NO_LEDGER = "The Finance & Accounting module has no ledger or grant records yet, so financial figures are not available."
PROPERTY_TAX_CODE = "PTX"


@dataclass
class TenantRollup:
    tenant: Tenant
    parcels: int = 0
    mapped_parcels: int = 0
    demand: float = 0.0


def _split(*values: Optional[str]) -> List[str]:
    """Merge comma-separated filter values into a de-duplicated upper-case list."""
    parts = [part.strip().upper() for value in values if value for part in value.split(",")]
    return list(dict.fromkeys(part for part in parts if part and part != "ALL"))


def _share(part: float, whole: float) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def _tenant_condition(states: List[str], ulbs: List[str]):
    conditions = []
    if states:
        conditions.append(
            or_(func.upper(Tenant.state_code).in_(states), func.upper(Tenant.parent_state_tenant_id).in_(states))
        )
    if ulbs:
        conditions.append(func.upper(Tenant.tenant_id).in_(ulbs))
    return and_(*conditions) if conditions else None


async def _tenant_rollups(db: AsyncSession, states: List[str], ulbs: List[str]) -> List[TenantRollup]:
    stmt = select(Tenant).where(Tenant.ulb_type != PLATFORM_ULB_TYPE).order_by(Tenant.name)
    condition = _tenant_condition(states, ulbs)
    if condition is not None:
        stmt = stmt.where(condition)
    tenants = (await db.scalars(stmt)).all()
    rollups = {t.tenant_id: TenantRollup(t) for t in tenants}
    if not rollups:
        return []

    parcel_rows = await db.execute(
        select(
            PropertyParcel.tenant_id,
            func.count(PropertyParcel.id),
            func.count(PropertyParcel.id).filter(
                PropertyParcel.latitude.isnot(None), PropertyParcel.longitude.isnot(None)
            ),
        )
        .where(PropertyParcel.tenant_id.in_(rollups))
        .group_by(PropertyParcel.tenant_id)
    )
    for tenant_id, parcels, mapped in parcel_rows.all():
        rollups[tenant_id].parcels = parcels
        rollups[tenant_id].mapped_parcels = mapped

    demand_rows = await db.execute(
        select(PropertyUnit.tenant_id, func.coalesce(func.sum(PropertyUnit.current_demand_amount), 0))
        .where(PropertyUnit.tenant_id.in_(rollups))
        .group_by(PropertyUnit.tenant_id)
    )
    for tenant_id, demand in demand_rows.all():
        if tenant_id in rollups:
            rollups[tenant_id].demand = float(demand)
    return list(rollups.values())


async def _state_rows(db: AsyncSession, states: List[str], rollups: List[TenantRollup]) -> List[Dict]:
    """One row per state tenant, totalled from the given city rollups."""
    stmt = select(StateTenant).order_by(StateTenant.state_name)
    if states:
        stmt = stmt.where(or_(func.upper(StateTenant.state_code).in_(states), func.upper(StateTenant.tenant_id).in_(states)))
    rows = []
    for state in (await db.scalars(stmt)).all():
        members = [r for r in rollups if (r.tenant.state_code or "").upper() == state.state_code.upper()]
        rows.append(
            {
                "stateCode": state.state_code,
                "stateName": state.state_name,
                "status": state.status,
                "ulbCount": len(members),
                "parcels": sum(r.parcels for r in members),
                "demand": sum(r.demand for r in members),
            }
        )
    return rows


def _unavailable(model, reason: str, **fields):
    return ApiResponse(data=model(dataAvailable=False, unavailableReason=reason, **fields))


@router.get("/filter-options", response_model=ApiResponse[ExecutiveFilterOptions])
async def get_filter_options(db: AsyncSession = Depends(get_read_db)):
    """Filter values derived from platform records. Empty lists mean no records exist yet."""
    states = (await db.scalars(select(StateTenant).order_by(StateTenant.state_name))).all()
    tenants = (await db.scalars(select(Tenant).where(Tenant.ulb_type != PLATFORM_ULB_TYPE).order_by(Tenant.name))).all()
    modules = (await db.execute(select(ModuleModel.code, ModuleModel.name).order_by(ModuleModel.display_order))).all()
    categories = (await db.scalars(select(distinct(PropertyUnit.usage_category)).order_by(PropertyUnit.usage_category))).all()
    ulb_types = sorted({t.ulb_type for t in tenants if t.ulb_type})

    today = datetime.date.today()
    fy_start = today.year if today.month >= 4 else today.year - 1
    financial_years = [f"FY {year}-{(year + 1) % 100:02d}" for year in range(fy_start, fy_start - 3, -1)]

    return ApiResponse(
        data=ExecutiveFilterOptions(
            states=[{"code": s.state_code, "name": s.state_name, "stateCode": s.state_code} for s in states],
            ulbs=[{"code": t.tenant_id, "name": t.name, "stateCode": t.state_code} for t in tenants],
            revenueModules=[{"code": m.code, "name": m.name} for m in modules],
            revenueCategories=list(categories),
            propertyCategories=list(categories),
            financialYears=financial_years,
            geographicScopes=["All Configured States", "Selected States", "Selected ULBs"],
            aggregationLevels=["State", "ULB", "Revenue Category"],
            ulbCategories=ulb_types,
            rankingMethods=["Parcel Count"],
        )
    )


@router.get("/overview", response_model=ApiResponse[GlobalOverviewStats])
async def get_executive_overview(
    stateTenant: Optional[str] = Query(None),
    stateTenants: Optional[str] = Query(None),
    ulbTenant: Optional[str] = Query(None),
    ulbTenants: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_read_db),
):
    """ADM-A01 Overview: tenant, parcel and citizen counts from live records."""
    states, ulbs = _split(stateTenant, stateTenants), _split(ulbTenant, ulbTenants)
    rollups = await _tenant_rollups(db, states, ulbs)
    state_rows = await _state_rows(db, states, rollups)
    tenant_ids = [r.tenant.tenant_id for r in rollups]
    citizens = await db.scalar(
        select(func.count(User.id)).where(User.role == "citizen", User.tenant_id.in_(tenant_ids))
    ) if tenant_ids else 0

    return ApiResponse(
        data=GlobalOverviewStats(
            totalRegisteredParcels=sum(r.parcels for r in rollups),
            totalRegisteredCitizens=citizens or 0,
            activeStateTenants=sum(1 for s in state_rows if s["status"] == "Active"),
            activeUlbTenants=len(rollups),
            stateBenchmarks=[
                {**s, "collected": None, "efficiency": None, "grievanceSla": None, "digitalAdoption": None}
                for s in state_rows
            ],
            unavailableReason=f"{NO_PAYMENTS} {NO_GRIEVANCES} {NO_ADOPTION}",
            unavailableMetrics=["revenue collected", "outstanding revenue", "grievances", "digital adoption", "trends"],
        )
    )


@router.get("/revenue-analytics", response_model=ApiResponse[RevenueAnalyticsStats])
async def get_revenue_analytics(
    stateTenant: Optional[str] = Query(None),
    stateTenants: Optional[str] = Query(None),
    ulbTenant: Optional[str] = Query(None),
    ulbTenants: Optional[str] = Query(None),
    revenueModule: Optional[str] = Query(None),
    revenueCategory: Optional[str] = Query(None),
    aggregationLevel: str = Query("State"),
    db: AsyncSession = Depends(get_read_db),
):
    """ADM-A01 Revenue: raised property tax demand. Unit demand is the only revenue record kept today."""
    modules = _split(revenueModule)
    if modules and PROPERTY_TAX_CODE not in modules:
        return _unavailable(RevenueAnalyticsStats, f"No demand records exist for {', '.join(modules)}.")

    states, ulbs = _split(stateTenant, stateTenants), _split(ulbTenant, ulbTenants)
    rollups = await _tenant_rollups(db, states, ulbs)
    tenant_ids = [r.tenant.tenant_id for r in rollups]
    level = aggregationLevel.strip().lower()

    if tenant_ids and (level == "revenue category" or revenueCategory):
        stmt = (
            select(PropertyUnit.usage_category, func.coalesce(func.sum(PropertyUnit.current_demand_amount), 0))
            .where(PropertyUnit.tenant_id.in_(tenant_ids))
            .group_by(PropertyUnit.usage_category)
            .order_by(PropertyUnit.usage_category)
        )
        if revenueCategory:
            stmt = stmt.where(PropertyUnit.usage_category == revenueCategory)
        pairs = [(name, float(demand)) for name, demand in (await db.execute(stmt)).all()]
    elif level == "ulb":
        pairs = [(r.tenant.name, r.demand) for r in rollups]
    else:
        pairs = [(s["stateName"], s["demand"]) for s in await _state_rows(db, states, rollups)]

    total = sum(demand for _, demand in pairs)
    return ApiResponse(
        data=RevenueAnalyticsStats(
            totalDemandTarget=total,
            breakdown=[
                {
                    "name": name,
                    "demand": demand,
                    "collected": None,
                    "arrears": None,
                    "efficiency": None,
                    "sharePct": _share(demand, total),
                }
                for name, demand in pairs
            ],
            unavailableReason=NO_PAYMENTS,
            unavailableMetrics=["collections", "arrears", "efficiency", "outstanding balance", "monthly trend"],
        )
    )


@router.get("/parcel-statistics", response_model=ApiResponse[ParcelStatisticsStats])
async def get_parcel_statistics(
    stateTenant: Optional[str] = Query(None),
    stateTenants: Optional[str] = Query(None),
    ulbTenant: Optional[str] = Query(None),
    ulbTenants: Optional[str] = Query(None),
    propertyCategory: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_read_db),
):
    """ADM-A01 Parcels: registry totals, GIS coordinates and usage categories."""
    rollups = await _tenant_rollups(db, _split(stateTenant, stateTenants), _split(ulbTenant, ulbTenants))
    tenant_ids = [r.tenant.tenant_id for r in rollups]
    total = sum(r.parcels for r in rollups)
    mapped = sum(r.mapped_parcels for r in rollups)

    rows = []
    vacant = 0
    if tenant_ids:
        stmt = (
            select(
                PropertyUnit.usage_category,
                func.count(distinct(Building.parcel_id)),
                func.coalesce(func.sum(PropertyUnit.current_demand_amount), 0),
            )
            .join(Building, PropertyUnit.building_id == Building.id)
            .where(PropertyUnit.tenant_id.in_(tenant_ids))
            .group_by(PropertyUnit.usage_category)
            .order_by(PropertyUnit.usage_category)
        )
        if propertyCategory:
            stmt = stmt.where(PropertyUnit.usage_category == propertyCategory)
        rows = (await db.execute(stmt)).all()
        vacant = await db.scalar(
            select(func.count(distinct(Building.parcel_id)))
            .join(PropertyUnit, PropertyUnit.building_id == Building.id)
            .where(PropertyUnit.tenant_id.in_(tenant_ids), PropertyUnit.occupancy_type == "Vacant")
        ) or 0

    counts = {category: count for category, count, _ in rows}
    total_demand = sum(float(demand) for _, _, demand in rows)
    return ApiResponse(
        data=ParcelStatisticsStats(
            totalParcels=total,
            gisMappedParcels=mapped,
            unmappedParcels=total - mapped,
            residentialParcels=counts.get("Residential", 0),
            commercialParcels=counts.get("Commercial", 0),
            vacantParcels=vacant,
            gisCoveragePct=_share(mapped, total),
            categoryBreakdown=[
                {
                    "category": category,
                    "count": count,
                    "pct": _share(count, total),
                    "revenueContribution": f"{_share(float(demand), total_demand)}%",
                }
                for category, count, demand in rows
            ],
            unavailableReason="Field verification and survey methods are not recorded for parcels yet.",
            unavailableMetrics=["verified parcels", "survey distribution"],
        )
    )


@router.get("/grievance-overview", response_model=ApiResponse[GrievanceOverviewStats])
async def get_grievance_overview():
    return _unavailable(GrievanceOverviewStats, NO_GRIEVANCES)


@router.get("/citizen-adoption", response_model=ApiResponse[CitizenAdoptionStats])
async def get_citizen_adoption(
    stateTenant: Optional[str] = Query(None),
    ulbTenant: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_read_db),
):
    rollups = await _tenant_rollups(db, _split(stateTenant), _split(ulbTenant))
    tenant_ids = [r.tenant.tenant_id for r in rollups]
    citizens = await db.scalar(
        select(func.count(User.id)).where(User.role == "citizen", User.tenant_id.in_(tenant_ids))
    ) if tenant_ids else 0
    return ApiResponse(
        data=CitizenAdoptionStats(
            registeredCitizens=citizens or 0,
            unavailableReason=NO_ADOPTION,
            unavailableMetrics=["active users", "applications", "payments", "channels", "trends"],
        )
    )


# ADM-A02: State & City Benchmarking Matrix


@router.get("/benchmarks/state-comparison", response_model=ApiResponse[StateComparisonResponse])
async def get_state_comparison(
    financialYear: str = Query(""),
    benchmarkName: str = Query(""),
    benchmarkPeriod: str = Query(""),
    selectedStates: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_read_db),
):
    """ADM-A02: states ordered by registered parcels. No composite score is calculated without source data."""
    states = _split(selectedStates)
    rollups = await _tenant_rollups(db, states, [])
    rows = sorted(await _state_rows(db, states, rollups), key=lambda s: (-s["parcels"], s["stateName"]))
    benchmarks = [
        {
            "rank": index,
            "stateCode": s["stateCode"],
            "stateName": s["stateName"],
            "compositeScore": None,
            "demand": s["demand"],
            "collected": None,
            "recoveryPct": None,
            "slaCompliancePct": None,
            "avgResolutionHours": None,
            "digitalAdoptionPct": None,
            "swachhRank": None,
            "swachhScore": None,
            "ulbCount": s["ulbCount"],
            "parcels": s["parcels"],
            "performanceTier": "Not rated",
            "radar": {},
        }
        for index, s in enumerate(rows, 1)
    ]
    return ApiResponse(
        data=StateComparisonResponse(
            benchmarkName=benchmarkName,
            financialYear=financialYear,
            benchmarkPeriod=benchmarkPeriod,
            comparisonMethod="Registered records",
            rankingMetric="Parcel Count",
            benchmarks=benchmarks,
            summary={"evaluatedStatesCount": len(benchmarks)},
            unavailableReason=f"{NO_PAYMENTS} {NO_GRIEVANCES} {NO_SWACHH} States are ordered by parcel count, not performance.",
            unavailableMetrics=["composite score", "recovery", "SLA", "digital adoption", "Swachh rank"],
        )
    )


@router.get("/benchmarks/city-comparison", response_model=ApiResponse[CityComparisonResponse])
async def get_city_comparison(
    stateTenant: Optional[str] = Query(None),
    selectedUlbs: Optional[str] = Query(None),
    financialYear: str = Query(""),
    comparisonPeriod: str = Query(""),
    ulbCategory: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_read_db),
):
    """ADM-A02: cities ordered by registered parcels."""
    rollups = await _tenant_rollups(db, _split(stateTenant), _split(selectedUlbs))
    if ulbCategory:
        rollups = [r for r in rollups if r.tenant.ulb_type == ulbCategory]
    if district:
        rollups = [r for r in rollups if (r.tenant.district or "").lower() == district.strip().lower()]
    rollups.sort(key=lambda r: (-r.parcels, r.tenant.name))
    benchmarks = [
        {
            "rank": index,
            "ulbCode": r.tenant.tenant_id,
            "ulbName": r.tenant.name,
            "stateCode": r.tenant.state_code,
            "category": r.tenant.ulb_type or "",
            "district": r.tenant.district or "",
            "population": None,
            "parcels": r.parcels,
            "compositeScore": None,
            "dcbDemand": r.demand,
            "dcbCollection": None,
            "dcbBalance": None,
            "dcbRecoveryPct": None,
            "grievancesTotal": None,
            "grievanceSlaPct": None,
            "avgResolutionDays": None,
            "swachhNationalRank": None,
            "swachhScore": None,
            "gfcStarRating": "",
            "digitalPenetrationPct": None,
            "growthTrajectory": "",
        }
        for index, r in enumerate(rollups, 1)
    ]
    return ApiResponse(
        data=CityComparisonResponse(
            stateTenant=stateTenant or "",
            financialYear=financialYear,
            comparisonPeriod=comparisonPeriod,
            rankingMethod="Parcel Count",
            benchmarks=benchmarks,
            summary={"totalParcelsCovered": sum(r.parcels for r in rollups), "totalCities": len(rollups)},
            unavailableReason=f"{NO_PAYMENTS} {NO_GRIEVANCES} {NO_SWACHH} Cities are ordered by parcel count, not performance.",
            unavailableMetrics=["composite score", "collection", "SLA", "digital penetration", "Swachh rank"],
        )
    )


@router.get("/benchmarks/dcb-recovery", response_model=ApiResponse[DcbRecoveryResponse])
async def get_dcb_recovery(
    financialYear: str = Query(""),
    stateTenant: Optional[str] = Query(None),
    ulbTenant: Optional[str] = Query(None),
    revenueModule: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_read_db),
):
    """ADM-A02 DCB: the demand side only, until payment records exist."""
    modules = _split(revenueModule)
    if modules and PROPERTY_TAX_CODE not in modules:
        return _unavailable(DcbRecoveryResponse, f"No demand records exist for {', '.join(modules)}.", financialYear=financialYear)

    rollups = await _tenant_rollups(db, _split(stateTenant), _split(ulbTenant))
    total = sum(r.demand for r in rollups)
    module_name = await db.scalar(select(ModuleModel.name).where(ModuleModel.code == PROPERTY_TAX_CODE))
    return ApiResponse(
        data=DcbRecoveryResponse(
            financialYear=financialYear,
            totalDemand=total,
            moduleBreakdown=[
                {
                    "moduleCode": PROPERTY_TAX_CODE,
                    "moduleName": module_name or PROPERTY_TAX_CODE,
                    "demand": total,
                    "collection": None,
                    "balance": None,
                    "recoveryPct": None,
                    "trend": "",
                }
            ],
            tenantBreakdown=[
                {
                    "tenantCode": r.tenant.tenant_id,
                    "tenantName": r.tenant.name,
                    "demand": r.demand,
                    "collection": None,
                    "balance": None,
                    "recoveryPct": None,
                    "status": "Not available",
                }
                for r in rollups
            ],
            unavailableReason=NO_PAYMENTS,
            unavailableMetrics=["collection", "balance", "recovery", "monthly trend"],
        )
    )


@router.get("/benchmarks/sla-compliance", response_model=ApiResponse[SlaComplianceResponse])
async def get_sla_compliance():
    return _unavailable(SlaComplianceResponse, NO_GRIEVANCES)


@router.get("/benchmarks/swachh-rankings", response_model=ApiResponse[SwachhRankingsResponse])
async def get_swachh_rankings():
    return _unavailable(SwachhRankingsResponse, NO_SWACHH)


# ADM-A03: Consolidated Financial Ledger


@router.get("/financial/grants-overview", response_model=ApiResponse[GrantsOverviewStats])
async def get_grants_overview():
    return _unavailable(GrantsOverviewStats, NO_LEDGER)


@router.get("/financial/grant-allocations", response_model=ApiResponse[GrantAllocationResponse])
async def get_grant_allocations():
    return _unavailable(GrantAllocationResponse, NO_LEDGER)


@router.post("/financial/grant-allocations", response_model=ApiResponse[GrantAllocationItem], status_code=status.HTTP_201_CREATED)
async def create_grant_allocation(payload: GrantAllocationCreate):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Grant allocations cannot be saved until the Finance & Accounting module has storage for them.",
    )


@router.get("/financial/summary", response_model=ApiResponse[FinancialSummaryStats])
async def get_financial_summary():
    return _unavailable(FinancialSummaryStats, NO_LEDGER)


@router.get("/financial/tenant-ledger", response_model=ApiResponse[TenantLedgerResponse])
async def get_tenant_ledger():
    return _unavailable(TenantLedgerResponse, NO_LEDGER)


@router.get("/financial/reconciliation", response_model=ApiResponse[ReconciliationResponse])
async def get_financial_reconciliation():
    return _unavailable(ReconciliationResponse, NO_LEDGER)
