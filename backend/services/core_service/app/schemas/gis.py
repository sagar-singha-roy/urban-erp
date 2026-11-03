import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from app.schemas.tenant import CamelModel


class GisWorkspaceFields(CamelModel):
    workspaceName: Optional[str] = Field(default=None, max_length=150)
    geographicScope: str
    stateTenants: List[str] = []
    ulbTenants: List[str] = []
    mapExtent: Optional[List[float]] = None
    baseMap: str
    crs: str
    defaultZoom: Optional[int] = Field(default=None, ge=1, le=20)
    defaultCentre: Optional[List[float]] = None
    visibleLayers: List[str] = []
    refreshInterval: Optional[str] = None


class GisWorkspacePayload(GisWorkspaceFields):
    @field_validator("mapExtent")
    @classmethod
    def extent_order(cls, value):
        if value is None:
            return value
        if len(value) != 4 or not (-180 <= value[0] < value[2] <= 180 and -90 <= value[1] < value[3] <= 90):
            raise ValueError("Map extent must be west, south, east, north in degrees.")
        return value

    @field_validator("defaultCentre")
    @classmethod
    def centre_range(cls, value):
        if value is None:
            return value
        if len(value) != 2 or not (-90 <= value[0] <= 90 and -180 <= value[1] <= 180):
            raise ValueError("Map centre must be latitude, longitude in degrees.")
        return value


# Already stored, so an older saved value must not stop the list loading.
class GisWorkspaceResponse(GisWorkspaceFields):
    id: str
    updatedAt: Optional[datetime.datetime] = None


class GisLayerPayload(CamelModel):
    tenantId: str
    layerName: str = Field(min_length=1, max_length=150)
    layerCode: str = Field(min_length=1, max_length=60)
    layerCategory: str
    layerType: str
    dataSource: str
    serviceUrl: Optional[str] = Field(default=None, max_length=500)
    workspaceName: Optional[str] = Field(default=None, max_length=150)
    layerIdentifier: Optional[str] = Field(default=None, max_length=150)
    crs: str
    defaultVisibility: bool = True
    opacity: float = Field(default=1.0, ge=0, le=1)
    layerStyle: Dict[str, Any] = {}
    layerStatus: str
    utilityCategory: Optional[str] = None
    networkType: Optional[str] = None
    department: Optional[str] = None


class GisLayerResponse(GisLayerPayload):
    id: str
    serviceApproved: bool = True
    tenantName: str = ""
    stateCode: str = ""
    featureCount: int = 0
    lastSyncedAt: Optional[datetime.datetime] = None


class GisImportPayload(CamelModel):
    sourceCrs: str
    featureCollection: Dict[str, Any]


class GisBoundaryImportPayload(CamelModel):
    tenantId: str
    level: str
    matchField: str = Field(min_length=1, max_length=60)
    sourceCrs: str
    featureCollection: Dict[str, Any]


class GisServicePayload(CamelModel):
    tenantId: str
    serviceName: str = Field(min_length=1, max_length=150)
    baseUrl: str = Field(min_length=1, max_length=500)
    isActive: bool = True


class GisServiceResponse(GisServicePayload):
    id: str


class GisImportResult(CamelModel):
    imported: int
    rejected: int


class GisScopeRow(CamelModel):
    tenantId: str
    tenantName: str
    stateCode: str
    district: str = ""
    status: str = ""
    wardCount: int = 0
    wardBoundaryCount: int = 0
    parcelCount: int = 0
    layerCount: int = 0
    lastSyncedAt: Optional[datetime.datetime] = None


class GisOptions(CamelModel):
    states: List[Dict[str, str]] = []
    ulbs: List[Dict[str, str]] = []
    districts: List[str] = []
    wards: List[Dict[str, str]] = []
    zones: List[Dict[str, str]] = []
    baseMaps: List[Dict[str, Any]] = []
    crsOptions: List[Dict[str, Any]] = []
    geographicScopes: List[str] = []
    refreshIntervals: List[str] = []
    layerCategories: List[str] = []
    layerTypes: List[str] = []
    dataSources: List[str] = []
    layerStatuses: List[str] = []
    boundaryLevels: List[str] = []
    utilityCategories: List[str] = []
    utilityNetworkTypes: List[str] = []
    assetStatuses: List[str] = []
    roadCategories: List[str] = []
    roadStatuses: List[str] = []
    roadSurfaces: List[str] = []
    parcelCategories: List[str] = []
    parcelStatuses: List[str] = []
    surveyStatuses: List[str] = []
