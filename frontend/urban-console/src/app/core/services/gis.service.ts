import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { EMPTY, Observable, expand, map, reduce } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  GisApprovedService,
  GisFeatureCollection,
  GisImportResult,
  GisLayer,
  GisOptions,
  GisPage,
  GisScopeRow,
  GisWorkspace,
} from '../models/gis.model';

interface ApiResponse<T> {
  data: T;
}

@Injectable({ providedIn: 'root' })
export class GisService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/executive/gis`;

  private params(filters: Record<string, unknown>): HttpParams {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        if (value.length) params = params.set(key, value.join(','));
      } else if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });
    return params;
  }

  private list<T>(path: string, filters: Record<string, unknown> = {}): Observable<T> {
    return this.http
      .get<ApiResponse<T>>(`${this.baseUrl}${path}`, { params: this.params(filters) })
      .pipe(map((res) => res.data));
  }

  getOptions(tenantId?: string): Observable<GisOptions> {
    return this.list('/options', { tenantId });
  }

  private page<T>(path: string, filters: Record<string, unknown>): Observable<GisPage<T>> {
    return this.http.get<GisPage<T>>(`${this.baseUrl}${path}`, { params: this.params(filters) });
  }

  getScopePage(filters: Record<string, unknown>): Observable<GisPage<GisScopeRow>> {
    return this.page('/scope', filters);
  }

  getLayersPage(filters: Record<string, unknown>): Observable<GisPage<GisLayer>> {
    return this.page('/layers', filters);
  }

  /** Every accessible layer, for dropdowns. Keeps asking until the server has returned them all. */
  getAllLayers(): Observable<GisLayer[]> {
    const size = 100;
    let skip = 0;
    return this.getLayersPage({ skip, limit: size }).pipe(
      expand((page) => {
        skip += size;
        return skip < page.total ? this.getLayersPage({ skip, limit: size }) : EMPTY;
      }),
      reduce((all, page) => [...all, ...page.data], [] as GisLayer[]),
    );
  }

  syncLayer(layerId: string): Observable<GisImportResult> {
    return this.http.post<ApiResponse<GisImportResult>>(`${this.baseUrl}/layers/${layerId}/sync`, {}).pipe(map((res) => res.data));
  }

  getServices(filters: Record<string, unknown>): Observable<GisPage<GisApprovedService>> {
    return this.page('/services', filters);
  }

  saveService(service: GisApprovedService): Observable<GisApprovedService> {
    const request = service.id
      ? this.http.put<ApiResponse<GisApprovedService>>(`${this.baseUrl}/services/${service.id}`, service)
      : this.http.post<ApiResponse<GisApprovedService>>(`${this.baseUrl}/services`, service);
    return request.pipe(map((res) => res.data));
  }

  importBoundaries(payload: { tenantId: string; level: string; matchField: string; sourceCrs: string; featureCollection: unknown }): Observable<GisImportResult> {
    return this.http.post<ApiResponse<GisImportResult>>(`${this.baseUrl}/boundaries/import`, payload).pipe(map((res) => res.data));
  }

  getScopeFeatures(filters: Record<string, unknown>): Observable<GisFeatureCollection> {
    return this.http.get<GisFeatureCollection>(`${this.baseUrl}/features/scope`, { params: this.params(filters) });
  }

  transform(lon: number, lat: number, crs: string): Observable<{ x: number; y: number; crs: string }> {
    return this.http.get<{ x: number; y: number; crs: string }>(`${this.baseUrl}/transform`, { params: this.params({ lon, lat, crs }) });
  }

  saveLayer(layer: Partial<GisLayer>): Observable<GisLayer> {
    const request = layer.id
      ? this.http.put<ApiResponse<GisLayer>>(`${this.baseUrl}/layers/${layer.id}`, layer)
      : this.http.post<ApiResponse<GisLayer>>(`${this.baseUrl}/layers`, layer);
    return request.pipe(map((res) => res.data));
  }

  deleteLayer(id: string): Observable<unknown> {
    return this.http.delete(`${this.baseUrl}/layers/${id}`);
  }

  importFeatures(layerId: string, sourceCrs: string, featureCollection: unknown): Observable<GisImportResult> {
    return this.http
      .post<ApiResponse<GisImportResult>>(`${this.baseUrl}/layers/${layerId}/features`, { sourceCrs, featureCollection })
      .pipe(map((res) => res.data));
  }

  getBoundaries(tenantId: string, level = 'Ward'): Observable<GisFeatureCollection> {
    return this.http.get<GisFeatureCollection>(`${this.baseUrl}/boundaries`, { params: this.params({ tenantId, level }) });
  }

  getFeatures(filters: Record<string, unknown>): Observable<GisFeatureCollection> {
    return this.http.get<GisFeatureCollection>(`${this.baseUrl}/features`, { params: this.params(filters) });
  }

  getParcels(filters: Record<string, unknown>): Observable<GisFeatureCollection> {
    return this.http.get<GisFeatureCollection>(`${this.baseUrl}/parcels`, { params: this.params(filters) });
  }

  getWorkspaces(): Observable<GisWorkspace[]> {
    return this.list('/workspaces', { limit: 100 });
  }

  saveWorkspace(workspace: GisWorkspace): Observable<GisWorkspace> {
    const request = workspace.id
      ? this.http.put<ApiResponse<GisWorkspace>>(`${this.baseUrl}/workspaces/${workspace.id}`, workspace)
      : this.http.post<ApiResponse<GisWorkspace>>(`${this.baseUrl}/workspaces`, workspace);
    return request.pipe(map((res) => res.data));
  }

  deleteWorkspace(id: string): Observable<unknown> {
    return this.http.delete(`${this.baseUrl}/workspaces/${id}`);
  }
}
