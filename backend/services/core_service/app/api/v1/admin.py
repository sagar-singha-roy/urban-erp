from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_read_db, get_write_db
from app.db.models import StateTenant, Tenant, Ward, PropertyParcel, PropertyUnit, User
from app.core.auth import get_current_user, require_roles
from app.core.redis import redis_client
from app.schemas.property import CamelModel

router = APIRouter(prefix="/admin", tags=["Super Admin Platform Management"])

class GlobalKPIs(CamelModel):
    total_states: int
    total_ulbs: int
    total_parcels: int
    total_revenue_demand: float
    total_revenue_collected: Optional[float] = None
    collection_efficiency: Optional[float] = None
    total_active_users: int
    system_health_pct: Optional[float] = None

class StateBenchmark(CamelModel):
    state_code: str
    state_name: str
    ulb_count: int
    parcels: int
    demand_amount: float
    collection_pct: Optional[float] = None
    status: str

@router.get("/overview", response_model=GlobalKPIs)
async def get_global_overview(
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(require_roles(["super_admin"]))
):
    """Aggregate macro KPIs across all States and ULBs."""
    ulb_count = await db.scalar(select(func.count(Tenant.tenant_id))) or 0
    parcels_count = await db.scalar(select(func.count(PropertyParcel.id))) or 0
    demand_val = float(await db.scalar(select(func.sum(PropertyUnit.current_demand_amount))) or 0.0)
    user_count = await db.scalar(select(func.count(User.id))) or 0

    return GlobalKPIs(
        total_states=await db.scalar(select(func.count(StateTenant.id))) or 0,
        total_ulbs=ulb_count,
        total_parcels=parcels_count,
        total_revenue_demand=demand_val,
        total_active_users=user_count
    )

@router.get("/benchmarks", response_model=List[StateBenchmark])
async def get_state_benchmarks(
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(require_roles(["super_admin"]))
):
    """Return per-state record totals from the tenant registry."""
    states = (await db.scalars(select(StateTenant).order_by(StateTenant.state_name))).all()
    benchmarks = []
    for state in states:
        tenant_ids = (await db.scalars(select(Tenant.tenant_id).where(Tenant.state_code == state.state_code))).all()
        parcels = await db.scalar(select(func.count(PropertyParcel.id)).where(PropertyParcel.tenant_id.in_(tenant_ids))) or 0
        demand = await db.scalar(select(func.sum(PropertyUnit.current_demand_amount)).where(PropertyUnit.tenant_id.in_(tenant_ids))) or 0
        benchmarks.append(
            StateBenchmark(
                state_code=state.state_code,
                state_name=state.state_name,
                ulb_count=len(tenant_ids),
                parcels=parcels,
                demand_amount=float(demand),
                status=state.status,
            )
        )
    return benchmarks

@router.get("/cluster/health")
async def get_cluster_health(
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(require_roles(["super_admin"]))
):
    """Connectivity actually measured by this service instance."""
    await db.execute(select(1))
    return {
        "status": "HEALTHY" if redis_client.redis else "DEGRADED",
        "database": "CONNECTED",
        "redisCache": "CONNECTED" if redis_client.redis else "NOT_CONNECTED",
    }
