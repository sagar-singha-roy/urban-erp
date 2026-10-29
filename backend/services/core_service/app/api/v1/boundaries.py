from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.session import get_read_db
from app.db.models import Ward, Zone, PropertyParcel
from app.schemas.property import WardResponse
from app.core.auth import get_current_user, get_current_tenant
from app.core.redis import redis_client

router = APIRouter(prefix="/boundaries", tags=["Boundaries & Wards"])

@router.get("/wards", response_model=List[WardResponse])
async def list_wards(
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_current_user)
):
    cache_key = f"boundaries:wards:{tenant_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Query wards with property count isolated strictly by tenant_id
    stmt = (
        select(
            Ward.id,
            Ward.zone_id,
            Ward.ward_number,
            Ward.ward_name,
            Ward.councilor_name,
            func.count(PropertyParcel.id).label("total_properties")
        )
        .outerjoin(
            PropertyParcel,
            and_(PropertyParcel.ward_id == Ward.id, PropertyParcel.tenant_id == tenant_id)
        )
        .where(Ward.tenant_id == tenant_id)
        .group_by(Ward.id, Ward.zone_id, Ward.ward_number, Ward.ward_name, Ward.councilor_name)
        .order_by(Ward.ward_number)
    )

    result = await db.execute(stmt)
    rows = result.all()

    ward_list = [
        WardResponse(
            id=r.id,
            zoneId=r.zone_id,
            wardNumber=r.ward_number,
            wardName=r.ward_name,
            councilorName=r.councilor_name,
            totalProperties=r.total_properties
        )
        for r in rows
    ]

    await redis_client.set(cache_key, [w.model_dump(by_alias=True) for w in ward_list], expire_seconds=600)
    return ward_list
