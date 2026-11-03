import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ApiResponse, AssetSet, BrandingProfile, DomainMapping, PageQuery, PagedResponse, RoutingStatus, TenantCertificate,
  TenantDomain, TenantOption, WhiteLabelOptions,
} from '../models/white-label.model';

@Injectable({ providedIn: 'root' })
export class WhiteLabelService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/white-label`;

  private params(query: PageQuery): HttpParams {
    let params = new HttpParams().set('skip', query.skip).set('limit', query.limit);
    if (query.search) params = params.set('search', query.search);
    if (query.tenantId) params = params.set('tenant_id', query.tenantId);
    return params;
  }

  getOptions(): Observable<ApiResponse<WhiteLabelOptions>> {
    return this.http.get<ApiResponse<WhiteLabelOptions>>(`${this.baseUrl}/options`);
  }

  getTenants(search?: string): Observable<ApiResponse<TenantOption[]>> {
    const params = search ? new HttpParams().set('search', search) : undefined;
    return this.http.get<ApiResponse<TenantOption[]>>(`${this.baseUrl}/tenants`, { params });
  }

  listBranding(query: PageQuery): Observable<PagedResponse<BrandingProfile>> {
    return this.http.get<PagedResponse<BrandingProfile>>(`${this.baseUrl}/branding`, { params: this.params(query) });
  }

  saveBranding(payload: BrandingProfile, id?: string): Observable<ApiResponse<BrandingProfile>> {
    return id
      ? this.http.put<ApiResponse<BrandingProfile>>(`${this.baseUrl}/branding/${id}`, payload)
      : this.http.post<ApiResponse<BrandingProfile>>(`${this.baseUrl}/branding`, payload);
  }

  listAssets(query: PageQuery): Observable<PagedResponse<AssetSet>> {
    return this.http.get<PagedResponse<AssetSet>>(`${this.baseUrl}/assets`, { params: this.params(query) });
  }

  uploadAssets(form: FormData): Observable<ApiResponse<AssetSet>> {
    return this.http.post<ApiResponse<AssetSet>>(`${this.baseUrl}/assets`, form);
  }

  updateAssets(id: string, payload: { altText: string; effectiveFrom: string | null; assetStatus: string }): Observable<ApiResponse<AssetSet>> {
    return this.http.put<ApiResponse<AssetSet>>(`${this.baseUrl}/assets/${id}`, payload);
  }

  assetPreviewUrl(fileId: string): string {
    return `${this.baseUrl}/assets/files/${fileId}`;
  }

  listDomains(query: PageQuery): Observable<PagedResponse<TenantDomain>> {
    return this.http.get<PagedResponse<TenantDomain>>(`${this.baseUrl}/domains`, { params: this.params(query) });
  }

  createDomain(payload: object): Observable<ApiResponse<TenantDomain>> {
    return this.http.post<ApiResponse<TenantDomain>>(`${this.baseUrl}/domains`, payload);
  }

  updateDomain(id: string, payload: object): Observable<ApiResponse<TenantDomain>> {
    return this.http.put<ApiResponse<TenantDomain>>(`${this.baseUrl}/domains/${id}`, payload);
  }

  verifyDomain(id: string): Observable<ApiResponse<TenantDomain>> {
    return this.http.post<ApiResponse<TenantDomain>>(`${this.baseUrl}/domains/${id}/verify`, {});
  }

  listCertificates(query: PageQuery): Observable<PagedResponse<TenantCertificate>> {
    return this.http.get<PagedResponse<TenantCertificate>>(`${this.baseUrl}/certificates`, { params: this.params(query) });
  }

  createCertificate(form: FormData): Observable<ApiResponse<TenantCertificate>> {
    return this.http.post<ApiResponse<TenantCertificate>>(`${this.baseUrl}/certificates`, form);
  }

  updateCertificate(id: string, payload: { autoRenewal: boolean; renewalNotificationDays: number }): Observable<ApiResponse<TenantCertificate>> {
    return this.http.put<ApiResponse<TenantCertificate>>(`${this.baseUrl}/certificates/${id}`, payload);
  }

  listMappings(query: PageQuery): Observable<PagedResponse<DomainMapping>> {
    return this.http.get<PagedResponse<DomainMapping>>(`${this.baseUrl}/mappings`, { params: this.params(query) });
  }

  saveMapping(payload: DomainMapping, id?: string): Observable<ApiResponse<DomainMapping>> {
    return id
      ? this.http.put<ApiResponse<DomainMapping>>(`${this.baseUrl}/mappings/${id}`, payload)
      : this.http.post<ApiResponse<DomainMapping>>(`${this.baseUrl}/mappings`, payload);
  }

  getRoutingStatus(): Observable<ApiResponse<RoutingStatus>> {
    return this.http.get<ApiResponse<RoutingStatus>>(`${this.baseUrl}/routing-status`);
  }
}
