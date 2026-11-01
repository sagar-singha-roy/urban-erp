import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  GisFeatureCollection,
  GisImportResult,
  GisLayer,
  GisOptions,
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

  getScope(filters: Record<string, unknown>): Observable<GisScopeRow[]> {
    return this.list('/scope', { ...filters, limit: 100 });
  }

  getLayers(filters: Record<string, unknown>): Observable<GisLayer[]> {
    return this.list('/layers', { ...filters, limit: 100 });
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

  getBoundaries(tenantId: string): Observable<GisFeatureCollection> {
    return this.http.get<GisFeatureCollection>(`${this.baseUrl}/boundaries`, { params: this.params({ tenantId }) });
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
    return this.http
      .post<ApiResponse<GisWorkspace>>(`${this.baseUrl}/workspaces`, workspace)
      .pipe(map((res) => res.data));
  }
}
