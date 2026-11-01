import { Component, OnInit, WritableSignal, inject, signal, computed } from '@angular/core';
import { PagerState, TablePagerComponent } from '../../../../shared/components/table-pager/table-pager.component';
import { Observable } from 'rxjs';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { DataNoticeComponent } from '../../../../shared/components/data-notice/data-notice.component';
import { ExecutiveService } from '../../../../core/services/executive.service';
import { DialogService } from '../../../../core/services/dialog.service';
import {
  GlobalOverviewStats,
  RevenueAnalyticsStats,
  ParcelStatisticsStats,
  GrievanceOverviewStats,
  CitizenAdoptionStats,
  ExecutiveDataStatus,
  ExecutiveFilterOptions,
} from '../../../../core/models/executive.model';

export type ExecutiveTab = 'overview' | 'revenue' | 'parcels' | 'grievances' | 'adoption';

@Component({
  selector: 'app-global-command-dashboard',
  standalone: true,
  imports: [TablePagerComponent, CommonModule, FormsModule, IconComponent, RefreshButtonComponent, DataNoticeComponent],
  templateUrl: './global-command-dashboard.component.html',
  styleUrl: './global-command-dashboard.component.scss',
})
export class GlobalCommandDashboardComponent implements OnInit {
  readonly pagers = new PagerState();
  private executiveService = inject(ExecutiveService);
  private dialogService = inject(DialogService);

  readonly activeTab = signal<ExecutiveTab>('overview');
  readonly isLoading = signal<boolean>(false);
  readonly isExporting = signal<boolean>(false);
  readonly dataNotice = signal<string>('');
  private loadToken = 0;

  // Filter Options from DB
  readonly filterOptions = signal<ExecutiveFilterOptions>({
    states: [],
    ulbs: [],
    departments: [],
    revenueModules: [],
    revenueCategories: [],
    propertyCategories: [],
    grievanceCategories: [],
    digitalServices: [],
    registrationChannels: [],
    financialYears: [],
    geographicScopes: [],
    aggregationLevels: [],
    ulbCategories: [],
    rankingMethods: [],
    swachhCategories: [],
    swachhSources: [],
  });

  // Overview Filters
  readonly overviewFilters = signal({
    period: 'this_month',
    fromDate: '',
    toDate: '',
    geoScope: 'All India / All Configured States',
    stateTenant: '',
    ulbTenant: '',
    department: '',
    refreshInterval: 'manual',
    comparisonPeriod: 'Previous Period',
  });

  // Revenue Filters
  readonly revenueFilters = signal({
    stateTenant: '',
    ulbTenant: '',
    revenueModule: '',
    revenueCategory: '',
    financialYear: 'FY 2026-27',
    fromDate: '',
    toDate: '',
    revenueComparison: 'vs Prior Year',
    aggregationLevel: 'State',
    chartType: 'Bar Chart',
  });

  // Parcel Filters
  readonly parcelFilters = signal({
    stateTenant: '',
    ulbTenant: '',
    district: '',
    ward: '',
    propertyCategory: '',
    registrationStatus: '',
    surveyStatus: 'all',
    gisStatus: 'all',
    reportingPeriod: 'this_month',
  });

  // Grievance Filters
  readonly grievanceFilters = signal({
    stateTenant: '',
    ulbTenant: '',
    department: '',
    category: '',
    priority: '',
    status: '',
    slaStatus: 'all',
    assignedOfficer: '',
    reportingPeriod: 'this_month',
    fromDate: '',
    toDate: '',
  });

  // Citizen Adoption Filters
  readonly citizenFilters = signal({
    stateTenant: '',
    ulbTenant: '',
    digitalService: '',
    registrationChannel: '',
    citizenType: 'All Citizens',
    reportingPeriod: 'this_month',
    fromDate: '',
    toDate: '',
    comparisonPeriod: 'vs Prior Year',
  });

  // Data Stores with Immediate Default Benchmarks (Page is never empty)
  readonly overviewData = signal<GlobalOverviewStats | null>(null);
  readonly revenueData = signal<RevenueAnalyticsStats | null>(null);
  readonly parcelData = signal<ParcelStatisticsStats | null>(null);
  readonly grievanceData = signal<GrievanceOverviewStats | null>(null);
  readonly citizenData = signal<CitizenAdoptionStats | null>(null);

  // Search filter inside tables
  readonly tableSearch = signal<string>('');

  readonly filteredBenchmarks = computed(() => {
    const data = this.overviewData();
    if (!data || !data.stateBenchmarks) return [];
    const q = this.tableSearch().trim().toLowerCase();
    if (!q) return data.stateBenchmarks;
    return data.stateBenchmarks.filter(
      (b) =>
        b.stateName.toLowerCase().includes(q) ||
        b.stateCode.toLowerCase().includes(q) ||
        b.status.toLowerCase().includes(q)
    );
  });

  ngOnInit(): void {
    this.loadFilterOptions();
    this.loadActiveTabData(false);
  }

  setTab(tab: ExecutiveTab): void {
    this.activeTab.set(tab);
    this.tableSearch.set('');
    this.loadActiveTabData(false);
  }

  loadFilterOptions(): void {
    this.executiveService.getFilterOptions().subscribe({
      next: (opts) => {
        if (opts && opts.states?.length > 0) {
          this.filterOptions.set(opts);
        }
      },
      error: () => this.dialogService.showToast('Could not load filter options.', 'error', 3000),
    });
  }

  refreshData(): void {
    this.loadActiveTabData(true);
  }

  loadActiveTabData(isUserRefresh = false): void {
    switch (this.activeTab()) {
      case 'overview':
        this.load(this.executiveService.getOverview(this.overviewFilters()), this.overviewData, isUserRefresh, 'Overview refreshed.');
        break;
      case 'revenue':
        this.load(this.executiveService.getRevenueAnalytics(this.revenueFilters()), this.revenueData, isUserRefresh, 'Revenue analytics refreshed.');
        break;
      case 'parcels':
        this.load(this.executiveService.getParcelStatistics(this.parcelFilters()), this.parcelData, isUserRefresh, 'Parcel statistics refreshed.');
        break;
      case 'grievances':
        this.load(this.executiveService.getGrievanceOverview(this.grievanceFilters()), this.grievanceData, isUserRefresh, 'Grievance overview refreshed.');
        break;
      case 'adoption':
        this.load(this.executiveService.getCitizenAdoption(this.citizenFilters()), this.citizenData, isUserRefresh, 'Citizen adoption refreshed.');
        break;
    }
  }

  // Values the API could not source arrive as null and must never render as figures
  show(val: unknown): string {
    return val === null || val === undefined || val === '' ? 'Not available' : String(val);
  }

  formatPct(val: unknown): string {
    return val === null || val === undefined ? 'Not available' : `${val}%`;
  }

  private load<T>(
    request: Observable<T>,
    target: WritableSignal<T | null>,
    isUserRefresh: boolean,
    successMessage: string,
  ): void {
    const token = ++this.loadToken;
    this.isLoading.set(true);
    this.dataNotice.set('');
    target.set(null);
    request.subscribe({
      next: (res) => {
        if (token !== this.loadToken) return;
        const status = res as unknown as ExecutiveDataStatus;
        target.set(status.dataAvailable === false ? null : res);
        this.dataNotice.set(status.unavailableReason ?? '');
        this.isLoading.set(false);
        if (isUserRefresh) {
          this.dialogService.showToast(successMessage, 'success', 2500);
        }
      },
      error: () => {
        if (token !== this.loadToken) return;
        this.dataNotice.set('This data could not be loaded. Nothing shown here should be relied on until a refresh succeeds.');
        this.isLoading.set(false);
        this.dialogService.showToast('Could not load this data.', 'error', 3500);
      },
    });
  }

  applyFilters(): void {
    this.loadActiveTabData(false);
    this.dialogService.showToast('Analytics filters applied successfully.', 'info', 2000);
  }

  resetFilters(): void {
    switch (this.activeTab()) {
      case 'overview':
        this.overviewFilters.set({
          period: 'this_month',
          fromDate: '',
          toDate: '',
          geoScope: 'All India / All Configured States',
          stateTenant: '',
          ulbTenant: '',
          department: '',
          refreshInterval: 'manual',
          comparisonPeriod: 'Previous Period',
        });
        break;
      case 'revenue':
        this.revenueFilters.set({
          stateTenant: '',
          ulbTenant: '',
          revenueModule: '',
          revenueCategory: '',
          financialYear: 'FY 2026-27',
          fromDate: '',
          toDate: '',
          revenueComparison: 'vs Prior Year',
          aggregationLevel: 'State',
          chartType: 'Bar Chart',
        });
        break;
      case 'parcels':
        this.parcelFilters.set({
          stateTenant: '',
          ulbTenant: '',
          district: '',
          ward: '',
          propertyCategory: '',
          registrationStatus: '',
          surveyStatus: 'all',
          gisStatus: 'all',
          reportingPeriod: 'this_month',
        });
        break;
      case 'grievances':
        this.grievanceFilters.set({
          stateTenant: '',
          ulbTenant: '',
          department: '',
          category: '',
          priority: '',
          status: '',
          slaStatus: 'all',
          assignedOfficer: '',
          reportingPeriod: 'this_month',
          fromDate: '',
          toDate: '',
        });
        break;
      case 'adoption':
        this.citizenFilters.set({
          stateTenant: '',
          ulbTenant: '',
          digitalService: '',
          registrationChannel: '',
          citizenType: 'All Citizens',
          reportingPeriod: 'this_month',
          fromDate: '',
          toDate: '',
          comparisonPeriod: 'vs Prior Year',
        });
        break;
    }
    this.loadActiveTabData(false);
    this.dialogService.showToast('Filters reset to defaults.', 'info', 2000);
  }

  async exportReport(): Promise<void> {
    this.dialogService.showToast('Report export is not available yet.', 'info', 3000);
  }

  // Format INR currency values to Indian Crore / Lakh notation
  formatInr(val: number | null | undefined): string {
    if (val === null || val === undefined) return 'Not available';
    if (val >= 10000000) {
      return `₹${(val / 10000000).toLocaleString('en-IN', { maximumFractionDigits: 1 })} Cr`;
    }
    if (val >= 100000) {
      return `₹${(val / 100000).toLocaleString('en-IN', { maximumFractionDigits: 1 })} L`;
    }
    return `₹${val.toLocaleString('en-IN')}`;
  }

  // Format large counts
  formatNumber(val: number | null | undefined): string {
    if (val === null || val === undefined) return 'Not available';
    if (val >= 10000000) {
      return `${(val / 10000000).toFixed(1)} Cr`;
    }
    if (val >= 1000000) {
      return `${(val / 1000000).toFixed(1)}M`;
    }
    if (val >= 1000) {
      return `${(val / 1000).toFixed(1)}k`;
    }
    return val.toLocaleString('en-IN');
  }

}
