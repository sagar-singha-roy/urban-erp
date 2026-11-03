import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse, PageQuery, PagedResponse } from '../models/white-label.model';
import {
  AccessGrant,
  AccessScope,
  AreaOption,
  CampaignPayload,
  ComponentOption,
  CrossTenantOptions,
  Department,
  GrantFilters,
  GrantPayload,
  HistoryEntry,
  HistoryFilters,
  PermissionRule,
  ReviewCampaign,
  ReviewItem,
  RulePayload,
  ScopePayload,
  UserOption,
} from '../models/cross-tenant.model';

/** ADM-R02 Cross-Tenant Access Management. The auth interceptor adds the token and tenant headers. */
@Injectable({ providedIn: 'root' })
export class CrossTenantService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/iam/cross-tenant`;

  private params(query: PageQuery, extra: Record<string, string | undefined> = {}): HttpParams {
    let params = new HttpParams().set('skip', query.skip).set('limit', query.limit);
    if (query.search) params = params.set('search', query.search);
    for (const [key, value] of Object.entries(extra)) {
      if (value) params = params.set(key, value);
    }
    return params;
  }

  private many(name: string, values: string[]): HttpParams {
    return values.reduce((params, value) => params.append(name, value), new HttpParams());
  }

  getOptions(): Observable<ApiResponse<CrossTenantOptions>> {
    return this.http.get<ApiResponse<CrossTenantOptions>>(`${this.baseUrl}/options`);
  }

  findUsers(search: string): Observable<ApiResponse<UserOption[]>> {
    return this.http.get<ApiResponse<UserOption[]>>(`${this.baseUrl}/lookups/users`, {
      params: search ? { search } : {},
    });
  }

  getAuthorities(): Observable<ApiResponse<UserOption[]>> {
    return this.http.get<ApiResponse<UserOption[]>>(`${this.baseUrl}/lookups/authorities`);
  }

  getComponents(modules: string[]): Observable<ApiResponse<ComponentOption[]>> {
    return this.http.get<ApiResponse<ComponentOption[]>>(`${this.baseUrl}/lookups/components`, {
      params: this.many('module', modules),
    });
  }

  getZones(tenantIds: string[]): Observable<ApiResponse<AreaOption[]>> {
    return this.http.get<ApiResponse<AreaOption[]>>(`${this.baseUrl}/lookups/zones`, {
      params: this.many('tenant_id', tenantIds),
    });
  }

  getWards(tenantIds: string[], zoneIds: string[]): Observable<ApiResponse<AreaOption[]>> {
    const params = zoneIds.reduce(
      (p, z) => p.append('zone_id', z),
      this.many('tenant_id', tenantIds),
    );
    return this.http.get<ApiResponse<AreaOption[]>>(`${this.baseUrl}/lookups/wards`, { params });
  }

  getDepartments(tenantIds: string[]): Observable<ApiResponse<Department[]>> {
    return this.http.get<ApiResponse<Department[]>>(`${this.baseUrl}/departments`, {
      params: this.many('tenant_id', tenantIds),
    });
  }

  createDepartment(payload: {
    tenantId: string;
    code: string;
    name: string;
  }): Observable<ApiResponse<Department>> {
    return this.http.post<ApiResponse<Department>>(`${this.baseUrl}/departments`, payload);
  }

  listGrants(query: PageQuery, filters: GrantFilters = {}): Observable<PagedResponse<AccessGrant>> {
    return this.http.get<PagedResponse<AccessGrant>>(`${this.baseUrl}/grants`, {
      params: this.params(query, {
        status: filters.status,
        access_level: filters.accessLevel,
        user_type: filters.userType,
        user_profile_id: filters.userProfileId,
      }),
    });
  }

  getGrant(id: string): Observable<ApiResponse<AccessGrant>> {
    return this.http.get<ApiResponse<AccessGrant>>(`${this.baseUrl}/grants/${id}`);
  }

  saveGrant(payload: GrantPayload, id?: string): Observable<ApiResponse<AccessGrant>> {
    return id
      ? this.http.put<ApiResponse<AccessGrant>>(`${this.baseUrl}/grants/${id}`, payload)
      : this.http.post<ApiResponse<AccessGrant>>(`${this.baseUrl}/grants`, payload);
  }

  approveGrant(id: string, note: string | null): Observable<ApiResponse<AccessGrant>> {
    return this.http.post<ApiResponse<AccessGrant>>(`${this.baseUrl}/grants/${id}/approve`, {
      note,
    });
  }

  rejectGrant(id: string, reason: string): Observable<ApiResponse<AccessGrant>> {
    return this.http.post<ApiResponse<AccessGrant>>(`${this.baseUrl}/grants/${id}/reject`, {
      reason,
    });
  }

  revokeGrant(id: string, reason: string): Observable<ApiResponse<AccessGrant>> {
    return this.http.post<ApiResponse<AccessGrant>>(`${this.baseUrl}/grants/${id}/revoke`, {
      reason,
    });
  }

  listScopes(query: PageQuery): Observable<PagedResponse<AccessScope>> {
    return this.http.get<PagedResponse<AccessScope>>(`${this.baseUrl}/scopes`, {
      params: this.params(query),
    });
  }

  saveScope(payload: ScopePayload): Observable<ApiResponse<AccessScope>> {
    return this.http.put<ApiResponse<AccessScope>>(`${this.baseUrl}/scopes`, payload);
  }

  listRules(query: PageQuery, reviewStatus?: string): Observable<PagedResponse<PermissionRule>> {
    return this.http.get<PagedResponse<PermissionRule>>(`${this.baseUrl}/rules`, {
      params: this.params(query, { review_status: reviewStatus }),
    });
  }

  saveRule(payload: RulePayload, id?: string): Observable<ApiResponse<PermissionRule>> {
    return id
      ? this.http.put<ApiResponse<PermissionRule>>(`${this.baseUrl}/rules/${id}`, payload)
      : this.http.post<ApiResponse<PermissionRule>>(`${this.baseUrl}/rules`, payload);
  }

  reviewRule(id: string, reviewStatus: string): Observable<ApiResponse<PermissionRule>> {
    return this.http.post<ApiResponse<PermissionRule>>(`${this.baseUrl}/rules/${id}/review`, {
      reviewStatus,
    });
  }

  listCampaigns(query: PageQuery): Observable<PagedResponse<ReviewCampaign>> {
    return this.http.get<PagedResponse<ReviewCampaign>>(`${this.baseUrl}/campaigns`, {
      params: this.params(query),
    });
  }

  createCampaign(payload: CampaignPayload): Observable<ApiResponse<ReviewCampaign>> {
    return this.http.post<ApiResponse<ReviewCampaign>>(`${this.baseUrl}/campaigns`, payload);
  }

  listItems(campaignId: string, query: PageQuery): Observable<PagedResponse<ReviewItem>> {
    return this.http.get<PagedResponse<ReviewItem>>(
      `${this.baseUrl}/campaigns/${campaignId}/items`,
      { params: this.params(query) },
    );
  }

  decideItem(
    campaignId: string,
    itemId: string,
    reviewDecision: string,
    reviewerComments: string | null,
  ): Observable<ApiResponse<ReviewItem>> {
    return this.http.post<ApiResponse<ReviewItem>>(
      `${this.baseUrl}/campaigns/${campaignId}/items/${itemId}/decision`,
      { reviewDecision, reviewerComments },
    );
  }

  private historyParams(query: PageQuery | null, filters: HistoryFilters): HttpParams {
    const extra = { action: filters.action, date_from: filters.dateFrom, date_to: filters.dateTo };
    if (query) return this.params(query, extra);
    let params = new HttpParams();
    for (const [key, value] of Object.entries(extra)) {
      if (value) params = params.set(key, value);
    }
    return params;
  }

  listHistory(query: PageQuery, filters: HistoryFilters): Observable<PagedResponse<HistoryEntry>> {
    return this.http.get<PagedResponse<HistoryEntry>>(`${this.baseUrl}/history`, {
      params: this.historyParams(query, filters),
    });
  }

  getHistoryActions(): Observable<ApiResponse<string[]>> {
    return this.http.get<ApiResponse<string[]>>(`${this.baseUrl}/history/actions`);
  }

  exportHistory(search: string, filters: HistoryFilters): Observable<Blob> {
    let params = this.historyParams(null, filters);
    if (search) params = params.set('search', search);
    return this.http.get(`${this.baseUrl}/history/export`, { params, responseType: 'blob' });
  }
}
