from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_read_db, get_write_db
from app.db.models import Tenant, Ward, PropertyParcel, Zone
from app.schemas.tenant import TenantResponse, TenantCreate, TenantSummary
from app.core.auth import get_current_user, get_current_tenant
from app.core.redis import redis_client

router = APIRouter(prefix="/tenants", tags=["SaaS Tenant Management"])

@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_current_user)
):
    """List all registered tenants (ULBs / Municipal Corporations)"""
    stmt = (
        select(
            Tenant.tenant_id,
            Tenant.name,
            Tenant.state_code,
            Tenant.district,
            Tenant.created_at,
            func.count(PropertyParcel.id.distinct()).label("total_parcels"),
            func.count(Ward.id.distinct()).label("total_wards")
        )
        .outerjoin(PropertyParcel, PropertyParcel.tenant_id == Tenant.tenant_id)
        .outerjoin(Ward, Ward.tenant_id == Tenant.tenant_id)
        .group_by(Tenant.tenant_id, Tenant.name, Tenant.state_code, Tenant.district, Tenant.created_at)
        .order_by(Tenant.name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        TenantResponse(
            tenantId=r.tenant_id,
            name=r.name,
            stateCode=r.state_code,
            district=r.district,
            createdAt=r.created_at,
            totalParcels=r.total_parcels,
            totalWards=r.total_wards
        )
        for r in rows
    ]

@router.get("/current", response_model=TenantResponse)
async def get_active_tenant(
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_current_user)
):
    """Retrieve details and metrics of currently active tenant context"""
    tenant = await db.scalar(select(Tenant).where(Tenant.tenant_id == tenant_id))
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found"
        )

    parcels_count = await db.scalar(
        select(func.count(PropertyParcel.id)).where(PropertyParcel.tenant_id == tenant_id)
    ) or 0
    wards_count = await db.scalar(
        select(func.count(Ward.id)).where(Ward.tenant_id == tenant_id)
    ) or 0

    return TenantResponse(
        tenantId=tenant.tenant_id,
        name=tenant.name,
        stateCode=tenant.state_code,
        district=tenant.district,
        createdAt=tenant.created_at,
        totalParcels=parcels_count,
        totalWards=wards_count
    )

@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_write_db),
    user: dict = Depends(get_current_user)
):
    """Provision a new SaaS tenant (ULB / Municipality)"""
    norm_id = payload.tenantId.strip().upper()
    existing = await db.scalar(select(Tenant).where(Tenant.tenant_id == norm_id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with ID '{norm_id}' already exists"
        )

    tenant = Tenant(
        tenant_id=norm_id,
        name=payload.name.strip(),
        state_code=payload.stateCode.strip().upper(),
        district=payload.district.strip()
    )
    db.add(tenant)
    await db.flush()

    # Automatically provision default Zone-1 and Ward-1 for new tenant
    default_zone = Zone(
        tenant_id=norm_id,
        code="ZONE-1",
        name=f"{payload.name} Central Zone"
    )
    db.add(default_zone)
    await db.flush()

    default_ward = Ward(
        tenant_id=norm_id,
        zone_id=default_zone.id,
        ward_number=1,
        ward_name="Ward 1 (Headquarters)",
        councilor_name="Elected Representative"
    )
    db.add(default_ward)
    await db.commit()
    await db.refresh(tenant)

    return TenantResponse(
        tenantId=tenant.tenant_id,
        name=tenant.name,
        stateCode=tenant.state_code,
        district=tenant.district,
        createdAt=tenant.created_at,
        totalParcels=0,
        totalWards=1
    )
