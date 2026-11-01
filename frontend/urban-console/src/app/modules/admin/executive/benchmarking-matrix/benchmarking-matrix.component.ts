import { Component, OnInit, WritableSignal, inject, signal, computed } from '@angular/core';
import { PagerState, TablePagerComponent } from '../../../../shared/components/table-pager/table-pager.component';
import { Observable } from 'rxjs';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { DataNoticeComponent } from '../../../../shared/components/data-notice/data-notice.component';
import { DialogService } from '../../../../core/services/dialog.service';
import { ExecutiveService } from '../../../../core/services/executive.service';
import {
  ExecutiveDataStatus,
  ExecutiveFilterOptions,
  StateComparisonResponse,
  CityComparisonResponse,
  DcbRecoveryResponse,
  SlaComplianceResponse,
  SwachhRankingsResponse,
} from '../../../../core/models/executive.model';
import { BenchmarkNotesDialogComponent } from './dialogs/benchmark-notes-dialog.component';

export type BenchmarkingTab = 'state' | 'city' | 'dcb' | 'sla' | 'swachh';

@Component({
  selector: 'app-benchmarking-matrix',
  standalone: true,
  imports: [TablePagerComponent, CommonModule, FormsModule, IconComponent, RefreshButtonComponent, DataNoticeComponent, BenchmarkNotesDialogComponent],
  templateUrl: './benchmarking-matrix.component.html',
  styleUrl: './benchmarking-matrix.component.scss',
})
export class BenchmarkingMatrixComponent implements OnInit {
  readonly pagers = new PagerState();
  private executiveService = inject(ExecutiveService);
  private dialogService = inject(DialogService);

  readonly activeTab = signal<BenchmarkingTab>('state');
  readonly isLoading = signal<boolean>(false);
  readonly isExporting = signal<boolean>(false);
  readonly dataNotice = signal<string>('');
  private loadToken = 0;
  readonly showNotesModal = signal<boolean>(false);

  // Dynamic filter options with comprehensive fallbacks
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

  // A. State Comparison Filter Model
  readonly stateFilters = signal({
    benchmarkName: 'National Urban Governance League FY26',
    financialYear: 'FY 2026-27',
    benchmarkPeriod: 'Q2 (Jul - Sep)',
    selectedStates: '',
    performanceIndicators: 'All Standard Indicators',
    comparisonMethod: 'Normalized Composite Score',
    rankingMetric: 'Composite Score',
    minThreshold: null as number | null,
    maxThreshold: null as number | null,
    comparisonNotes: '',
  });

  // B. City Comparison Filter Model
  readonly cityFilters = signal({
    stateTenant: '',
    selectedUlbs: '',
    financialYear: 'FY 2026-27',
    comparisonPeriod: 'Year to Date (YTD)',
    ulbCategory: '',
    district: '',
    performanceIndicators: 'All Core Indicators',
    rankingMethod: 'Weighted Composite Score',
    comparisonNotes: '',
  });

  // C. DCB Recovery Filter Model
  readonly dcbFilters = signal({
    financialYear: 'FY 2026-27',
    stateTenant: '',
    ulbTenant: '',
    revenueModule: '',
    revenueCategory: '',
    taxFeeType: '',
    comparisonPeriod: 'Previous Period',
  });

  // D. SLA Compliance Filter Model
  readonly slaFilters = signal({
    stateTenant: '',
    ulbTenant: '',
    department: '',
    serviceCategory: '',
    grievanceCategory: '',
    slaTarget: 48,
    reportingPeriod: 'this_month',
    fromDate: '',
    toDate: '',
    complianceThreshold: 85,
  });

  // E. Swachh Rankings Filter Model
  readonly swachhFilters = signal({
    assessmentYear: '2026',
    assessmentCycle: 'Annual National Assessment',
    stateTenant: '',
    ulbTenant: '',
    ulbCategory: '',
    rankingCategory: 'Population > 10 Lakhs',
    indicator: '',
    externalRankingSource: 'Ministry of Housing & Urban Affairs (MoHUA)',
  });

  // Data Stores with Immediate Default Benchmarks (Page never loads blank)
  readonly stateData = signal<StateComparisonResponse | null>(null);
  readonly cityData = signal<CityComparisonResponse | null>(null);
  readonly dcbData = signal<DcbRecoveryResponse | null>(null);
  readonly slaData = signal<SlaComplianceResponse | null>(null);
  readonly swachhData = signal<SwachhRankingsResponse | null>(null);

  // Search filter inside active table
  readonly tableSearch = signal<string>('');

  // Filtered lists based on search
  readonly filteredStates = computed(() => {
    const data = this.stateData();
    if (!data?.benchmarks) return [];
    const q = this.tableSearch().trim().toLowerCase();
    if (!q) return data.benchmarks;
    return data.benchmarks.filter(
      (s) =>
        s.stateName.toLowerCase().includes(q) ||
        s.stateCode.toLowerCase().includes(q) ||
        s.performanceTier.toLowerCase().includes(q)
    );
  });

  readonly filteredCities = computed(() => {
    const data = this.cityData();
    if (!data?.benchmarks) return [];
    const q = this.tableSearch().trim().toLowerCase();
    if (!q) return data.benchmarks;
    return data.benchmarks.filter(
      (c) =>
        c.ulbName.toLowerCase().includes(q) ||
        c.ulbCode.toLowerCase().includes(q) ||
        c.district.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q)
    );
  });

  readonly filteredDcbModules = computed(() => {
    const data = this.dcbData();
    if (!data?.moduleBreakdown) return [];
    const q = this.tableSearch().trim().toLowerCase();
    if (!q) return data.moduleBreakdown;
    return data.moduleBreakdown.filter(
      (m) => m.moduleName.toLowerCase().includes(q) || m.moduleCode.toLowerCase().includes(q)
    );
  });

  readonly filteredSlaDepartments = computed(() => {
    const data = this.slaData();
    if (!data?.departmentMatrix) return [];
    const q = this.tableSearch().trim().toLowerCase();
    if (!q) return data.departmentMatrix;
    return data.departmentMatrix.filter(
      (d) => d.department.toLowerCase().includes(q) || d.breachRisk.toLowerCase().includes(q)
    );
  });

  readonly filteredSwachhUlbs = computed(() => {
    const data = this.swachhData();
    if (!data?.nationalRankings) return [];
    const q = this.tableSearch().trim().toLowerCase();
    if (!q) return data.nationalRankings;
    return data.nationalRankings.filter(
      (u) =>
        u.ulbName.toLowerCase().includes(q) ||
        u.stateName.toLowerCase().includes(q) ||
        u.gfcStar.toLowerCase().includes(q)
    );
  });

  ngOnInit(): void {
    this.loadFilterOptions();
    this.loadActiveTabData(false);
  }

  setTab(tab: BenchmarkingTab): void {
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
      case 'state':
        this.load(this.executiveService.getStateComparison(this.stateFilters()), this.stateData, isUserRefresh, 'State comparison refreshed.');
        break;
      case 'city':
        this.load(this.executiveService.getCityComparison(this.cityFilters()), this.cityData, isUserRefresh, 'City comparison refreshed.');
        break;
      case 'dcb':
        this.load(this.executiveService.getDcbRecovery(this.dcbFilters()), this.dcbData, isUserRefresh, 'DCB figures refreshed.');
        break;
      case 'sla':
        this.load(this.executiveService.getSlaCompliance(this.slaFilters()), this.slaData, isUserRefresh, 'SLA compliance refreshed.');
        break;
      case 'swachh':
        this.load(this.executiveService.getSwachhRankings(this.swachhFilters()), this.swachhData, isUserRefresh, 'Swachh rankings refreshed.');
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
    this.loadActiveTabData(true);
  }

  resetFilters(): void {
    switch (this.activeTab()) {
      case 'state':
        this.stateFilters.set({
          benchmarkName: 'National Urban Governance League FY26',
          financialYear: 'FY 2026-27',
          benchmarkPeriod: 'Q2 (Jul - Sep)',
          selectedStates: '',
          performanceIndicators: 'All Standard Indicators',
          comparisonMethod: 'Normalized Composite Score',
          rankingMetric: 'Composite Score',
          minThreshold: null,
          maxThreshold: null,
          comparisonNotes: '',
        });
        break;
      case 'city':
        this.cityFilters.set({
          stateTenant: '',
          selectedUlbs: '',
          financialYear: 'FY 2026-27',
          comparisonPeriod: 'Year to Date (YTD)',
          ulbCategory: '',
          district: '',
          performanceIndicators: 'All Core Indicators',
          rankingMethod: 'Weighted Composite Score',
          comparisonNotes: '',
        });
        break;
      case 'dcb':
        this.dcbFilters.set({
          financialYear: 'FY 2026-27',
          stateTenant: '',
          ulbTenant: '',
          revenueModule: '',
          revenueCategory: '',
          taxFeeType: '',
          comparisonPeriod: 'Previous Period',
        });
        break;
      case 'sla':
        this.slaFilters.set({
          stateTenant: '',
          ulbTenant: '',
          department: '',
          serviceCategory: '',
          grievanceCategory: '',
          slaTarget: 48,
          reportingPeriod: 'this_month',
          fromDate: '',
          toDate: '',
          complianceThreshold: 85,
        });
        break;
      case 'swachh':
        this.swachhFilters.set({
          assessmentYear: '2026',
          assessmentCycle: 'Annual National Assessment',
          stateTenant: '',
          ulbTenant: '',
          ulbCategory: '',
          rankingCategory: 'Population > 10 Lakhs',
          indicator: '',
          externalRankingSource: 'Ministry of Housing & Urban Affairs (MoHUA)',
        });
        break;
    }
    this.tableSearch.set('');
    this.loadActiveTabData(false);
    this.dialogService.showToast('Filters reset to default scope.', 'info', 2000);
  }

  exportReport(): void {
    this.dialogService.showToast('Report export is not available yet.', 'info', 3000);
  }

  openNotesModal(): void {
    this.showNotesModal.set(true);
  }

  handleSaveNotes(): void {
    this.showNotesModal.set(false);
    this.dialogService.showToast('Notes cannot be saved yet, so this note was not recorded.', 'info', 3500);
  }

  // Formatters
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

  formatNumber(val: number | null | undefined): string {
    if (val === null || val === undefined) return 'Not available';
    if (val >= 10000000) {
      return `${(val / 10000000).toFixed(1)} Cr`;
    }
    if (val >= 100000) {
      return `${(val / 100000).toFixed(1)} L`;
    }
    if (val >= 1000) {
      return `${(val / 1000).toFixed(1)}k`;
    }
    return val.toLocaleString('en-IN');
  }

}
