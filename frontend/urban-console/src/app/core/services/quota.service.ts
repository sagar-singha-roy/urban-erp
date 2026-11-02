import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse, PageQuery, PagedResponse } from '../models/white-label.model';
import {
  AlertEvent, AlertRule, ApiPolicy, QuotaOptions, RecipientOption, SmsAllocation, StorageAllocation, StorageUsageFilters,
  StorageUsageRow, ThresholdLevel,
} from '../models/quota.model';

@Injectable({ providedIn: 'root' })
export class QuotaService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/modules/quotas`;

  private params(query: PageQuery): HttpParams {
    let params = new HttpParams().set('skip', query.skip).set('limit', query.limit);
    if (query.search) params = params.set('search', query.search);
    return params;
  }

  private list<T>(path: string, query: PageQuery): Observable<PagedResponse<T>> {
    return this.http.get<PagedResponse<T>>(`${this.baseUrl}/${path}`, { params: this.params(query) });
  }

  private save<T>(path: string, payload: T, id?: string): Observable<ApiResponse<T>> {
    return id ? this.http.put<ApiResponse<T>>(`${this.baseUrl}/${path}/${id}`, payload) : this.http.post<ApiResponse<T>>(`${this.baseUrl}/${path}`, payload);
  }

  getOptions(): Observable<ApiResponse<QuotaOptions>> {
    return this.http.get<ApiResponse<QuotaOptions>>(`${this.baseUrl}/options`);
  }

  getRecipients(): Observable<ApiResponse<RecipientOption[]>> {
    return this.http.get<ApiResponse<RecipientOption[]>>(`${this.baseUrl}/recipients`);
  }

  listStorage(query: PageQuery): Observable<PagedResponse<StorageAllocation>> {
    return this.list('storage/allocations', query);
  }

  saveStorage(payload: StorageAllocation, id?: string): Observable<ApiResponse<StorageAllocation>> {
    return this.save('storage/allocations', payload, id);
  }

  storageUsage(query: PageQuery, filters: StorageUsageFilters): Observable<PagedResponse<StorageUsageRow>> {
    let params = this.params(query);
    const single: [string, string | number | null | undefined][] = [
      ['tenant_level', filters.tenantLevel], ['state_tenant_id', filters.stateTenantId], ['ulb_tenant_id', filters.ulbTenantId],
      ['storage_provider', filters.storageProvider], ['storage_type', filters.storageType],
      ['date_from', filters.dateFrom ? `${filters.dateFrom}T00:00:00` : ''], ['date_to', filters.dateTo ? `${filters.dateTo}T23:59:59` : ''],
      ['usage_state', filters.usageState], ['min_percentage', filters.minPercentage], ['max_percentage', filters.maxPercentage],
    ];
    for (const [name, value] of single) {
      if (value !== null && value !== undefined && value !== '') params = params.set(name, value);
    }
    for (const module of filters.modules ?? []) params = params.append('module', module);
    return this.http.get<PagedResponse<StorageUsageRow>>(`${this.baseUrl}/storage/usage`, { params });
  }

  listSms(query: PageQuery): Observable<PagedResponse<SmsAllocation>> {
    return this.list('sms/allocations', query);
  }

  saveSms(payload: SmsAllocation, id?: string): Observable<ApiResponse<SmsAllocation>> {
    return this.save('sms/allocations', payload, id);
  }

  listPolicies(query: PageQuery): Observable<PagedResponse<ApiPolicy>> {
    return this.list('api/policies', query);
  }

  savePolicy(payload: ApiPolicy, id?: string): Observable<ApiResponse<ApiPolicy>> {
    return this.save('api/policies', payload, id);
  }

  listRules(query: PageQuery): Observable<PagedResponse<AlertRule>> {
    return this.list('alerts/rules', query);
  }

  saveRule(payload: AlertRule, id?: string): Observable<ApiResponse<AlertRule>> {
    return this.save('alerts/rules', payload, id);
  }

  listEvents(query: PageQuery): Observable<PagedResponse<AlertEvent>> {
    return this.list('alerts/events', query);
  }

  acknowledgeEvent(id: string): Observable<ApiResponse<AlertEvent>> {
    return this.http.post<ApiResponse<AlertEvent>>(`${this.baseUrl}/alerts/events/${id}/acknowledge`, {});
  }

  getLevels(): Observable<ApiResponse<ThresholdLevel[]>> {
    return this.http.get<ApiResponse<ThresholdLevel[]>>(`${this.baseUrl}/alerts/levels`);
  }

  updateLevel(id: string, percentage: number): Observable<ApiResponse<ThresholdLevel>> {
    return this.http.put<ApiResponse<ThresholdLevel>>(`${this.baseUrl}/alerts/levels/${id}`, { percentage });
  }
}
