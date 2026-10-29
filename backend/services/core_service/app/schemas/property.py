from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class OwnerBase(CamelModel):
    fullName: str
    mobileNumber: str
    email: Optional[str] = None
    ownershipShare: float = 100.0

class OwnerResponse(OwnerBase):
    id: str

class UnitBase(CamelModel):
    ptin: str
    unitNumber: str
    floorNumber: int = 0
    usageCategory: str
    carpetAreaSqft: float
    builtUpAreaSqft: float
    occupancyType: str = "Owner"
    annualRentalValue: float = 0.0
    currentDemandAmount: float = 0.0
    taxStatus: str = "PAID"

class UnitResponse(UnitBase):
    id: str
    owners: List[OwnerResponse] = []

class BuildingBase(CamelModel):
    buildingName: Optional[str] = None
    buildingType: str
    totalFloors: int = 1
    constructionYear: Optional[int] = None
    buildingPermissionNo: Optional[str] = None

class BuildingResponse(BuildingBase):
    id: str
    units: List[UnitResponse] = []

class PropertyCreate(CamelModel):
    ulpin: str
    surveyNumber: str
    plotNumber: Optional[str] = None
    totalAreaSqyd: float
    wardId: str
    localityId: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str
    building: BuildingBase
    unit: UnitBase
    owner: OwnerBase

class PropertySummary(CamelModel):
    id: str
    ulpin: str
    surveyNumber: str
    address: str
    wardNumber: Optional[int] = None
    wardName: Optional[str] = None
    buildingType: Optional[str] = None
    totalUnits: int = 0
    ptin: Optional[str] = None
    ownerName: Optional[str] = None
    usageCategory: Optional[str] = None
    currentDemandAmount: float = 0.0
    taxStatus: Optional[str] = None

class PropertyDetailResponse(CamelModel):
    id: str
    tenantId: str
    ulpin: str
    surveyNumber: str
    plotNumber: Optional[str] = None
    totalAreaSqyd: float
    wardId: str
    wardName: Optional[str] = None
    wardNumber: Optional[int] = None
    localityName: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str
    buildings: List[BuildingResponse] = []

class WardResponse(CamelModel):
    id: str
    zoneId: str
    wardNumber: int
    wardName: str
    councilorName: Optional[str] = None
    totalProperties: int = 0

class DashboardStats(CamelModel):
    totalParcels: int
    totalUnits: int
    totalDemand: float
    totalCollected: float
    residentialCount: int
    commercialCount: int
    wardCount: int

