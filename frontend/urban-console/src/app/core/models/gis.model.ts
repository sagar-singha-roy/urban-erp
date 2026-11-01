export interface GisCode {
  code: string;
  name: string;
  stateCode?: string;
  district?: string;
}

export interface GisBaseMap extends GisCode {
  url: string;
  attribution: string;
  maxZoom: number;
}

export interface GisNamedRef {
  id: string;
  name: string;
  zoneId?: string;
}

export interface GisOptions {
  states: GisCode[];
  ulbs: GisCode[];
  districts: string[];
  wards: GisNamedRef[];
  zones: GisNamedRef[];
  baseMaps: GisBaseMap[];
  crsOptions: GisCode[];
  geographicScopes: string[];
  refreshIntervals: string[];
  layerCategories: string[];
  layerTypes: string[];
  dataSources: string[];
  layerStatuses: string[];
  boundaryLevels: string[];
  utilityCategories: string[];
  utilityNetworkTypes: string[];
  assetStatuses: string[];
  roadCategories: string[];
  roadStatuses: string[];
  roadSurfaces: string[];
  parcelCategories: string[];
  parcelStatuses: string[];
}

export interface GisLayerStyle {
  color?: string;
  weight?: number;
  fillOpacity?: number;
}

export interface GisLayer {
  id?: string;
  tenantId: string;
  tenantName?: string;
  stateCode?: string;
  layerName: string;
  layerCode: string;
  layerCategory: string;
  layerType: string;
  dataSource: string;
  serviceUrl?: string | null;
  workspaceName?: string | null;
  layerIdentifier?: string | null;
  crs: string;
  defaultVisibility: boolean;
  opacity: number;
  layerStyle: GisLayerStyle;
  layerStatus: string;
  utilityCategory?: string | null;
  networkType?: string | null;
  department?: string | null;
  featureCount?: number;
  lastSyncedAt?: string | null;
}

export interface GisScopeRow {
  tenantId: string;
  tenantName: string;
  stateCode: string;
  district: string;
  status: string;
  wardCount: number;
  wardBoundaryCount: number;
  parcelCount: number;
  layerCount: number;
  lastSyncedAt: string | null;
}

export interface GisWorkspace {
  id?: string;
  workspaceName: string;
  geographicScope: string;
  stateTenants: string[];
  ulbTenants: string[];
  mapExtent: number[] | null;
  baseMap: string;
  crs: string;
  defaultZoom: number | null;
  defaultCentre: number[] | null;
  visibleLayers: string[];
  refreshInterval: string;
  updatedAt?: string;
}

export interface GisFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSON.Feature[];
  truncated?: boolean;
  unmapped?: number;
}

export interface GisImportResult {
  imported: number;
  rejected: number;
}
