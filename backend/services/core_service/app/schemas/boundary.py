from typing import Optional

from app.schemas.tenant import CamelModel


class WardResponse(CamelModel):
    id: str
    zoneId: str
    wardNumber: int
    wardName: str
    councilorName: Optional[str] = None
    totalProperties: int = 0
