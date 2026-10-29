from typing import List, Optional
import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

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
