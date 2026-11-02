import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import maplibregl from 'maplibre-gl';
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
const INDIA_CENTRE: [number, number] = [80, 22.5];
const INDIA_ZOOM = 4;
const INDIA_3D_HEIGHT_M = 4500000;
const CESIUM_BASE_URL = 'cesium/';

/** One thing on the map, kept apart from the renderer so 2D and 3D draw the same data. */
interface MapOverlay {
  label: string;
  color: string;
  labelField?: string;
  collection?: GisFeatureCollection;
  wms?: { url: string; layers: string; opacity: number };
}
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
  @ViewChild('globeHost') globeHost?: ElementRef<HTMLDivElement>;
  private map?: maplibregl.Map;
  private mapReady = false;
  private popup?: maplibregl.Popup;
  private hoverLabel?: maplibregl.Popup;
  private overlays = new Map<string, MapOverlay>();
  private cesium?: typeof import('cesium');
  private globe?: import('cesium').Viewer;
  private globeBase?: import('cesium').ImageryLayer;
  private globeItems = new Map<string, import('cesium').GeoJsonDataSource | import('cesium').ImageryLayer>();
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
  readonly is3d = signal(false);
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
    this.map = new maplibregl.Map({
      container: this.mapHost.nativeElement,
      style: { version: 8, sources: {}, layers: [] },
      center: INDIA_CENTRE,
      zoom: INDIA_ZOOM,
    });
    this.map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');
    this.map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right');
    this.map.on('mousemove', (event) => {
      this.cursor.set(`${event.lngLat.lat.toFixed(5)}, ${event.lngLat.lng.toFixed(5)}`);
      this.showHoverLabel(event);
    });
    this.map.on('click', (event) => this.showPopup(event));
    this.map.on('load', () => {
      this.mapReady = true;
      this.applyBaseMap();
      this.overlays.forEach((overlay, key) => this.drawIn2d(key, overlay));
    });
    // Keeps tiles correct when the panel changes size, including full screen.
    this.resizeObserver = new ResizeObserver(() => this.map?.resize());
    this.resizeObserver.observe(this.mapHost.nativeElement);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    this.resizeObserver?.disconnect();
    this.map?.remove();
    this.globe?.destroy();
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
    if (!base) return;
    this.applyGlobeBase();
    if (!this.map || !this.mapReady) return;
    if (this.map.getLayer('base')) this.map.removeLayer('base');
    if (this.map.getSource('base')) this.map.removeSource('base');
    // MapLibre has no {s} placeholder, so subdomains become separate tile URLs.
    const tiles = base.url.includes('{s}') ? ['a', 'b', 'c'].map((sub) => base.url.replace('{s}', sub)) : [base.url];
    this.map.addSource('base', { type: 'raster', tiles, tileSize: 256, attribution: base.attribution, maxzoom: base.maxZoom });
    const firstLayer = this.map.getStyle().layers[0]?.id;
    this.map.addLayer({ id: 'base', type: 'raster', source: 'base' }, firstLayer);
  }

  private overlayLayerIds(key: string): string[] {
    return [`ov-${key}-fill`, `ov-${key}-line`, `ov-${key}-point`, `ov-${key}-raster`];
  }

  private setOverlay(key: string, overlay: MapOverlay | null, count: number | null = null): void {
    this.eraseFrom2d(key);
    this.eraseFromGlobe(key);
    this.overlays.delete(key);
    this.legend.update((items) => items.filter((item) => item.key !== key));
    if (overlay) {
      this.overlays.set(key, overlay);
      this.drawIn2d(key, overlay);
      void this.drawOnGlobe(key, overlay);
      this.legend.update((items) => [...items, { key, label: overlay.label, color: overlay.color, count }]);
    }
  }

  private eraseFrom2d(key: string): void {
    if (!this.map || !this.mapReady) return;
    this.overlayLayerIds(key).forEach((id) => {
      if (this.map!.getLayer(id)) this.map!.removeLayer(id);
    });
    if (this.map.getSource(`ov-${key}`)) this.map.removeSource(`ov-${key}`);
  }

  /** Style objects do not survive MapLibre's worker, so per-feature values are flattened first. */
  private flatten(collection: GisFeatureCollection, color: string): GeoJSON.FeatureCollection {
    return {
      type: 'FeatureCollection',
      features: collection.features.map((feature) => {
        const props = feature.properties ?? {};
        const style = (props['_style'] ?? {}) as { color?: string; weight?: number; fillOpacity?: number };
        return {
          ...feature,
          properties: { ...props, _color: style.color ?? color, _weight: style.weight ?? 2, _fillOpacity: style.fillOpacity ?? 0.2 },
        };
      }),
    };
  }

  private drawIn2d(key: string, overlay: MapOverlay): void {
    if (!this.map || !this.mapReady) return;
    const source = `ov-${key}`;
    if (overlay.wms) {
      const { url, layers, opacity } = overlay.wms;
      const separator = url.includes('?') ? '&' : '?';
      this.map.addSource(source, {
        type: 'raster',
        tileSize: 256,
        tiles: [`${url}${separator}service=WMS&version=1.1.1&request=GetMap&layers=${encodeURIComponent(layers)}&format=image/png&transparent=true&srs=EPSG:3857&width=256&height=256&bbox={bbox-epsg-3857}`],
      });
      this.map.addLayer({ id: `${source}-raster`, type: 'raster', source, paint: { 'raster-opacity': opacity } });
      return;
    }
    if (!overlay.collection) return;
    this.map.addSource(source, { type: 'geojson', data: this.flatten(overlay.collection, overlay.color) });
    this.map.addLayer({
      id: `${source}-fill`, type: 'fill', source, filter: ['==', ['geometry-type'], 'Polygon'],
      paint: { 'fill-color': ['get', '_color'], 'fill-opacity': ['get', '_fillOpacity'] },
    });
    this.map.addLayer({
      id: `${source}-line`, type: 'line', source, filter: ['!=', ['geometry-type'], 'Point'],
      paint: { 'line-color': ['get', '_color'], 'line-width': ['get', '_weight'] },
    });
    this.map.addLayer({
      id: `${source}-point`, type: 'circle', source, filter: ['==', ['geometry-type'], 'Point'],
      paint: { 'circle-color': ['get', '_color'], 'circle-radius': 6, 'circle-opacity': 0.7, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1 },
    });
  }

  private featuresAt(point: maplibregl.Point): maplibregl.MapGeoJSONFeature[] {
    if (!this.map) return [];
    const layers = [...this.overlays.keys()].flatMap((key) => this.overlayLayerIds(key)).filter((id) => this.map!.getLayer(id) && !id.endsWith('-raster'));
    return layers.length ? this.map.queryRenderedFeatures(point, { layers }) : [];
  }

  private overlayOf(feature: maplibregl.MapGeoJSONFeature): MapOverlay | undefined {
    return this.overlays.get(String(feature.source).replace(/^ov-/, ''));
  }

  private showPopup(event: maplibregl.MapMouseEvent): void {
    const feature = this.featuresAt(event.point)[0];
    if (!feature || !this.map) return;
    const props = feature.properties ?? {};
    const box = document.createElement('div');
    const title = document.createElement('div');
    title.className = 'gis-popup-title';
    title.textContent = String(props['_layer'] ?? this.overlayOf(feature)?.label ?? '');
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
    this.popup?.remove();
    this.popup = new maplibregl.Popup({ maxWidth: '320px' }).setLngLat(event.lngLat).setDOMContent(box).addTo(this.map);
  }

  private showHoverLabel(event: maplibregl.MapMouseEvent): void {
    if (!this.map) return;
    const feature = this.featuresAt(event.point)[0];
    this.map.getCanvas().style.cursor = feature ? 'pointer' : '';
    const field = feature && this.overlayOf(feature)?.labelField;
    const text = field ? feature.properties?.[field] : null;
    if (!text) {
      this.hoverLabel?.remove();
      return;
    }
    this.hoverLabel ??= new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    this.hoverLabel.setLngLat(event.lngLat).setText(String(text)).addTo(this.map);
  }

  /** The globe is loaded only when asked for, because CesiumJS is several megabytes. */
  async toggle3d(): Promise<void> {
    if (this.is3d()) {
      this.is3d.set(false);
      setTimeout(() => this.map?.resize(), 0);
      return;
    }
    this.is3d.set(true);
    if (this.globe) {
      setTimeout(() => this.globe?.resize(), 0);
      return;
    }
    this.isLoadingMap.set(true);
    try {
      (window as unknown as { CESIUM_BASE_URL: string }).CESIUM_BASE_URL = CESIUM_BASE_URL;
      this.cesium = await import('cesium');
      if (!document.getElementById('cesium-widgets')) {
        const link = document.createElement('link');
        link.id = 'cesium-widgets';
        link.rel = 'stylesheet';
        link.href = `${CESIUM_BASE_URL}Widgets/widgets.css`;
        document.head.appendChild(link);
      }
      // baseLayer false keeps Cesium off its Ion service: the base map comes from the same list as 2D.
      this.globe = new this.cesium.Viewer(this.globeHost!.nativeElement, {
        baseLayer: false,
        animation: false,
        timeline: false,
        geocoder: false,
        baseLayerPicker: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        fullscreenButton: false,
      });
      this.applyGlobeBase();
      const centre = this.map?.getCenter();
      this.globe.camera.setView({ destination: this.cesium.Cartesian3.fromDegrees(centre?.lng ?? INDIA_CENTRE[0], centre?.lat ?? INDIA_CENTRE[1], INDIA_3D_HEIGHT_M) });
      await Promise.all([...this.overlays].map(([key, overlay]) => this.drawOnGlobe(key, overlay)));
    } catch {
      this.is3d.set(false);
      this.dialogs.showToast('The 3D view could not be started on this device.', 'error', 3500);
    } finally {
      this.isLoadingMap.set(this.pendingRequests > 0);
    }
  }

  private applyGlobeBase(): void {
    const base = this.options().baseMaps.find((b) => b.code === this.workspace.baseMap);
    if (!this.globe || !this.cesium || !base) return;
    if (this.globeBase) this.globe.imageryLayers.remove(this.globeBase);
    const provider = new this.cesium.UrlTemplateImageryProvider({
      url: base.url,
      subdomains: ['a', 'b', 'c'],
      maximumLevel: base.maxZoom,
      credit: new this.cesium.Credit(base.attribution),
    });
    this.globeBase = this.globe.imageryLayers.addImageryProvider(provider, 0);
  }

  private eraseFromGlobe(key: string): void {
    const item = this.globeItems.get(key);
    if (!item || !this.globe || !this.cesium) return;
    if (item instanceof this.cesium.ImageryLayer) this.globe.imageryLayers.remove(item);
    else this.globe.dataSources.remove(item, true);
    this.globeItems.delete(key);
  }

  private async drawOnGlobe(key: string, overlay: MapOverlay): Promise<void> {
    const cesium = this.cesium;
    if (!this.globe || !cesium) return;
    if (overlay.wms) {
      const layer = this.globe.imageryLayers.addImageryProvider(
        new cesium.WebMapServiceImageryProvider({
          url: overlay.wms.url,
          layers: overlay.wms.layers,
          parameters: { transparent: true, format: 'image/png' },
        }),
      );
      layer.alpha = overlay.wms.opacity;
      this.globeItems.set(key, layer);
      return;
    }
    if (!overlay.collection) return;
    const color = cesium.Color.fromCssColorString(overlay.color);
    const source = await cesium.GeoJsonDataSource.load(overlay.collection, {
      stroke: color,
      fill: color.withAlpha(0.2),
      markerColor: color,
      clampToGround: true,
    });
    if (this.overlays.get(key) !== overlay) return;
    this.eraseFromGlobe(key);
    await this.globe.dataSources.add(source);
    this.globeItems.set(key, source);
    if (this.is3d()) void this.globe.flyTo(source);
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
    this.map?.jumpTo({ center: INDIA_CENTRE, zoom: INDIA_ZOOM, pitch: 0, bearing: 0 });
    if (this.globe && this.cesium) {
      void this.globe.camera.flyTo({ destination: this.cesium.Cartesian3.fromDegrees(INDIA_CENTRE[0], INDIA_CENTRE[1], INDIA_3D_HEIGHT_M) });
    }
  }

  private boundsOf(collections: (GisFeatureCollection | undefined)[]): maplibregl.LngLatBounds | null {
    const bounds = new maplibregl.LngLatBounds();
    const visit = (coords: unknown): void => {
      if (!Array.isArray(coords)) return;
      if (typeof coords[0] === 'number') bounds.extend([coords[0], coords[1] as number]);
      else coords.forEach(visit);
    };
    const visitGeometry = (geometry: GeoJSON.Geometry | null): void => {
      if (!geometry) return;
      if (geometry.type === 'GeometryCollection') geometry.geometries.forEach(visitGeometry);
      else visit(geometry.coordinates);
    };
    collections.forEach((collection) => collection?.features.forEach((feature) => visitGeometry(feature.geometry)));
    return bounds.isEmpty() ? null : bounds;
  }

  fitToData(): void {
    const bounds = this.boundsOf([...this.overlays.values()].map((overlay) => overlay.collection));
    if (bounds) {
      this.map?.fitBounds(bounds, { maxZoom: 15, padding: 32 });
      if (this.globe && this.cesium && this.is3d()) {
        void this.globe.camera.flyTo({ destination: this.cesium.Rectangle.fromDegrees(bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()) });
      }
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
    this.setOverlay(key, { label, color, labelField, collection }, collection.features.length);
    const bounds = this.boundsOf([collection]);
    if (bounds) this.map?.fitBounds(bounds, { maxZoom: 15, padding: 24 });
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
      this.setOverlay(layer.id, {
        label: layer.layerName,
        color: layer.layerStyle?.color ?? '#2563eb',
        wms: { url: layer.serviceUrl!, layers: layer.layerIdentifier!, opacity: layer.opacity ?? 1 },
      });
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
    const merged: GisFeatureCollection = { type: 'FeatureCollection', features: [] };
    this.setOverlay('boundaries', null);
    tenants.forEach((tenantId) =>
      this.mapRequest.getBoundaries(tenantId).subscribe({
        next: (collection) => {
          merged.features.push(...collection.features);
          const styled = merged.features.map((f) => ({ ...f, properties: { ...f.properties, _style: { color: '#7c3aed', weight: 2, fillOpacity: 0.05 } } }));
          this.setOverlay('boundaries', { label: 'Ward boundaries', color: '#7c3aed', collection: { type: 'FeatureCollection', features: styled } }, merged.features.length);
          this.featureSummary.set(merged.features.length ? `${merged.features.length} ward boundaries shown.` : 'No ward boundaries are recorded for this selection yet.');
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
      next: (collection) => this.setOverlay('zones', {
        label: 'Zone boundaries',
        color: '#16a34a',
        collection: { ...collection, features: collection.features.map((f) => ({ ...f, properties: { ...f.properties, _style: { color: '#16a34a', weight: 2, fillOpacity: 0.05 } } })) },
      }, collection.features.length),
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
      this.map?.jumpTo({ center: [centre[1], centre[0]], zoom: this.workspace.defaultZoom ?? 12 });
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
    setTimeout(() => this.map?.resize(), 0);
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
