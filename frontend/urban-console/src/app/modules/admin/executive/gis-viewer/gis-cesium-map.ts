import type * as CesiumTypes from 'cesium';
import { GisBaseMap, GisFeatureCollection } from '../../../../core/models/gis.model';

/** One thing on the map. */
export interface MapOverlay {
  label: string;
  color: string;
  labelField?: string;
  collection?: GisFeatureCollection;
  wms?: { url: string; layers: string; opacity: number };
}

export interface MapCallbacks {
  onPointerMove(lat: number, lng: number): void;
  /** Returns true when the click was used, such as to pick a point, so no popup opens. */
  onClick(lat: number, lng: number): boolean;
  onViewChanged(bbox: string): void;
  onError(message: string): void;
}

export type LngLatBox = [west: number, south: number, east: number, north: number];

const CESIUM_BASE_URL = 'cesium/';
const HOME_LNG = 80;
const HOME_LAT = 22.5;
const HOME_ZOOM = 4;
const WORLD_METRES = 3.6e7;
const POINT_PIXELS = 10;
const HOVER_INTERVAL_MS = 80;
const SMALLEST_BOX_DEGREES = 0.005;
const FLY_SECONDS = 0.6;
const MORPH_SECONDS = 0.6;
const LOADING_COLOUR = '#e8eef3';

/** Approximate, because Cesium measures camera distance rather than tile levels. */
export function metresForZoom(zoom: number): number {
  return WORLD_METRES / 2 ** zoom;
}

export function zoomForMetres(metres: number): number {
  return Math.min(20, Math.max(1, Math.round(Math.log2(WORLD_METRES / metres))));
}

export function boundsOf(collections: (GisFeatureCollection | undefined)[]): LngLatBox | null {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  const visit = (coords: unknown): void => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === 'number') {
      west = Math.min(west, coords[0]);
      east = Math.max(east, coords[0]);
      south = Math.min(south, coords[1] as number);
      north = Math.max(north, coords[1] as number);
    } else {
      coords.forEach(visit);
    }
  };
  const visitGeometry = (geometry: GeoJSON.Geometry | null): void => {
    if (!geometry) return;
    if (geometry.type === 'GeometryCollection') geometry.geometries.forEach(visitGeometry);
    else visit(geometry.coordinates);
  };
  collections.forEach((collection) => collection?.features.forEach((feature) => visitGeometry(feature.geometry)));
  return west === Infinity ? null : [west, south, east, north];
}

/** The one map engine for 2D and 3D. Loaded on demand, because CesiumJS is several megabytes. */
export class GisCesiumMap {
  private cesium?: typeof CesiumTypes;
  private viewer?: CesiumTypes.Viewer;
  private baseLayer?: CesiumTypes.ImageryLayer;
  private baseMap?: GisBaseMap;
  private handler?: CesiumTypes.ScreenSpaceEventHandler;
  private overlays = new Map<string, MapOverlay>();
  private drawn = new Map<string, CesiumTypes.GeoJsonDataSource | CesiumTypes.ImageryLayer>();
  private overlayByEntity = new WeakMap<object, MapOverlay>();
  private popup?: HTMLElement;
  private tooltip?: HTMLElement;
  private lastHover = 0;
  private is3d = false;
  private hasFittedData = false;

  constructor(private host: HTMLElement, private callbacks: MapCallbacks) {}

  async start(): Promise<void> {
    (window as unknown as { CESIUM_BASE_URL: string }).CESIUM_BASE_URL = CESIUM_BASE_URL;
    const cesium = await import('cesium');
    this.cesium = cesium;
    if (!document.getElementById('cesium-widgets')) {
      const link = document.createElement('link');
      link.id = 'cesium-widgets';
      link.rel = 'stylesheet';
      link.href = `${CESIUM_BASE_URL}Widgets/widgets.css`;
      document.head.appendChild(link);
    }
    // baseLayer false keeps Cesium off its Ion service. Web Mercator keeps 2D maps looking as people expect.
    const viewer = new cesium.Viewer(this.host, {
      sceneMode: cesium.SceneMode.SCENE2D,
      mapProjection: new cesium.WebMercatorProjection(),
      baseLayer: false,
      animation: false,
      timeline: false,
      geocoder: false,
      baseLayerPicker: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      showRenderLoopErrors: false,
    });
    this.viewer = viewer;
    // Tiles take a moment to arrive, and a black map looks broken while they do.
    const loading = cesium.Color.fromCssColorString(LOADING_COLOUR);
    viewer.scene.backgroundColor = loading;
    viewer.scene.globe.baseColor = loading;
    viewer.scene.renderError.addEventListener(() => this.callbacks.onError('The map stopped drawing on this device.'));
    viewer.camera.moveEnd.addEventListener(() => this.reportView());
    viewer.camera.moveStart.addEventListener(() => this.closePopup());
    this.bindPointer(cesium, viewer);
    // The canvas only has its real size after the first frame, and a view set earlier would show nothing.
    const firstFrame = viewer.scene.postRender.addEventListener(() => {
      firstFrame();
      if (!this.hasFittedData) this.goHome();
    });
    if (this.baseMap) this.setBaseMap(this.baseMap);
    await Promise.all([...this.overlays].map(([key, overlay]) => this.draw(key, overlay)));
  }

  destroy(): void {
    this.handler?.destroy();
    this.viewer?.destroy();
    this.viewer = undefined;
  }

  setBaseMap(base: GisBaseMap): void {
    this.baseMap = base;
    if (!this.viewer || !this.cesium) return;
    if (this.baseLayer) this.viewer.imageryLayers.remove(this.baseLayer);
    this.baseLayer = this.viewer.imageryLayers.addImageryProvider(
      new this.cesium.UrlTemplateImageryProvider({
        url: base.url,
        subdomains: ['a', 'b', 'c'],
        maximumLevel: base.maxZoom,
        credit: new this.cesium.Credit(base.attribution),
      }),
      0,
    );
  }

  hasOverlay(key: string): boolean {
    return this.overlays.has(key);
  }

  setOverlay(key: string, overlay: MapOverlay | null): void {
    this.erase(key);
    this.closePopup();
    if (overlay) {
      this.overlays.set(key, overlay);
      void this.draw(key, overlay);
    } else {
      this.overlays.delete(key);
    }
  }

  private erase(key: string): void {
    const item = this.drawn.get(key);
    if (!item || !this.viewer || !this.cesium) return;
    if (item instanceof this.cesium.ImageryLayer) this.viewer.imageryLayers.remove(item);
    else this.viewer.dataSources.remove(item, true);
    this.drawn.delete(key);
  }

  private async draw(key: string, overlay: MapOverlay): Promise<void> {
    const cesium = this.cesium;
    const viewer = this.viewer;
    if (!viewer || !cesium) return;
    if (overlay.wms) {
      const layer = viewer.imageryLayers.addImageryProvider(
        new cesium.WebMapServiceImageryProvider({
          url: overlay.wms.url,
          layers: overlay.wms.layers,
          parameters: { transparent: true, format: 'image/png' },
          enablePickFeatures: false,
        }),
      );
      layer.alpha = overlay.wms.opacity;
      this.drawn.set(key, layer);
        return;
    }
    if (!overlay.collection) return;
    const source = await cesium.GeoJsonDataSource.load(overlay.collection, { clampToGround: false });
    // A newer version of this overlay may have arrived while this one loaded.
    if (this.overlays.get(key) !== overlay || !this.viewer) return;
    this.styleEntities(cesium, source, overlay);
    this.erase(key);
    await viewer.dataSources.add(source);
    this.drawn.set(key, source);
  }

  /** Each feature can carry its own style, so colours are set entity by entity. */
  private styleEntities(cesium: typeof CesiumTypes, source: CesiumTypes.GeoJsonDataSource, overlay: MapOverlay): void {
    const now = cesium.JulianDate.now();
    for (const entity of source.entities.values) {
      this.overlayByEntity.set(entity, overlay);
      const style = (entity.properties?.getValue(now)?.['_style'] ?? {}) as { color?: string; weight?: number; fillOpacity?: number };
      const color = cesium.Color.fromCssColorString(style.color ?? overlay.color);
      const material = new cesium.ColorMaterialProperty(color);
      if (entity.polygon) {
        entity.polygon.material = new cesium.ColorMaterialProperty(color.withAlpha(style.fillOpacity ?? 0.2));
        entity.polygon.outline = new cesium.ConstantProperty(true);
        entity.polygon.outlineColor = new cesium.ConstantProperty(color);
        entity.polygon.height = new cesium.ConstantProperty(0);
      }
      if (entity.polyline) {
        entity.polyline.material = material;
        entity.polyline.width = new cesium.ConstantProperty(style.weight ?? 2);
      }
      if (entity.billboard) {
        // GeoJSON points default to pin images, which would each need drawing and do not suit dense parcels.
        entity.billboard = undefined;
        entity.point = new cesium.PointGraphics({
          pixelSize: POINT_PIXELS,
          color: color.withAlpha(0.8),
          outlineColor: cesium.Color.WHITE,
          outlineWidth: 1,
        });
      }
    }
  }

  private bindPointer(cesium: typeof CesiumTypes, viewer: CesiumTypes.Viewer): void {
    this.handler = new cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    this.handler.setInputAction((movement: CesiumTypes.ScreenSpaceEventHandler.MotionEvent) => {
      const now = performance.now();
      if (now - this.lastHover < HOVER_INTERVAL_MS) return;
      this.lastHover = now;
      const point = this.lngLatAt(movement.endPosition);
      if (point) this.callbacks.onPointerMove(point[1], point[0]);
      this.showHover(movement.endPosition);
    }, cesium.ScreenSpaceEventType.MOUSE_MOVE);
    this.handler.setInputAction((click: CesiumTypes.ScreenSpaceEventHandler.PositionedEvent) => {
      const point = this.lngLatAt(click.position);
      if (!point) return;
      this.closePopup();
      if (this.callbacks.onClick(point[1], point[0])) return;
      this.showPopup(click.position);
    }, cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private lngLatAt(position: CesiumTypes.Cartesian2): [number, number] | null {
    if (!this.viewer || !this.cesium) return null;
    const hit = this.viewer.camera.pickEllipsoid(position);
    if (!hit) return null;
    const place = this.cesium.Cartographic.fromCartesian(hit);
    return [this.cesium.Math.toDegrees(place.longitude), this.cesium.Math.toDegrees(place.latitude)];
  }

  private entityAt(position: CesiumTypes.Cartesian2): CesiumTypes.Entity | null {
    const picked = this.viewer?.scene.pick(position);
    const entity = picked?.id;
    return entity && this.overlayByEntity.has(entity) ? (entity as CesiumTypes.Entity) : null;
  }

  private propertiesOf(entity: CesiumTypes.Entity): Record<string, unknown> {
    return entity.properties?.getValue(this.cesium!.JulianDate.now()) ?? {};
  }

  private place(element: HTMLElement, position: CesiumTypes.Cartesian2): void {
    element.style.left = `${position.x}px`;
    element.style.top = `${position.y}px`;
  }

  private showHover(position: CesiumTypes.Cartesian2): void {
    if (!this.viewer) return;
    const entity = this.entityAt(position);
    this.viewer.scene.canvas.style.cursor = entity ? 'pointer' : '';
    const field = entity && this.overlayByEntity.get(entity)?.labelField;
    const text = field ? this.propertiesOf(entity)[field] : null;
    if (!text) {
      this.tooltip?.remove();
      this.tooltip = undefined;
      return;
    }
    if (!this.tooltip) {
      this.tooltip = document.createElement('div');
      this.tooltip.className = 'gis-map-tooltip';
      this.viewer.container.appendChild(this.tooltip);
    }
    // textContent throughout, because these values come from imported data.
    this.tooltip.textContent = String(text);
    this.place(this.tooltip, position);
  }

  private showPopup(position: CesiumTypes.Cartesian2): void {
    if (!this.viewer) return;
    const entity = this.entityAt(position);
    if (!entity) return;
    const props = this.propertiesOf(entity);
    const box = document.createElement('div');
    box.className = 'gis-map-popup';
    const title = document.createElement('div');
    title.className = 'gis-popup-title';
    title.textContent = String(props['_layer'] ?? this.overlayByEntity.get(entity)?.label ?? '');
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
    this.place(box, position);
    this.viewer.container.appendChild(box);
    this.popup = box;
  }

  private closePopup(): void {
    this.popup?.remove();
    this.popup = undefined;
  }

  private metres(): number {
    if (!this.viewer || !this.cesium) return metresForZoom(HOME_ZOOM);
    const { camera } = this.viewer;
    if (!this.is3d && camera.frustum instanceof this.cesium.OrthographicOffCenterFrustum) {
      return (camera.frustum.right ?? 0) - (camera.frustum.left ?? 0);
    }
    return camera.positionCartographic.height;
  }

  /** The visible area in degrees. Null when the view runs past the edge of the world. */
  viewBox(): LngLatBox | null {
    const rectangle = this.viewer?.camera.computeViewRectangle();
    if (!rectangle || !this.cesium) return null;
    const deg = this.cesium.Math.toDegrees;
    return [deg(rectangle.west), deg(rectangle.south), deg(rectangle.east), deg(rectangle.north)];
  }

  private reportView(): void {
    const box = this.viewBox();
    if (box) this.callbacks.onViewChanged(box.join(','));
  }

  centre(): { lat: number; lng: number; zoom: number } | null {
    if (!this.viewer) return null;
    const canvas = this.viewer.scene.canvas;
    const point = this.lngLatAt(new this.cesium!.Cartesian2(canvas.clientWidth / 2, canvas.clientHeight / 2));
    return point ? { lng: point[0], lat: point[1], zoom: zoomForMetres(this.metres()) } : null;
  }

  jumpTo(lat: number, lng: number, zoom: number): void {
    this.viewer?.camera.setView({ destination: this.cesium!.Cartesian3.fromDegrees(lng, lat, metresForZoom(zoom)) });
  }

  goHome(): void {
    this.jumpTo(HOME_LAT, HOME_LNG, HOME_ZOOM);
  }

  fitBox([west, south, east, north]: LngLatBox): void {
    if (!this.viewer || !this.cesium) return;
    this.hasFittedData = true;
    // A single point has no size, so it gets a small area around it.
    const pad = (span: number) => (span < SMALLEST_BOX_DEGREES ? SMALLEST_BOX_DEGREES : span * 0.1);
    const lng = pad(east - west);
    const lat = pad(north - south);
    void this.viewer.camera.flyTo({
      destination: this.cesium.Rectangle.fromDegrees(Math.max(west - lng, -180), Math.max(south - lat, -90), Math.min(east + lng, 180), Math.min(north + lat, 90)),
      duration: FLY_SECONDS,
    });
  }

  fitCollection(collection: GisFeatureCollection): void {
    const box = boundsOf([collection]);
    if (box) this.fitBox(box);
  }

  fitAll(): boolean {
    const box = boundsOf([...this.overlays.values()].map((overlay) => overlay.collection));
    if (box) this.fitBox(box);
    return !!box;
  }

  zoomBy(direction: 'in' | 'out'): void {
    if (!this.viewer) return;
    const metres = this.metres();
    // In 2D each amount applies to both sides of the view, in 3D to the camera's height.
    const step = this.is3d ? (direction === 'in' ? metres / 2 : metres) : direction === 'in' ? metres / 4 : metres / 2;
    if (direction === 'in') this.viewer.camera.zoomIn(step);
    else this.viewer.camera.zoomOut(step);
  }

  /** Switches without rebuilding, and keeps showing the same place. */
  setMode(is3d: boolean): void {
    const viewer = this.viewer;
    const cesium = this.cesium;
    if (!viewer || !cesium || this.is3d === is3d) return;
    // A wide view runs past the world's edge and has no box, so its centre and zoom are the fallback.
    const box = this.viewBox();
    const view = this.centre();
    this.is3d = is3d;
    const restore = viewer.scene.morphComplete.addEventListener(() => {
      restore();
      if (box) viewer.camera.setView({ destination: cesium.Rectangle.fromDegrees(...box) });
      else if (view) this.jumpTo(view.lat, view.lng, view.zoom);
      else this.goHome();
      });
    if (is3d) viewer.scene.morphTo3D(MORPH_SECONDS);
    else viewer.scene.morphTo2D(MORPH_SECONDS);
  }
}
