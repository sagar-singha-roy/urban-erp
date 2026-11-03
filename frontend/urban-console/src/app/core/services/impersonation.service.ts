import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse, PageQuery, PagedResponse } from '../models/white-label.model';
import {
  ApproverOption,
  AuditEntry,
  CurrentSession,
  DecisionPayload,
  HubProfile,
  ImpersonationOptions,
  ImpersonationPolicy,
  ImpersonationRequest,
  RequestPayload,
  SessionAction,
  SupportSession,
  TargetOption,
} from '../models/impersonation.model';

/** ADM-R04 Support Impersonation Hub. The session itself lives in an httpOnly cookie the API sets. */
@Injectable({ providedIn: 'root' })
export class ImpersonationService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/impersonation`;

  private params(query: PageQuery, extra: Record<string, string | undefined> = {}): HttpParams {
    let params = new HttpParams().set('skip', query.skip).set('limit', query.limit);
    if (query.search) params = params.set('search', query.search);
    for (const [key, value] of Object.entries(extra)) {
      if (value) params = params.set(key, value);
    }
    return params;
  }

  getOptions(): Observable<ApiResponse<ImpersonationOptions>> {
    return this.http.get<ApiResponse<ImpersonationOptions>>(`${this.baseUrl}/options`);
  }

  getMe(): Observable<ApiResponse<HubProfile>> {
    return this.http.get<ApiResponse<HubProfile>>(`${this.baseUrl}/me`);
  }

  findTargets(search: string): Observable<ApiResponse<TargetOption[]>> {
    return this.http.get<ApiResponse<TargetOption[]>>(`${this.baseUrl}/lookups/targets`, {
      params: search ? { search } : {},
    });
  }

  getApprovers(): Observable<ApiResponse<ApproverOption[]>> {
    return this.http.get<ApiResponse<ApproverOption[]>>(`${this.baseUrl}/lookups/approvers`);
  }

  listPolicies(query: PageQuery): Observable<PagedResponse<ImpersonationPolicy>> {
    return this.http.get<PagedResponse<ImpersonationPolicy>>(`${this.baseUrl}/policies`, {
      params: this.params(query),
    });
  }

  savePolicy(
    payload: ImpersonationPolicy,
    id?: string,
  ): Observable<ApiResponse<ImpersonationPolicy>> {
    return id
      ? this.http.put<ApiResponse<ImpersonationPolicy>>(`${this.baseUrl}/policies/${id}`, payload)
      : this.http.post<ApiResponse<ImpersonationPolicy>>(`${this.baseUrl}/policies`, payload);
  }

  listRequests(query: PageQuery, status?: string): Observable<PagedResponse<ImpersonationRequest>> {
    return this.http.get<PagedResponse<ImpersonationRequest>>(`${this.baseUrl}/requests`, {
      params: this.params(query, { status }),
    });
  }

  createRequest(payload: RequestPayload): Observable<ApiResponse<ImpersonationRequest>> {
    return this.http.post<ApiResponse<ImpersonationRequest>>(`${this.baseUrl}/requests`, payload);
  }

  cancelRequest(id: string): Observable<ApiResponse<ImpersonationRequest>> {
    return this.http.post<ApiResponse<ImpersonationRequest>>(
      `${this.baseUrl}/requests/${id}/cancel`,
      {},
    );
  }

  decide(id: string, payload: DecisionPayload): Observable<ApiResponse<ImpersonationRequest>> {
    return this.http.post<ApiResponse<ImpersonationRequest>>(
      `${this.baseUrl}/requests/${id}/decision`,
      payload,
    );
  }

  startSession(requestId: string): Observable<ApiResponse<SupportSession>> {
    return this.http.post<ApiResponse<SupportSession>>(
      `${this.baseUrl}/requests/${requestId}/start`,
      {},
    );
  }

  listSessions(query: PageQuery, status?: string): Observable<PagedResponse<SupportSession>> {
    return this.http.get<PagedResponse<SupportSession>>(`${this.baseUrl}/sessions`, {
      params: this.params(query, { status }),
    });
  }

  terminate(sessionId: string, reason: string): Observable<ApiResponse<SupportSession>> {
    return this.http.post<ApiResponse<SupportSession>>(
      `${this.baseUrl}/sessions/${sessionId}/terminate`,
      { reason },
    );
  }

  currentSession(): Observable<ApiResponse<CurrentSession>> {
    return this.http.get<ApiResponse<CurrentSession>>(`${this.baseUrl}/session/current`);
  }

  endCurrentSession(): Observable<ApiResponse<CurrentSession>> {
    return this.http.post<ApiResponse<CurrentSession>>(`${this.baseUrl}/session/current/end`, {});
  }

  listAudit(
    query: PageQuery,
    dateFrom?: string,
    dateTo?: string,
  ): Observable<PagedResponse<AuditEntry>> {
    return this.http.get<PagedResponse<AuditEntry>>(`${this.baseUrl}/audit`, {
      params: this.params(query, { date_from: dateFrom, date_to: dateTo }),
    });
  }

  listActions(sessionId: string, query: PageQuery): Observable<PagedResponse<SessionAction>> {
    return this.http.get<PagedResponse<SessionAction>>(
      `${this.baseUrl}/audit/${sessionId}/actions`,
      { params: this.params(query) },
    );
  }

  exportAudit(search: string, dateFrom?: string, dateTo?: string): Observable<Blob> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries({ search, date_from: dateFrom, date_to: dateTo })) {
      if (value) params = params.set(key, value);
    }
    return this.http.get(`${this.baseUrl}/audit/export`, { params, responseType: 'blob' });
  }
}
