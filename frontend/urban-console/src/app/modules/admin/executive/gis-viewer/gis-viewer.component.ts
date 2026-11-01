import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import * as L from 'leaflet';
import { Observable, defer, finalize } from 'rxjs';
import { DataNoticeComponent } from '../../../../shared/components/data-notice/data-notice.component';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { RowSearchPipe } from '../../../../shared/components/table-pager/row-search.pipe';
import { PagerState, TablePagerComponent } from '../../../../shared/components/table-pager/table-pager.component';
import { TableSearchComponent } from '../../../../shared/components/table-pager/table-search.component';
import { DialogService } from '../../../../core/services/dialog.service';
import { GisService } from '../../../../core/services/gis.service';
import {
  GisFeatureCollection,
  GisImportResult,
  GisLayer,
  GisOptions,
  GisScopeRow,
  GisWorkspace,
} from '../../../../core/models/gis.model';
import { GisImportDialogComponent } from './dialogs/gis-import-dialog.component';
import { GisLayerDialogComponent } from './dialogs/gis-layer-dialog.component';
import { GisMultiSelectComponent } from './gis-multi-select.component';

type GisTab = 'overview' | 'state' | 'city' | 'parcels' | 'utilities' | 'roads';

const EMPTY_OPTIONS: GisOptions = {
  states: [], ulbs: [], districts: [], wards: [], zones: [], baseMaps: [], crsOptions: [], geographicScopes: [],
  refreshIntervals: [], layerCategories: [], layerTypes: [], dataSources: [], layerStatuses: [], boundaryLevels: [],
  utilityCategories: [], utilityNetworkTypes: [], assetStatuses: [], roadCategories: [], roadStatuses: [],
  roadSurfaces: [], parcelCategories: [], parcelStatuses: [],
};
const INDIA_CENTRE: L.LatLngTuple = [22.5, 80];
const INDIA_ZOOM = 5;
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
    TablePagerComponent,
    TableSearchComponent,
    RowSearchPipe,
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
  private resizeObserver?: ResizeObserver;
  private map?: L.Map;
  private baseLayer?: L.TileLayer;
  private overlays = new Map<string, L.Layer>();
  private refreshTimer?: ReturnType<typeof setInterval>;

  readonly pagers = new PagerState();
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
  readonly cursor = signal('Move over the map');
  private pendingRequests = 0;
  readonly featureSummary = signal('');
  readonly layerDialog = signal<{ layer: GisLayer | null; category: string } | null>(null);
  readonly importLayer = signal<GisLayer | null>(null);

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
  parcelFilter = { state: '', tenantId: '', wards: [] as string[], categories: [] as string[], statuses: [] as string[], surveyStatus: '', gisStatus: 'mapped', dataSource: 'PostGIS', layerId: '', boundaryDisplay: true, labelField: 'ulpin', search: '' };
  utilityFilter = { state: '', tenantId: '', categories: [] as string[], networkType: '', layerId: '', assetStatuses: [] as string[], department: '', dataSource: 'PostGIS', visible: true, color: '#0891b2' };
  roadFilter = { state: '', tenantId: '', zones: [] as string[], wards: [] as string[], categories: [] as string[], status: '', roadLayerId: '', zoneLayerId: '', dataSource: 'PostGIS', minWidth: null as number | null, maxWidth: null as number | null, surfaces: [] as string[], visible: true };
  cityFilter = { state: '', tenantId: '' };

  ngOnInit(): void {
    this.loadOptions();
    this.loadLayers();
    this.loadWorkspaces();
    this.loadScope();
  }

  ngAfterViewInit(): void {
    if (!this.mapHost) return;
    this.map = L.map(this.mapHost.nativeElement, { zoomControl: false }).setView(INDIA_CENTRE, INDIA_ZOOM);
    L.control.zoom({ position: 'bottomright' }).addTo(this.map);
    L.control.scale({ position: 'bottomright', imperial: false }).addTo(this.map);
    this.map.on('mousemove', (event: L.LeafletMouseEvent) =>
      this.cursor.set(`${event.latlng.lat.toFixed(5)}, ${event.latlng.lng.toFixed(5)}`),
    );
    this.applyBaseMap();
    // Keeps tiles correct when the panel changes size, including full screen.
    this.resizeObserver = new ResizeObserver(() => this.map?.invalidateSize());
    this.resizeObserver.observe(this.mapHost.nativeElement);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    this.resizeObserver?.disconnect();
    this.map?.remove();
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

  loadLayers(): void {
    this.gis.getLayers({ tenantId: this.cityFilter.tenantId }).subscribe({
      next: (layers) => this.layers.set(layers),
      error: () => this.notice.set('GIS layers could not be loaded.'),
    });
  }

  loadScope(): void {
    this.gis
      .getScope({
        stateTenants: this.stateFilter.stateTenants,
        districts: this.stateFilter.districts,
        ulbTenants: this.stateFilter.ulbTenants,
        boundaryStatus: this.stateFilter.boundaryStatus,
      })
      .subscribe({
        next: (rows) => this.scope.set(rows),
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
    if (!this.map || !base) return;
    this.baseLayer?.remove();
    this.baseLayer = L.tileLayer(base.url, { attribution: base.attribution, maxZoom: base.maxZoom }).addTo(this.map);
  }

  private setOverlay(key: string, layer: L.Layer | null, label = key, color = '#2563eb', count: number | null = null): void {
    const previous = this.overlays.get(key);
    if (previous) this.map?.removeLayer(previous);
    this.overlays.delete(key);
    this.legend.update((items) => items.filter((item) => item.key !== key));
    if (layer && this.map) {
      layer.addTo(this.map);
      this.overlays.set(key, layer);
      this.legend.update((items) => [...items, { key, label, color, count }]);
    }
  }

  removeOverlay(key: string): void {
    this.setOverlay(key, null);
  }

  /** Same calls as GisService, with the map's loading bar shown while they run. */
  private readonly mapRequest = {
    getFeatures: (filters: Record<string, unknown>) => this.withLoading(this.gis.getFeatures(filters)),
    getParcels: (filters: Record<string, unknown>) => this.withLoading(this.gis.getParcels(filters)),
    getBoundaries: (tenantId: string) => this.withLoading(this.gis.getBoundaries(tenantId)),
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
    this.map?.setView(INDIA_CENTRE, INDIA_ZOOM);
  }

  fitToData(): void {
    const group = L.featureGroup([...this.overlays.values()].filter((layer) => layer instanceof L.FeatureGroup));
    const bounds = group.getBounds();
    if (bounds.isValid()) {
      this.map?.fitBounds(bounds, { maxZoom: 16, padding: [32, 32] });
    } else {
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

  private drawCollection(key: string, label: string, collection: GisFeatureCollection, color: string, labelField?: string): void {
    const geo = L.geoJSON(collection, {
      style: (feature) => {
        const style = (feature?.properties?._style ?? {}) as { color?: string; weight?: number; fillOpacity?: number };
        return { color: style.color ?? color, weight: style.weight ?? 2, fillOpacity: style.fillOpacity ?? 0.2 };
      },
      pointToLayer: (_feature, latlng) => L.circleMarker(latlng, { radius: 6, color, fillOpacity: 0.7 }),
      onEachFeature: (feature, layer) => {
        const props = feature.properties ?? {};
        const box = document.createElement('div');
        const title = document.createElement('div');
        title.className = 'gis-popup-title';
        title.textContent = String(props['_layer'] ?? label);
        box.appendChild(title);
        Object.entries(props)
          .filter(([name]) => !name.startsWith('_'))
          .forEach(([name, value]) => {
            const row = document.createElement('div');
            row.className = 'gis-popup-row';
            const key = document.createElement('span');
            key.textContent = name.replace(/([a-z])([A-Z])/g, '$1 $2');
            const val = document.createElement('span');
            val.textContent = String(value ?? '');
            row.append(key, val);
            box.appendChild(row);
          });
        layer.bindPopup(box);
        if (labelField && props[labelField]) layer.bindTooltip(String(props[labelField]));
      },
    });
    this.setOverlay(key, geo, label, color, collection.features.length);
    const bounds = geo.getBounds();
    if (bounds.isValid()) this.map?.fitBounds(bounds, { maxZoom: 16, padding: [24, 24] });
    const count = collection.features.length;
    this.featureSummary.set(`${count} feature${count === 1 ? '' : 's'} shown${collection.truncated ? ' (limit reached, zoom in or filter further)' : ''}.`);
  }

  private showError(err: { error?: { detail?: unknown } }, fallback: string): void {
    const detail = err?.error?.detail;
    this.dialogs.showToast(typeof detail === 'string' ? detail : fallback, 'error', 3500);
  }

  private showRemoteLayer(layer: GisLayer): void {
    if (!this.map || !layer.id) return;
    if (layer.dataSource === 'WMS') {
      this.setOverlay(
        layer.id,
        L.tileLayer.wms(layer.serviceUrl!, { layers: layer.layerIdentifier!, format: 'image/png', transparent: true, opacity: layer.opacity }),
        layer.layerName,
        layer.layerStyle?.color ?? '#2563eb',
      );
    } else if (layer.dataSource === 'WFS') {
      // Native fetch: session cookies and tenant headers must never reach a third-party service.
      const url = new URL(layer.serviceUrl!);
      Object.entries({ service: 'WFS', version: '2.0.0', request: 'GetFeature', typeNames: layer.layerIdentifier!, outputFormat: 'application/json', srsName: 'EPSG:4326', count: '5000' })
        .forEach(([k, v]) => url.searchParams.set(k, v));
      fetch(url.toString(), { credentials: 'omit' })
        .then((res) => {
          if (!res.ok) throw new Error(String(res.status));
          return res.json();
        })
        .then((collection: GisFeatureCollection) => this.drawCollection(layer.id!, layer.layerName, collection, layer.layerStyle?.color ?? '#2563eb'))
        .catch(() => this.dialogs.showToast(`WFS service for ${layer.layerName} could not be read.`, 'error', 3500));
    }
  }

  toggleLayer(layer: GisLayer, visible: boolean): void {
    if (!layer.id) return;
    if (!visible) {
      this.setOverlay(layer.id, null);
      return;
    }
    if (['WMS', 'WFS'].includes(layer.dataSource)) {
      this.showRemoteLayer(layer);
      return;
    }
    this.mapRequest.getFeatures({ tenantId: layer.tenantId, layerIds: [layer.id] }).subscribe({
      next: (collection) => this.drawCollection(layer.id!, layer.layerName, collection, layer.layerStyle?.color ?? '#2563eb'),
      error: (err) => this.showError(err, 'This layer could not be loaded.'),
    });
  }

  isOnMap(layer: GisLayer): boolean {
    return !!layer.id && this.overlays.has(layer.id);
  }

  showState(): void {
    this.loadScope();
    if (!this.stateFilter.visible) {
      this.setOverlay('boundaries', null);
      return;
    }
    const tenants = this.stateFilter.ulbTenants.length ? this.stateFilter.ulbTenants : this.scope().map((r) => r.tenantId);
    const group = L.featureGroup();
    let found = 0;
    this.setOverlay('boundaries', group, 'Ward boundaries', '#7c3aed');
    tenants.forEach((tenantId) =>
      this.mapRequest.getBoundaries(tenantId).subscribe({
        next: (collection) => {
          found += collection.features.length;
          L.geoJSON(collection, { style: { color: '#7c3aed', weight: 2, fillOpacity: 0.05 } }).addTo(group);
          this.featureSummary.set(found ? `${found} ward boundaries shown.` : 'No ward boundaries are recorded for this selection yet.');
        },
        error: (err) => this.showError(err, 'Boundaries could not be loaded.'),
      }),
    );
  }

  showParcels(): void {
    const f = this.parcelFilter;
    if (!f.tenantId) {
      this.dialogs.showToast('Choose a ULB / city first.', 'info', 2500);
      return;
    }
    this.mapRequest.getParcels({ tenantId: f.tenantId, wards: f.wards, categories: f.categories, statuses: f.statuses, gisStatus: f.gisStatus, search: f.search })
      .subscribe({
        next: (collection) => {
          if (collection.unmapped !== undefined) {
            this.setOverlay('parcels', null);
            this.featureSummary.set(`${collection.unmapped} parcels have no coordinates, so they cannot be drawn.`);
            return;
          }
          this.drawCollection('parcels', 'Registered parcels', collection, '#ea580c', f.boundaryDisplay ? f.labelField : undefined);
          if (f.layerId) {
            const layer = this.layers().find((l) => l.id === f.layerId);
            if (layer) this.toggleLayer(layer, true);
          }
        },
        error: (err) => this.showError(err, 'Parcels could not be loaded.'),
      });
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
    if (layer && ['WMS', 'WFS'].includes(layer.dataSource)) {
      this.showRemoteLayer(layer);
      return;
    }
    this.mapRequest.getFeatures({ tenantId: f.tenantId, layerIds: [f.layerId], assetStatus: f.assetStatuses }).subscribe({
      next: (collection) => this.drawCollection('utilities', 'Utility network', collection, f.color),
      error: (err) => this.showError(err, 'The network could not be loaded.'),
    });
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
    this.mapRequest.getFeatures({ tenantId: f.tenantId, layerIds: [f.roadLayerId], roadCategory: f.categories, roadStatus: f.status, roadSurface: f.surfaces, zone: f.zones, ward: f.wards, minWidth: f.minWidth, maxWidth: f.maxWidth })
      .subscribe({
        next: (collection) => this.drawCollection('roads', 'Roads', collection, '#475569'),
        error: (err) => this.showError(err, 'Roads could not be loaded.'),
      });
    this.mapRequest.getFeatures({ tenantId: f.tenantId, layerIds: [f.zoneLayerId], zone: f.zones }).subscribe({
      next: (collection) => this.setOverlay('zones', L.geoJSON(collection, { style: { color: '#16a34a', weight: 2, fillOpacity: 0.05 } }), 'Zone boundaries', '#16a34a', collection.features.length),
      error: (err) => this.showError(err, 'Zone boundaries could not be loaded.'),
    });
  }

  // Workspace
  useCurrentExtent(): void {
    const b = this.map?.getBounds();
    if (b) this.extentText = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].map((v) => v.toFixed(5)).join(', ');
  }

  useCurrentCentre(): void {
    const c = this.map?.getCenter();
    if (c) this.centreText = `${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}`;
    if (this.map) this.workspace.defaultZoom = this.map.getZoom();
  }

  private parseNumbers(text: string, count: number): number[] | null {
    const values = text.split(',').map((v) => Number(v.trim()));
    return text.trim() && values.length === count && values.every((v) => Number.isFinite(v)) ? values : null;
  }

  saveWorkspace(): void {
    this.workspace.mapExtent = this.parseNumbers(this.extentText, 4);
    this.workspace.defaultCentre = this.parseNumbers(this.centreText, 2);
    this.gis.saveWorkspace(this.workspace).subscribe({
      next: () => {
        this.dialogs.showToast('Map workspace saved.', 'success', 2500);
        this.loadWorkspaces();
      },
      error: (err) => this.showError(err, 'The workspace could not be saved.'),
    });
  }

  applyWorkspace(id: string): void {
    const saved = this.workspaces().find((w) => w.id === id);
    if (!saved) return;
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
      this.map?.fitBounds([[extent[1], extent[0]], [extent[3], extent[2]]]);
    } else if (centre) {
      this.map?.setView([centre[0], centre[1]], this.workspace.defaultZoom ?? 12);
    }
  }

  onRefreshIntervalChange(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    const ms = REFRESH_MS[this.workspace.refreshInterval];
    if (ms) {
      this.refreshTimer = setInterval(() => {
        this.layers().filter((l) => this.isOnMap(l)).forEach((l) => this.toggleLayer(l, true));
      }, ms);
    }
  }

  // Dialogs and tabs
  setTab(tab: GisTab): void {
    this.activeTab.set(tab);
    setTimeout(() => this.map?.invalidateSize(), 0);
  }

  onLayerSaved(): void {
    this.layerDialog.set(null);
    this.dialogs.showToast('GIS layer saved.', 'success', 2500);
    this.loadLayers();
  }

  onImported(result: GisImportResult): void {
    this.importLayer.set(null);
    this.dialogs.showToast(`${result.imported} features imported, ${result.rejected} rejected.`, result.rejected ? 'warning' : 'success', 3500);
    this.loadLayers();
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
      },
      error: (err) => this.showError(err, 'The layer could not be deleted.'),
    });
  }
}
