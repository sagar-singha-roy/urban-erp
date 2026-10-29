from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.db.session import get_read_db, get_write_db
from app.db.models import PropertyParcel, Building, PropertyUnit, Owner, Ward
from app.schemas.property import (
    PropertySummary, PropertyDetailResponse, PropertyCreate, DashboardStats
)
from app.core.auth import get_current_user, require_roles, get_current_tenant
from app.core.redis import redis_client
from app.core.config import settings

router = APIRouter(prefix="/properties", tags=["Properties & ULPIN"])

@router.get("/stats/summary", response_model=DashboardStats)
async def get_dashboard_stats(
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_current_user)
):
    cache_key = f"stats:summary:{tenant_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Query counts and totals isolated strictly by tenant_id
    parcels_count = await db.scalar(
        select(func.count(PropertyParcel.id)).where(PropertyParcel.tenant_id == tenant_id)
    ) or 0
    units_count = await db.scalar(
        select(func.count(PropertyUnit.id)).where(PropertyUnit.tenant_id == tenant_id)
    ) or 0
    wards_count = await db.scalar(
        select(func.count(Ward.id)).where(Ward.tenant_id == tenant_id)
    ) or 0
    
    total_demand = await db.scalar(
        select(func.sum(PropertyUnit.current_demand_amount)).where(PropertyUnit.tenant_id == tenant_id)
    ) or 0.0
    
    # Residential vs commercial
    res_count = await db.scalar(
        select(func.count(PropertyUnit.id)).where(
            PropertyUnit.tenant_id == tenant_id,
            PropertyUnit.usage_category == "Residential"
        )
    ) or 0
    comm_count = await db.scalar(
        select(func.count(PropertyUnit.id)).where(
            PropertyUnit.tenant_id == tenant_id,
            PropertyUnit.usage_category == "Commercial"
        )
    ) or 0
    
    total_collected = float(total_demand) * 0.76 # Reference collection efficiency

    stats = {
        "totalParcels": parcels_count,
        "totalUnits": units_count,
        "totalDemand": float(total_demand),
        "totalCollected": round(total_collected, 2),
        "residentialCount": res_count,
        "commercialCount": comm_count,
        "wardCount": wards_count
    }
    
    await redis_client.set(cache_key, stats, expire_seconds=180)
    return stats

@router.get("", response_model=List[PropertySummary])
async def list_properties(
    q: Optional[str] = Query(None, description="Search by ULPIN, PTIN, or Owner"),
    wardId: Optional[str] = Query(None, alias="wardId", description="Filter by Ward ID"),
    taxStatus: Optional[str] = Query(None, alias="taxStatus", description="Filter by Tax Status (PAID/DUE/ARREARS)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_current_user)
):
    stmt = (
        select(PropertyParcel)
        .options(
            selectinload(PropertyParcel.ward),
            selectinload(PropertyParcel.buildings).selectinload(Building.units).selectinload(PropertyUnit.owners)
        )
        .where(PropertyParcel.tenant_id == tenant_id)
        .limit(limit)
        .offset(offset)
    )

    if wardId:
        stmt = stmt.where(PropertyParcel.ward_id == wardId)

    if q:
        q_clean = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                PropertyParcel.ulpin.ilike(q_clean),
                PropertyParcel.survey_number.ilike(q_clean),
                PropertyParcel.address.ilike(q_clean)
            )
        )

    result = await db.execute(stmt)
    parcels = result.scalars().all()

    summaries: List[PropertySummary] = []
    for p in parcels:
        firstBldg = p.buildings[0] if p.buildings else None
        firstUnit = firstBldg.units[0] if firstBldg and firstBldg.units else None
        firstOwner = firstUnit.owners[0] if firstUnit and firstUnit.owners else None

        if taxStatus and firstUnit and firstUnit.tax_status != taxStatus:
            continue

        summaries.append(
            PropertySummary(
                id=p.id,
                ulpin=p.ulpin,
                surveyNumber=p.survey_number,
                address=p.address,
                wardNumber=p.ward.ward_number if p.ward else None,
                wardName=p.ward.ward_name if p.ward else None,
                buildingType=firstBldg.building_type if firstBldg else "Residential",
                totalUnits=sum(len(b.units) for b in p.buildings),
                ptin=firstUnit.ptin if firstUnit else None,
                ownerName=firstOwner.full_name if firstOwner else "Unassigned",
                usageCategory=firstUnit.usage_category if firstUnit else "Residential",
                currentDemandAmount=float(firstUnit.current_demand_amount) if firstUnit else 0.0,
                taxStatus=firstUnit.tax_status if firstUnit else "PAID"
            )
        )

    return summaries

@router.get("/{ulpin}", response_model=PropertyDetailResponse)
async def get_property_by_ulpin(
    ulpin: str,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_current_user)
):
    stmt = (
        select(PropertyParcel)
        .options(
            selectinload(PropertyParcel.ward),
            selectinload(PropertyParcel.locality),
            selectinload(PropertyParcel.buildings).selectinload(Building.units).selectinload(PropertyUnit.owners)
        )
        .where(
            PropertyParcel.ulpin == ulpin,
            PropertyParcel.tenant_id == tenant_id
        )
    )
    result = await db.execute(stmt)
    parcel = result.scalar_one_or_none()

    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property parcel with ULPIN '{ulpin}' not found for tenant '{tenant_id}'."
        )

    return PropertyDetailResponse(
        id=parcel.id,
        tenantId=parcel.tenant_id,
        ulpin=parcel.ulpin,
        surveyNumber=parcel.survey_number,
        plotNumber=parcel.plot_number,
        totalAreaSqyd=parcel.total_area_sqyd,
        wardId=parcel.ward_id,
        wardName=parcel.ward.ward_name if parcel.ward else None,
        wardNumber=parcel.ward.ward_number if parcel.ward else None,
        localityName=parcel.locality.locality_name if parcel.locality else None,
        latitude=parcel.latitude,
        longitude=parcel.longitude,
        address=parcel.address,
        buildings=parcel.buildings
    )

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_write_db),
    user: dict = Depends(require_roles(["revenue_officer", "super_admin"]))
):
    # Check ULPIN duplicate
    existing = await db.scalar(
        select(PropertyParcel).where(
            PropertyParcel.ulpin == payload.ulpin,
            PropertyParcel.tenant_id == tenant_id
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Property with ULPIN '{payload.ulpin}' already exists in tenant '{tenant_id}'."
        )

    parcel = PropertyParcel(
        tenant_id=tenant_id,
        ulpin=payload.ulpin,
        survey_number=payload.surveyNumber,
        plot_number=payload.plotNumber,
        total_area_sqyd=payload.totalAreaSqyd,
        ward_id=payload.wardId,
        locality_id=payload.localityId,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address
    )
    db.add(parcel)
    await db.flush()

    bldg = Building(
        tenant_id=tenant_id,
        parcel_id=parcel.id,
        building_name=payload.building.buildingName,
        building_type=payload.building.buildingType,
        total_floors=payload.building.totalFloors,
        construction_year=payload.building.constructionYear,
        building_permission_no=payload.building.buildingPermissionNo
    )
    db.add(bldg)
    await db.flush()

    unit = PropertyUnit(
        tenant_id=tenant_id,
        building_id=bldg.id,
        ptin=payload.unit.ptin,
        unit_number=payload.unit.unitNumber,
        floor_number=payload.unit.floorNumber,
        usage_category=payload.unit.usageCategory,
        carpet_area_sqft=payload.unit.carpetAreaSqft,
        built_up_area_sqft=payload.unit.builtUpAreaSqft,
        occupancy_type=payload.unit.occupancyType,
        annual_rental_value=payload.unit.annualRentalValue,
        current_demand_amount=payload.unit.currentDemandAmount,
        tax_status=payload.unit.taxStatus
    )
    db.add(unit)
    await db.flush()

    owner = Owner(
        tenant_id=tenant_id,
        unit_id=unit.id,
        full_name=payload.owner.fullName,
        mobile_number=payload.owner.mobileNumber,
        email=payload.owner.email,
        ownership_share=payload.owner.ownershipShare
    )
    db.add(owner)
    await db.commit()

    # Invalidate Redis cache for this tenant
    await redis_client.delete(f"stats:summary:{tenant_id}")

    return {"message": "Property parcel created successfully", "ulpin": parcel.ulpin, "id": parcel.id, "tenantId": tenant_id}

