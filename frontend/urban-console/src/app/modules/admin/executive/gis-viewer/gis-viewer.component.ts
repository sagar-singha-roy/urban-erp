import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable, defer, finalize, map } from 'rxjs';
import { DataNoticeComponent } from '../../../../shared/components/data-notice/data-notice.component';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { WlPaginationComponent } from '../../../../shared/components/wl-pagination/wl-pagination.component';
import { DialogService } from '../../../../core/services/dialog.service';
import { GisService } from '../../../../core/services/gis.service';
import {
  GisApprovedService,
  GisFeatureCollection,
  GisImportResult,
  GisLayer,
  GisOptions,
  GisParcelFilter,
  GisRoadFilter,
  GisScopeRow,
  GisUtilityFilter,
  GisWorkspace,
} from '../../../../core/models/gis.model';
import { GisCesiumMap, MapOverlay } from './gis-cesium-map';
import { GisImportDialogComponent } from './dialogs/gis-import-dialog.component';
import { GisBoundaryDialogComponent } from './dialogs/gis-boundary-dialog.component';
import { GisLayerDialogComponent } from './dialogs/gis-layer-dialog.component';
import { GisServiceDialogComponent } from './dialogs/gis-service-dialog.component';
import { GisParcelsTabComponent } from './tabs/gis-parcels-tab.component';
import { GisRoadsTabComponent } from './tabs/gis-roads-tab.component';
import { GisUtilitiesTabComponent } from './tabs/gis-utilities-tab.component';
import { GisMultiSelectComponent } from './gis-multi-select.component';

type GisTab = 'overview' | 'state' | 'city' | 'parcels' | 'utilities' | 'roads';

const EMPTY_OPTIONS: GisOptions = {
  states: [], ulbs: [], districts: [], wards: [], zones: [], baseMaps: [], crsOptions: [], geographicScopes: [],
  refreshIntervals: [], layerCategories: [], layerTypes: [], dataSources: [], layerStatuses: [], boundaryLevels: [],
  utilityCategories: [], utilityNetworkTypes: [], assetStatuses: [], roadCategories: [], roadStatuses: [],
  roadSurfaces: [], parcelCategories: [], parcelStatuses: [], surveyStatuses: [],
};
const REFRESH_MS: Record<string, number> = { '1 minute': 60000, '5 minutes': 300000, '15 minutes': 900000 };

@Component({
  selector: 'app-gis-viewer',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent,
    DataNoticeComponent,
    RefreshButtonComponent,
    WlPaginationComponent,
    GisBoundaryDialogComponent,
    GisServiceDialogComponent,
    GisParcelsTabComponent,
    GisUtilitiesTabComponent,
    GisRoadsTabComponent,
    GisLayerDialogComponent,
    GisImportDialogComponent,
    GisMultiSelectComponent,
  ],
  templateUrl: './gis-viewer.component.html',
  styleUrl: './gis-viewer.component.scss',
})
export class GisViewerComponent implements OnInit, AfterViewInit, OnDestroy {
  private gis = inject(GisService);
  private dialogs = inject(DialogService);

  @ViewChild('mapHost') mapHost?: ElementRef<HTMLDivElement>;
  @ViewChild('mapPanel') mapPanel?: ElementRef<HTMLElement>;
  private map?: GisCesiumMap;
  private refreshTimer?: ReturnType<typeof setInterval>;

  readonly tabs: { id: GisTab; label: string; icon: string }[] = [
    { id: 'overview', label: 'Map Overview', icon: 'ri-map-2-line' },
    { id: 'state', label: 'State Selection', icon: 'ri-road-map-line' },
    { id: 'city', label: 'City Layers', icon: 'ri-stack-line' },
    { id: 'parcels', label: 'Parcel Layers', icon: 'ri-layout-grid-line' },
    { id: 'utilities', label: 'Utility Networks', icon: 'ri-flashlight-line' },
    { id: 'roads', label: 'Zone & Road Layers', icon: 'ri-route-line' },
  ];
  readonly activeTab = signal<GisTab>('overview');
  readonly options = signal<GisOptions>(EMPTY_OPTIONS);
  readonly layers = signal<GisLayer[]>([]);
  readonly scope = signal<GisScopeRow[]>([]);
  readonly workspaces = signal<GisWorkspace[]>([]);
  readonly notice = signal('');
  readonly legend = signal<{ key: string; label: string; color: string; count: number | null }[]>([]);
  readonly isLoadingMap = signal(false);
  readonly is3d = signal(false);
  readonly cursor = signal('Move over the map');
  private pendingRequests = 0;
  readonly featureSummary = signal('');
  readonly layerDialog = signal<{ layer: GisLayer | null; category: string } | null>(null);
  readonly importLayer = signal<GisLayer | null>(null);
  readonly serviceDialog = signal<{ service: GisApprovedService | null } | null>(null);
  readonly boundaryDialog = signal(false);
  readonly services = signal<GisApprovedService[]>([]);
  readonly syncingId = signal<string | null>(null);
  readonly pickMode = signal<'centre' | 'extent' | null>(null);
  readonly clicked = signal('');
  extentFirst: { lat: number; lng: number } | null = null;
  includeParcels = false;

  // Server-side lists
  readonly cityLayers = signal<GisLayer[]>([]);
  readonly cityTotal = signal(0);
  readonly cityPage = signal(1);
  readonly cityLimit = signal(10);
  readonly citySearch = signal('');
  readonly scopeTotal = signal(0);
  readonly scopePage = signal(1);
  readonly scopeLimit = signal(10);
  readonly scopeSearch = signal('');

  /** Overlays cut off by the feature limit, with how to fetch them for the area on screen. */
  private viewportFetchers = new Map<string, (bbox: string) => void>();
  private moveTimer?: ReturnType<typeof setTimeout>;

  workspace: GisWorkspace = {
    workspaceName: '',
    geographicScope: '',
    stateTenants: [],
    ulbTenants: [],
    mapExtent: null,
    baseMap: 'osm',
    crs: 'EPSG:4326',
    defaultZoom: null,
    defaultCentre: null,
    visibleLayers: [],
    refreshInterval: 'Manual',
  };
  extentText = '';
  centreText = '';
  selectedWorkspaceId = '';

  stateFilter = { stateTenants: [] as string[], districts: [] as string[], ulbTenants: [] as string[], boundaryLevel: 'Ward', boundaryStatus: '', source: 'PostGIS', visible: true };
  parcelFilter: GisParcelFilter = { state: '', tenantId: '', wards: [], categories: [], statuses: [], surveyStatus: '', gisStatus: 'mapped', dataSource: 'PostGIS', layerId: '', boundaryDisplay: true, labelField: 'ulpin', search: '' };
  utilityFilter: GisUtilityFilter = { state: '', tenantId: '', categories: [], networkType: '', layerId: '', assetStatuses: [], department: '', dataSource: 'PostGIS', visible: true, color: '#0891b2' };
  roadFilter: GisRoadFilter = { state: '', tenantId: '', zones: [], wards: [], categories: [], status: '', roadLayerId: '', zoneLayerId: '', dataSource: 'PostGIS', minWidth: null, maxWidth: null, surfaces: [], visible: true };
  cityFilter = { state: '', tenantId: '' };

  ngOnInit(): void {
    this.loadOptions();
    this.loadLayers();
    this.loadCityLayers();
    this.loadServices();
    this.loadWorkspaces();
    this.loadScope();
  }

  ngAfterViewInit(): void {
    if (!this.mapHost) return;
    this.map = new GisCesiumMap(this.mapHost.nativeElement, {
      onPointerMove: (lat, lng) => this.cursor.set(`${lat.toFixed(5)}, ${lng.toFixed(5)}`),
      onClick: (lat, lng) => this.onMapClick(lat, lng),
      onViewChanged: (bbox) => this.onMapMoved(bbox),
      onError: (message) => this.notice.set(message),
    });
    this.applyBaseMap();
    this.isLoadingMap.set(true);
    this.map
      .start()
      .catch(() => this.notice.set('The map could not start. It needs a browser and device with WebGL turned on.'))
      .finally(() => this.isLoadingMap.set(this.pendingRequests > 0));
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    clearTimeout(this.moveTimer);
    this.map?.destroy();
  }

  // Data
  loadOptions(tenantId?: string): void {
    this.gis.getOptions(tenantId).subscribe({
      next: (options) => {
        this.options.set(options);
        if (!this.workspace.geographicScope) this.workspace.geographicScope = options.geographicScopes[0] ?? '';
        this.applyBaseMap();
      },
      error: () => this.notice.set('GIS filter options could not be loaded.'),
    });
  }

  /** Every accessible layer, for the dropdowns on each tab. */
  loadLayers(): void {
    this.gis.getAllLayers().subscribe({
      next: (layers) => this.layers.set(layers),
      error: () => this.notice.set('GIS layers could not be loaded.'),
    });
  }

  loadCityLayers(): void {
    this.gis
      .getLayersPage({ tenantId: this.cityFilter.tenantId, search: this.citySearch(), skip: (this.cityPage() - 1) * this.cityLimit(), limit: this.cityLimit() })
      .subscribe({
        next: (page) => {
          this.cityLayers.set(page.data);
          this.cityTotal.set(page.total);
        },
        error: () => this.notice.set('GIS layers could not be loaded.'),
      });
  }

  loadServices(): void {
    this.gis.getServices({ tenantId: this.cityFilter.tenantId, limit: 100 }).subscribe({
      next: (page) => this.services.set(page.data),
      error: () => this.notice.set('Approved services could not be loaded.'),
    });
  }

  private scopeFilters(): Record<string, unknown> {
    return {
      stateTenants: this.stateFilter.stateTenants,
      districts: this.stateFilter.districts,
      ulbTenants: this.stateFilter.ulbTenants,
      boundaryStatus: this.stateFilter.boundaryStatus,
    };
  }

  loadScope(): void {
    this.gis
      .getScopePage({ ...this.scopeFilters(), search: this.scopeSearch(), skip: (this.scopePage() - 1) * this.scopeLimit(), limit: this.scopeLimit() })
      .subscribe({
        next: (page) => {
          this.scope.set(page.data);
          this.scopeTotal.set(page.total);
        },
        error: () => this.notice.set('Administrative scope could not be loaded.'),
      });
  }

  loadWorkspaces(): void {
    this.gis.getWorkspaces().subscribe({
      next: (rows) => this.workspaces.set(rows),
      error: () => this.notice.set('Saved workspaces could not be loaded.'),
    });
  }

  refreshAll(): void {
    this.loadOptions();
    this.loadLayers();
    this.loadCityLayers();
    this.loadServices();
    this.loadScope();
    this.loadWorkspaces();
  }

  ulbsFor(state: string): GisOptions['ulbs'] {
    return this.options().ulbs.filter((u) => !state || u.stateCode === state);
  }

  layersFor(tenantId: string, category?: string): GisLayer[] {
    return this.layers().filter((l) => l.tenantId === tenantId && (!category || l.layerCategory === category));
  }

  onTenantChange(tenantId: string): void {
    if (tenantId) this.loadOptions(tenantId);
  }

  // Map
  applyBaseMap(): void {
    const base = this.options().baseMaps.find((b) => b.code === this.workspace.baseMap);
    if (base) this.map?.setBaseMap(base);
  }

  private setOverlay(key: string, overlay: MapOverlay | null, count: number | null = null): void {
    this.map?.setOverlay(key, overlay);
    this.legend.update((items) => items.filter((item) => item.key !== key));
    if (overlay) {
      this.legend.update((items) => [...items, { key, label: overlay.label, color: overlay.color, count }]);
    } else {
      this.viewportFetchers.delete(key);
    }
  }

  toggle3d(): void {
    this.is3d.update((value) => !value);
    this.map?.setMode(this.is3d());
  }

  zoom(direction: 'in' | 'out'): void {
    this.map?.zoomBy(direction);
  }

  removeOverlay(key: string): void {
    this.setOverlay(key, null);
  }

  /** Same calls as GisService, with the map's loading bar shown while they run. */
  private readonly mapRequest = {
    getFeatures: (filters: Record<string, unknown>) => this.withLoading(this.gis.getFeatures(filters)),
    getParcels: (filters: Record<string, unknown>) => this.withLoading(this.gis.getParcels(filters)),
    getBoundaries: (tenantId: string, level: string) => this.withLoading(this.gis.getBoundaries(tenantId, level)),
    getScopeFeatures: (filters: Record<string, unknown>) => this.withLoading(this.gis.getScopeFeatures(filters)),
  };

  private withLoading<T>(request: Observable<T>): Observable<T> {
    return defer(() => {
      this.pendingRequests += 1;
      this.isLoadingMap.set(true);
      return request.pipe(
        finalize(() => {
          this.pendingRequests = Math.max(0, this.pendingRequests - 1);
          this.isLoadingMap.set(this.pendingRequests > 0);
        }),
      );
    });
  }

  resetView(): void {
    this.map?.goHome();
  }

  fitToData(): void {
    if (!this.map?.fitAll()) {
      this.dialogs.showToast('Nothing on the map to fit to yet.', 'info', 2500);
    }
  }

  toggleFullscreen(): void {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void this.mapPanel?.nativeElement.requestFullscreen();
    }
  }

  private drawCollection(key: string, label: string, collection: GisFeatureCollection, color: string, labelField?: string, fit = true): void {
    this.setOverlay(key, { label, color, labelField, collection }, collection.features.length);
    if (fit) this.map?.fitCollection(collection);
    const count = collection.features.length;
    this.featureSummary.set(`${count} feature${count === 1 ? '' : 's'} shown${collection.truncated ? ' (limit reached, zoom in for more)' : ''}.`);
  }

  /** Draws a query, and if the limit cut it off, fetches again for the area on screen after each move. */
  private drawQuery(key: string, label: string, color: string, labelField: string | undefined, fetch: (bbox?: string) => Observable<GisFeatureCollection>, fallback: string, fit = true): void {
    fetch().subscribe({
      next: (collection) => {
        this.drawCollection(key, label, collection, color, labelField, fit);
        if (collection.truncated) {
          this.viewportFetchers.set(key, (bbox) =>
            fetch(bbox).subscribe({
              next: (visible) => this.drawCollection(key, label, visible, color, labelField, false),
              error: (err) => this.showError(err, fallback),
            }),
          );
        } else {
          this.viewportFetchers.delete(key);
        }
      },
      error: (err) => this.showError(err, fallback),
    });
  }

  private onMapMoved(bbox: string): void {
    clearTimeout(this.moveTimer);
    this.moveTimer = setTimeout(() => this.viewportFetchers.forEach((run) => run(bbox)), 400);
  }

  private onMapClick(lat: number, lng: number): boolean {
    const mode = this.pickMode();
    if (mode === 'centre') {
      this.centreText = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      this.pickMode.set(null);
      return true;
    }
    if (mode === 'extent') {
      if (!this.extentFirst) {
        this.extentFirst = { lat, lng };
        return true;
      }
      const a = this.extentFirst;
      this.extentText = [Math.min(a.lng, lng), Math.min(a.lat, lat), Math.max(a.lng, lng), Math.max(a.lat, lat)].map((v) => v.toFixed(5)).join(', ');
      this.extentFirst = null;
      this.pickMode.set(null);
      return true;
    }
    this.showClickedCoordinates(lat, lng);
    return false;
  }

  startPick(mode: 'centre' | 'extent'): void {
    this.extentFirst = null;
    this.pickMode.set(this.pickMode() === mode ? null : mode);
  }

  /** The 2D map is always Web Mercator. The chosen CRS decides the coordinates people read and export. */
  private showClickedCoordinates(lat: number, lng: number): void {
    const crs = this.workspace.crs;
    if (!crs || crs === 'EPSG:4326') {
      this.clicked.set('');
      return;
    }
    this.gis.transform(lng, lat, crs).subscribe({
      next: (result) => this.clicked.set(`${crs}: ${result.x.toFixed(2)}, ${result.y.toFixed(2)}`),
      error: () => this.clicked.set(''),
    });
  }

  private showError(err: { error?: { detail?: unknown } }, fallback: string): void {
    const detail = err?.error?.detail;
    this.dialogs.showToast(typeof detail === 'string' ? detail : fallback, 'error', 3500);
  }

  private showWms(layer: GisLayer): void {
    if (!layer.id) return;
    if (layer.serviceApproved === false || !layer.serviceUrl) {
      this.dialogs.showToast(`The service for ${layer.layerName} is not approved.`, 'error', 3500);
      return;
    }
    this.setOverlay(layer.id, {
      label: layer.layerName,
      color: layer.layerStyle?.color ?? '#2563eb',
      wms: { url: layer.serviceUrl, layers: layer.layerIdentifier!, opacity: layer.opacity ?? 1 },
    });
  }

  /** WFS layers are read from their PostGIS copy, which the server has cut to this ULB. */
  toggleLayer(layer: GisLayer, visible: boolean, fit = true): void {
    if (!layer.id) return;
    if (!visible) {
      this.setOverlay(layer.id, null);
      return;
    }
    if (layer.dataSource === 'WMS') {
      this.showWms(layer);
      return;
    }
    if (layer.dataSource === 'WFS' && !layer.lastSyncedAt) {
      this.dialogs.showToast(`Sync ${layer.layerName} before showing it.`, 'info', 3000);
      return;
    }
    this.drawQuery(
      layer.id, layer.layerName, layer.layerStyle?.color ?? '#2563eb', undefined,
      (bbox) => this.mapRequest.getFeatures({ tenantId: layer.tenantId, layerIds: [layer.id], bbox }),
      'This layer could not be loaded.', fit,
    );
  }

  syncLayer(layer: GisLayer): void {
    if (!layer.id) return;
    this.syncingId.set(layer.id);
    this.gis.syncLayer(layer.id).subscribe({
      next: (result) => {
        this.syncingId.set(null);
        this.dialogs.showToast(`${result.imported} features stored, ${result.rejected} outside this ULB or invalid.`, result.rejected ? 'warning' : 'success', 4000);
        this.loadLayers();
        this.loadCityLayers();
      },
      error: (err) => {
        this.syncingId.set(null);
        this.showError(err, 'This layer could not be synchronised.');
      },
    });
  }

  isOnMap(layer: GisLayer): boolean {
    return !!layer.id && !!this.map?.hasOverlay(layer.id);
  }

  showState(): void {
    this.scopePage.set(1);
    this.loadScope();
    const f = this.stateFilter;
    this.setOverlay('boundaries', null);
    if (!f.visible) return;
    // Asks the server afresh, so the map follows these filters and not the previous results.
    this.withLoading(this.gis.getScopePage({ ...this.scopeFilters(), limit: 100 })).subscribe({
      next: (page) => {
        const label = `${f.boundaryLevel} boundaries`;
        const merged: GisFeatureCollection = { type: 'FeatureCollection', features: [] };
        if (!page.data.length) {
          this.featureSummary.set('No ULBs match this selection.');
          return;
        }
        page.data.forEach((row) => {
          const request = f.source === 'PostGIS'
            ? this.mapRequest.getBoundaries(row.tenantId, f.boundaryLevel)
            : this.mapRequest.getFeatures({ tenantId: row.tenantId, category: ['Boundary'], dataSource: f.source });
          request.subscribe({
            next: (collection) => {
              merged.features.push(...collection.features);
              const styled = merged.features.map((feature) => ({ ...feature, properties: { ...feature.properties, _style: { color: '#7c3aed', weight: 2, fillOpacity: 0.05 } } }));
              this.setOverlay('boundaries', { label, color: '#7c3aed', labelField: 'name', collection: { type: 'FeatureCollection', features: styled } }, merged.features.length);
              this.featureSummary.set(merged.features.length ? `${merged.features.length} boundaries shown.` : `No boundary data at ${f.boundaryLevel} level yet. Import boundaries under City Layers.`);
            },
            error: (err) => this.showError(err, 'Boundaries could not be loaded.'),
          });
        });
      },
      error: (err) => this.showError(err, 'Boundaries could not be loaded.'),
    });
  }

  showParcels(): void {
    const f = this.parcelFilter;
    if (!f.tenantId) {
      this.dialogs.showToast('Choose a ULB / city first.', 'info', 2500);
      return;
    }
    const layer = this.layers().find((l) => l.id === f.layerId);
    if (f.dataSource !== 'PostGIS') {
      this.setOverlay('parcels', null);
      if (!layer) {
        this.dialogs.showToast('Choose a parcel layer from this data source.', 'info', 2500);
        return;
      }
      this.toggleLayer(layer, true);
      return;
    }
    const filters = { tenantId: f.tenantId, wards: f.wards, categories: f.categories, statuses: f.statuses, surveyStatus: f.surveyStatus, gisStatus: f.gisStatus, search: f.search, boundaryDisplay: f.boundaryDisplay };
    if (f.gisStatus === 'unmapped') {
      this.mapRequest.getParcels(filters).subscribe({
        next: (collection) => {
          this.setOverlay('parcels', null);
          this.featureSummary.set(`${collection.unmapped ?? 0} parcels have no coordinates, so they cannot be drawn.`);
        },
        error: (err) => this.showError(err, 'Parcels could not be loaded.'),
      });
      return;
    }
    this.drawQuery('parcels', 'Registered parcels', '#ea580c', f.labelField, (bbox) => this.mapRequest.getParcels({ ...filters, bbox }), 'Parcels could not be loaded.');
    if (layer) this.toggleLayer(layer, true);
  }

  showUtilities(): void {
    const f = this.utilityFilter;
    if (!f.tenantId || !f.layerId) {
      this.dialogs.showToast('Choose a ULB / city and a network layer first.', 'info', 2500);
      return;
    }
    if (!f.visible) {
      this.setOverlay('utilities', null);
      return;
    }
    const layer = this.layers().find((l) => l.id === f.layerId);
    if (layer?.dataSource === 'WMS') {
      this.showWms(layer);
      return;
    }
    const filters = { tenantId: f.tenantId, layerIds: [f.layerId], assetStatus: f.assetStatuses, utilityCategory: f.categories, networkType: f.networkType, department: f.department, dataSource: f.dataSource };
    // The colour chosen here is the Network Style, so it takes priority over the layer's own.
    const withStyle = (collection: GisFeatureCollection): GisFeatureCollection => ({
      ...collection,
      features: collection.features.map((feature) => ({ ...feature, properties: { ...feature.properties, _style: { ...(feature.properties?.['_style'] ?? {}), color: f.color } } })),
    });
    this.drawQuery('utilities', 'Utility network', f.color, undefined, (bbox) => this.mapRequest.getFeatures({ ...filters, bbox }).pipe(map(withStyle)), 'The network could not be loaded.');
  }

  showRoads(): void {
    const f = this.roadFilter;
    if (!f.tenantId || !f.roadLayerId || !f.zoneLayerId) {
      this.dialogs.showToast('Choose a ULB / city, a road layer and a zone boundary layer first.', 'info', 3000);
      return;
    }
    if (!f.visible) {
      this.setOverlay('roads', null);
      this.setOverlay('zones', null);
      return;
    }
    const roadFilters = { tenantId: f.tenantId, layerIds: [f.roadLayerId], dataSource: f.dataSource, roadCategory: f.categories, roadStatus: f.status, roadSurface: f.surfaces, zone: f.zones, ward: f.wards, minWidth: f.minWidth, maxWidth: f.maxWidth };
    this.drawQuery('roads', 'Roads', '#475569', undefined, (bbox) => this.mapRequest.getFeatures({ ...roadFilters, bbox }), 'Roads could not be loaded.');
    this.mapRequest.getFeatures({ tenantId: f.tenantId, layerIds: [f.zoneLayerId], dataSource: f.dataSource, zone: f.zones }).subscribe({
      next: (collection) => this.setOverlay('zones', {
        label: 'Zone boundaries',
        color: '#16a34a',
        collection: { ...collection, features: collection.features.map((feature) => ({ ...feature, properties: { ...feature.properties, _style: { color: '#16a34a', weight: 2, fillOpacity: 0.05 } } })) },
      }, collection.features.length),
      error: (err) => this.showError(err, 'Zone boundaries could not be loaded.'),
    });
  }

  // Geographic scope
  private scopeQuery(): Record<string, unknown> {
    const w = this.workspace;
    return {
      geographicScope: w.geographicScope,
      stateTenants: w.stateTenants,
      ulbTenants: w.ulbTenants,
      extent: this.parseNumbers(this.extentText, 4)?.join(','),
      layerIds: w.visibleLayers,
      includeParcels: this.includeParcels,
    };
  }

  /** The server decides what the scope covers, and refuses anything outside this user's access. */
  applyScope(): void {
    this.setOverlay('scope', null);
    this.drawQuery('scope', this.workspace.geographicScope, '#2563eb', undefined, (bbox) => this.mapRequest.getScopeFeatures({ ...this.scopeQuery(), bbox }), 'This scope could not be loaded.');
  }

  exportScope(): void {
    this.withLoading(this.gis.getScopeFeatures({ ...this.scopeQuery(), outputCrs: this.workspace.crs, limit: 5000 })).subscribe({
      next: (collection) => {
        const url = URL.createObjectURL(new Blob([JSON.stringify(collection)], { type: 'application/geo+json' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `gis-export-${this.workspace.crs.replace(':', '-')}.geojson`;
        link.click();
        URL.revokeObjectURL(url);
        this.dialogs.showToast(`${collection.features.length} features exported in ${this.workspace.crs}${collection.truncated ? ' (limit reached)' : ''}.`, collection.truncated ? 'warning' : 'success', 3500);
      },
      error: (err) => this.showError(err, 'This scope could not be exported.'),
    });
  }

  // Workspace
  useCurrentExtent(): void {
    const box = this.map?.viewBox();
    if (box) this.extentText = box.map((v) => v.toFixed(5)).join(', ');
  }

  useCurrentCentre(): void {
    const view = this.map?.centre();
    if (!view) return;
    this.centreText = `${view.lat.toFixed(5)}, ${view.lng.toFixed(5)}`;
    this.workspace.defaultZoom = view.zoom;
  }

  private parseNumbers(text: string, count: number): number[] | null {
    const values = text.split(',').map((v) => Number(v.trim()));
    return text.trim() && values.length === count && values.every((v) => Number.isFinite(v)) ? values : null;
  }

  saveWorkspace(): void {
    this.workspace.mapExtent = this.parseNumbers(this.extentText, 4);
    this.workspace.defaultCentre = this.parseNumbers(this.centreText, 2);
    this.gis.saveWorkspace(this.workspace).subscribe({
      next: (saved) => {
        this.dialogs.showToast('Map workspace saved.', 'success', 2500);
        this.workspace = { ...saved };
        this.selectedWorkspaceId = saved.id ?? '';
        this.loadWorkspaces();
      },
      error: (err) => this.showError(err, 'The workspace could not be saved.'),
    });
  }

  applyWorkspace(id: string): void {
    const saved = this.workspaces().find((w) => w.id === id);
    if (!saved) {
      // Choosing None starts a new workspace, so Save does not overwrite the previous one.
      this.workspace = { ...this.workspace, id: undefined };
      return;
    }
    this.workspace = { ...saved };
    this.extentText = saved.mapExtent?.join(', ') ?? '';
    this.centreText = saved.defaultCentre?.join(', ') ?? '';
    this.applyBaseMap();
    this.applyView();
    this.layers().filter((l) => l.id && saved.visibleLayers.includes(l.id)).forEach((l) => this.toggleLayer(l, true));
    this.onRefreshIntervalChange();
  }

  applyView(): void {
    const extent = this.parseNumbers(this.extentText, 4);
    const centre = this.parseNumbers(this.centreText, 2);
    if (extent) {
      // Extent is west, south, east, north, which is longitude first.
      this.map?.fitBox([extent[0], extent[1], extent[2], extent[3]]);
    } else if (centre) {
      this.map?.jumpTo(centre[0], centre[1], this.workspace.defaultZoom ?? 12);
    }
  }

  onRefreshIntervalChange(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    const ms = REFRESH_MS[this.workspace.refreshInterval];
    if (ms) {
      this.refreshTimer = setInterval(() => {
        // Refreshes keep the current view, so the map does not jump while someone is reading it.
        this.layers().filter((l) => this.isOnMap(l)).forEach((l) => this.toggleLayer(l, true, false));
      }, ms);
    }
  }

  async deleteWorkspace(): Promise<void> {
    const id = this.selectedWorkspaceId;
    const confirmed = await this.dialogs.confirm({ title: 'Delete workspace', message: `Delete '${this.workspace.workspaceName}'?`, confirmText: 'Delete', cancelText: 'Cancel', variant: 'destructive' });
    if (!confirmed || !id) return;
    this.gis.deleteWorkspace(id).subscribe({
      next: () => {
        this.dialogs.showToast('Map workspace deleted.', 'success', 2500);
        this.selectedWorkspaceId = '';
        this.workspace = { ...this.workspace, id: undefined };
        this.loadWorkspaces();
      },
      error: (err) => this.showError(err, 'The workspace could not be deleted.'),
    });
  }

  // Dialogs and tabs
  setTab(tab: GisTab): void {
    this.activeTab.set(tab);
  }

  onLayerSaved(): void {
    this.layerDialog.set(null);
    this.dialogs.showToast('GIS layer saved.', 'success', 2500);
    this.loadLayers();
    this.loadCityLayers();
  }

  onImported(result: GisImportResult): void {
    this.importLayer.set(null);
    this.dialogs.showToast(`${result.imported} features imported, ${result.rejected} rejected.`, result.rejected ? 'warning' : 'success', 3500);
    this.loadLayers();
    this.loadCityLayers();
  }

  async removeLayer(layer: GisLayer): Promise<void> {
    const confirmed = await this.dialogs.confirm({
      title: 'Delete layer',
      message: `Delete '${layer.layerName}' and its ${layer.featureCount ?? 0} stored features?`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      variant: 'destructive',
    });
    if (!confirmed || !layer.id) return;
    this.setOverlay(layer.id, null);
    this.gis.deleteLayer(layer.id).subscribe({
      next: () => {
        this.dialogs.showToast('GIS layer deleted.', 'success', 2500);
        this.loadLayers();
        this.loadCityLayers();
      },
      error: (err) => this.showError(err, 'The layer could not be deleted.'),
    });
  }

  onServiceSaved(): void {
    this.serviceDialog.set(null);
    this.dialogs.showToast('Service saved.', 'success', 2500);
    this.loadServices();
    this.loadCityLayers();
    this.loadLayers();
  }

  onBoundariesImported(result: GisImportResult): void {
    this.boundaryDialog.set(false);
    this.dialogs.showToast(`${result.imported} boundaries imported, ${result.rejected} rejected.`, result.rejected ? 'warning' : 'success', 3500);
    this.loadScope();
  }
}
