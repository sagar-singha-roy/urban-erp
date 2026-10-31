from typing import List, Optional, Generic, TypeVar, Any
import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

DataT = TypeVar("DataT")

class ApiResponse(CamelModel, Generic[DataT]):
    success: bool = True
    code: int = 2000
    data: DataT

class TenantBase(CamelModel):
    tenantId: str
    name: str
    stateCode: str = "TG"
    district: str

class TenantCreate(CamelModel):
    tenantId: str
    name: str
    stateCode: str = "TG"
    district: str

class TenantResponse(TenantBase):
    createdAt: Optional[datetime.datetime] = None
    totalParcels: Optional[int] = 0
    totalWards: Optional[int] = 0

class TenantSummary(CamelModel):
    tenantId: str
    name: str
    stateCode: str
    district: str

class MasterStateResponse(CamelModel):
    code: str
    name: str
    officialName: str
    defaultSlug: str
    primaryLanguage: str = "English"
    additionalLanguages: List[str] = []
    zone: Optional[str] = None

class DistrictResponse(CamelModel):
    id: str
    stateCode: str
    code: str
    name: str
    headquarters: Optional[str] = None

class CityResponse(CamelModel):
    id: str
    stateCode: str
    districtId: Optional[str] = None
    name: str
    ulbType: str
    ulbCode: str

class StateTenantBase(CamelModel):
    stateName: str
    stateCode: str
    tenantSlug: str
    status: str = "Draft"
    country: str = "India"
    timeZone: str = "Asia/Kolkata"
    primaryLanguage: str = "English"
    additionalLanguages: Optional[List[str]] = []
    officialStateName: Optional[str] = None
    stateEmblemUrl: Optional[str] = None
    stateWebsite: Optional[str] = None
    administrativeEmail: str
    administrativePhone: Optional[str] = None
    address: Optional[str] = None
    effectiveDate: Optional[str] = None
    notes: Optional[str] = None

class StateTenantCreate(StateTenantBase):
    pass

class StateTenantUpdate(CamelModel):
    stateName: Optional[str] = None
    stateCode: Optional[str] = None
    tenantSlug: Optional[str] = None
    status: Optional[str] = None
    country: Optional[str] = None
    timeZone: Optional[str] = None
    primaryLanguage: Optional[str] = None
    additionalLanguages: Optional[List[str]] = None
    officialStateName: Optional[str] = None
    stateEmblemUrl: Optional[str] = None
    stateWebsite: Optional[str] = None
    administrativeEmail: Optional[str] = None
    administrativePhone: Optional[str] = None
    address: Optional[str] = None
    effectiveDate: Optional[str] = None
    notes: Optional[str] = None

class StateTenantResponse(StateTenantBase):
    tenantId: str
    createdAt: Optional[datetime.datetime] = None
    updatedAt: Optional[datetime.datetime] = None

class TenantAuditLogResponse(CamelModel):
    id: str
    tenantId: str
    action: str
    performedBy: str
    timestamp: datetime.datetime
    details: Optional[str] = None
    ipAddress: Optional[str] = None
