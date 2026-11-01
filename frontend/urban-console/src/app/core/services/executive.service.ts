import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { KeycloakAuthService } from './keycloak.service';
import { environment } from '../../../environments/environment';
import {
  GlobalOverviewStats,
  RevenueAnalyticsStats,
  ParcelStatisticsStats,
  GrievanceOverviewStats,
  CitizenAdoptionStats,
  ExecutiveFilterOptions,
  StateComparisonResponse,
  CityComparisonResponse,
  DcbRecoveryResponse,
  SlaComplianceResponse,
  SwachhRankingsResponse,
  GrantsOverviewStats,
  GrantAllocationResponse,
  GrantAllocationItem,
  GrantAllocationCreate,
  FinancialSummaryStats,
  TenantLedgerResponse,
  ReconciliationResponse,
} from '../models/executive.model';

export interface ApiResponse<T> {
  success?: boolean;
  statusCode?: number;
  message?: string;
  data: T;
}

function unwrapResponse<T>(res: ApiResponse<T> | T): T {
  if (res && typeof res === 'object' && 'data' in res) {
    return (res as ApiResponse<T>).data;
  }
  return res as T;
}

@Injectable({
  providedIn: 'root',
})
export class ExecutiveService {
  private http = inject(HttpClient);
  private authService = inject(KeycloakAuthService);
  private baseUrl = `${environment.apiUrl}/executive`;

  private getHeaders(): HttpHeaders {
    return this.authService.getHeaders();
  }

  private buildParams(filterObj: Record<string, any>): HttpParams {
    let params = new HttpParams();
    Object.keys(filterObj).forEach((key) => {
      const val = filterObj[key];
      if (val !== undefined && val !== null && val !== '') {
        if (Array.isArray(val)) {
          if (val.length > 0) {
            params = params.set(key, val.join(','));
          }
        } else {
          params = params.set(key, String(val));
        }
      }
    });
    return params;
  }

  getFilterOptions(): Observable<ExecutiveFilterOptions> {
    return this.http
      .get<ApiResponse<ExecutiveFilterOptions>>(`${this.baseUrl}/filter-options`, {
        headers: this.getHeaders(),
      })
      .pipe(map(unwrapResponse));
  }

  getOverview(filters: Record<string, any> = {}): Observable<GlobalOverviewStats> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<GlobalOverviewStats>>(`${this.baseUrl}/overview`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getRevenueAnalytics(filters: Record<string, any> = {}): Observable<RevenueAnalyticsStats> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<RevenueAnalyticsStats>>(`${this.baseUrl}/revenue-analytics`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getParcelStatistics(filters: Record<string, any> = {}): Observable<ParcelStatisticsStats> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<ParcelStatisticsStats>>(`${this.baseUrl}/parcel-statistics`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getGrievanceOverview(filters: Record<string, any> = {}): Observable<GrievanceOverviewStats> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<GrievanceOverviewStats>>(`${this.baseUrl}/grievance-overview`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getCitizenAdoption(filters: Record<string, any> = {}): Observable<CitizenAdoptionStats> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<CitizenAdoptionStats>>(`${this.baseUrl}/citizen-adoption`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  // ADM-A02: State & City Benchmarking Matrix
  getStateComparison(filters: Record<string, any> = {}): Observable<StateComparisonResponse> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<StateComparisonResponse>>(`${this.baseUrl}/benchmarks/state-comparison`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getCityComparison(filters: Record<string, any> = {}): Observable<CityComparisonResponse> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<CityComparisonResponse>>(`${this.baseUrl}/benchmarks/city-comparison`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getDcbRecovery(filters: Record<string, any> = {}): Observable<DcbRecoveryResponse> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<DcbRecoveryResponse>>(`${this.baseUrl}/benchmarks/dcb-recovery`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getSlaCompliance(filters: Record<string, any> = {}): Observable<SlaComplianceResponse> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<SlaComplianceResponse>>(`${this.baseUrl}/benchmarks/sla-compliance`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getSwachhRankings(filters: Record<string, any> = {}): Observable<SwachhRankingsResponse> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<SwachhRankingsResponse>>(`${this.baseUrl}/benchmarks/swachh-rankings`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  // ADM-A03: Consolidated Financial Ledger
  getGrantsOverview(filters: Record<string, any> = {}): Observable<GrantsOverviewStats> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<GrantsOverviewStats>>(`${this.baseUrl}/financial/grants-overview`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getGrantAllocations(filters: Record<string, any> = {}): Observable<GrantAllocationResponse> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<GrantAllocationResponse>>(`${this.baseUrl}/financial/grant-allocations`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  createGrantAllocation(payload: GrantAllocationCreate): Observable<GrantAllocationItem> {
    return this.http
      .post<ApiResponse<GrantAllocationItem>>(`${this.baseUrl}/financial/grant-allocations`, payload, {
        headers: this.getHeaders(),
      })
      .pipe(map(unwrapResponse));
  }

  getFinancialSummary(filters: Record<string, any> = {}): Observable<FinancialSummaryStats> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<FinancialSummaryStats>>(`${this.baseUrl}/financial/summary`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getTenantLedger(filters: Record<string, any> = {}): Observable<TenantLedgerResponse> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<TenantLedgerResponse>>(`${this.baseUrl}/financial/tenant-ledger`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }

  getFinancialReconciliation(filters: Record<string, any> = {}): Observable<ReconciliationResponse> {
    const params = this.buildParams(filters);
    return this.http
      .get<ApiResponse<ReconciliationResponse>>(`${this.baseUrl}/financial/reconciliation`, {
        headers: this.getHeaders(),
        params,
      })
      .pipe(map(unwrapResponse));
  }
}

