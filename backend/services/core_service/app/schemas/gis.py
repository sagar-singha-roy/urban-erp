import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.schemas.tenant import CamelModel


class GisWorkspacePayload(CamelModel):
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


class GisWorkspaceResponse(GisWorkspacePayload):
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
    tenantName: str = ""
    stateCode: str = ""
    featureCount: int = 0
    lastSyncedAt: Optional[datetime.datetime] = None


class GisImportPayload(CamelModel):
    sourceCrs: str
    featureCollection: Dict[str, Any]


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
