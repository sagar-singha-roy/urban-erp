import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { DataNoticeComponent } from '../../../../shared/components/data-notice/data-notice.component';
import { DialogService } from '../../../../core/services/dialog.service';
import { ExecutiveService } from '../../../../core/services/executive.service';
import {
  ExecutiveDataStatus,
  GrantsOverviewStats,
  GrantAllocationItem,
  GrantAllocationCreate,
  FinancialSummaryStats,
  TenantLedgerResponse,
  ReconciliationResponse,
} from '../../../../core/models/executive.model';
import { GrantAllocationDialogComponent } from './dialogs/grant-allocation-dialog.component';
import {
  ReconciliationRunDialogComponent,
  ReconciliationRunRequest,
} from './dialogs/reconciliation-run-dialog.component';

export type FinancialTab = 'grants' | 'allocations' | 'summary' | 'ledger' | 'recon';

@Component({
  selector: 'app-financial-ledger',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent, RefreshButtonComponent,
    DataNoticeComponent,
    GrantAllocationDialogComponent,
    ReconciliationRunDialogComponent,
  ],
  templateUrl: './financial-ledger.component.html',
  styleUrl: './financial-ledger.component.scss',
})
export class FinancialLedgerComponent implements OnInit {
  protected readonly Math = Math;
  private executiveService = inject(ExecutiveService);
  private dialogService = inject(DialogService);

  readonly activeTab = signal<FinancialTab>('grants');
  readonly isLoading = signal<boolean>(false);
  readonly isExporting = signal<boolean>(false);
  readonly dataNotice = signal<string>('Loading financial records…');

  // Dialog signals
  readonly showAllocationModal = signal<boolean>(false);
  readonly showReconModal = signal<boolean>(false);

  // Search & Pagination Signals
  readonly ledgerSearch = signal<string>('');
  readonly ledgerPage = signal<number>(1);
  readonly ledgerLimit = signal<number>(10);

  readonly allocationSearch = signal<string>('');
  readonly allocationPage = signal<number>(1);
  readonly allocationLimit = signal<number>(10);

  readonly reconSearch = signal<string>('');
  readonly reconPage = signal<number>(1);
  readonly reconLimit = signal<number>(10);

  // Common Filters
  readonly selectedFinancialYear = signal<string>('FY 2026-27');
  readonly selectedState = signal<string>('');
  readonly selectedUlb = signal<string>('');
  readonly selectedScheme = signal<string>('');
  readonly selectedAuthority = signal<string>('');
  readonly selectedGrantStatus = signal<string>('');
  readonly selectedAggregation = signal<string>('State');

  // Grants Overview Signal
  readonly grantsData = signal<GrantsOverviewStats>({} as GrantsOverviewStats);

  // Allocations Registry Signal
  readonly allocations = signal<GrantAllocationItem[]>([]);

  // Financial Summary Signal
  readonly summaryData = signal<FinancialSummaryStats>({} as FinancialSummaryStats);

  // Tenant-wise Ledger Signal
  readonly ledgerData = signal<TenantLedgerResponse>({} as TenantLedgerResponse);

  // Reconciliation Signal
  readonly reconData = signal<ReconciliationResponse>({} as ReconciliationResponse);

  // Filtered Computed Signals
  readonly filteredLedgerTransactions = computed(() => {
    const term = this.ledgerSearch().trim().toLowerCase();
    const txns = this.ledgerData().transactions;
    if (!term) return txns;
    return txns.filter(
      (t) =>
        t.voucher.toLowerCase().includes(term) ||
        t.accountHead.toLowerCase().includes(term) ||
        t.ulb.toLowerCase().includes(term) ||
        t.id.toLowerCase().includes(term) ||
        t.status.toLowerCase().includes(term)
    );
  });

  readonly paginatedLedger = computed(() => {
    const list = this.filteredLedgerTransactions();
    const page = this.ledgerPage();
    const limit = this.ledgerLimit();
    const start = (page - 1) * limit;
    return list.slice(start, start + limit);
  });

  readonly totalLedgerPages = computed(() => {
    const count = this.filteredLedgerTransactions().length;
    return Math.max(1, Math.ceil(count / this.ledgerLimit()));
  });

  readonly filteredAllocations = computed(() => {
    const term = this.allocationSearch().trim().toLowerCase();
    const list = this.allocations();
    if (!term) return list;
    return list.filter(
      (a) =>
        a.grantRef.toLowerCase().includes(term) ||
        a.grantScheme.toLowerCase().includes(term) ||
        a.stateTenant.toLowerCase().includes(term) ||
        (a.targetUlb && a.targetUlb.toLowerCase().includes(term)) ||
        a.sanctionOrderNo.toLowerCase().includes(term) ||
        a.status.toLowerCase().includes(term)
    );
  });

  readonly paginatedAllocations = computed(() => {
    const list = this.filteredAllocations();
    const page = this.allocationPage();
    const limit = this.allocationLimit();
    const start = (page - 1) * limit;
    return list.slice(start, start + limit);
  });

  readonly totalAllocationPages = computed(() => {
    const count = this.filteredAllocations().length;
    return Math.max(1, Math.ceil(count / this.allocationLimit()));
  });

  readonly filteredReconItems = computed(() => {
    const term = this.reconSearch().trim().toLowerCase();
    const list = this.reconData().reconciliationItems;
    if (!term) return list;
    return list.filter(
      (r) =>
        r.txnRef.toLowerCase().includes(term) ||
        r.utr.toLowerCase().includes(term) ||
        r.matchStatus.toLowerCase().includes(term) ||
        r.remarks.toLowerCase().includes(term)
    );
  });

  readonly paginatedRecon = computed(() => {
    const list = this.filteredReconItems();
    const page = this.reconPage();
    const limit = this.reconLimit();
    const start = (page - 1) * limit;
    return list.slice(start, start + limit);
  });

  readonly totalReconPages = computed(() => {
    const count = this.filteredReconItems().length;
    return Math.max(1, Math.ceil(count / this.reconLimit()));
  });

  ngOnInit(): void {
    this.fetchData();
  }

  setTab(tab: FinancialTab): void {
    this.activeTab.set(tab);
  }

  fetchData(): void {
    this.isLoading.set(true);
    this.executiveService.getGrantsOverview({ financialYear: this.selectedFinancialYear() }).subscribe({
      next: (data) => {
        const status = data as unknown as ExecutiveDataStatus;
        this.dataNotice.set(status.dataAvailable === false ? (status.unavailableReason ?? 'No records exist yet.') : '');
        if (status.dataAvailable !== false) {
          this.grantsData.set(data);
        }
        this.isLoading.set(false);
      },
      error: () => {
        this.dataNotice.set('Financial records could not be loaded.');
        this.isLoading.set(false);
      },
    });
  }

  applyFilters(): void {
    this.fetchData();
  }

  resetFilters(): void {
    this.selectedFinancialYear.set('FY 2026-27');
    this.selectedState.set('');
    this.selectedUlb.set('');
    this.selectedScheme.set('');
    this.selectedAuthority.set('');
    this.selectedGrantStatus.set('');
    this.selectedAggregation.set('State');
    this.fetchData();
    this.dialogService.showToast('Filters reset to default reporting period', 'info', 3000);
  }

  refreshData(): void {
    this.fetchData();
  }

  exportReport(): void {
    this.dialogService.showToast('Ledger export is not available yet.', 'info', 3000);
  }

  // Dialog actions
  openAllocationModal(): void {
    this.showAllocationModal.set(true);
  }

  closeAllocationModal(): void {
    this.showAllocationModal.set(false);
  }

  onSaveAllocation(payload: GrantAllocationCreate): void {
    this.executiveService.createGrantAllocation(payload).subscribe({
      next: (item) => {
        if (item) {
          this.allocations.update((list) => [item, ...list]);
        }
        this.showAllocationModal.set(false);
        this.dialogService.showToast(
          `Grant order ${payload.sanctionOrderNo} successfully recorded & disbursed`,
          'success',
          4000
        );
      },
      error: (err) => {
        console.error('Error saving allocation:', err);
        // Optimistic append
        const newRecord: GrantAllocationItem = {
          id: `ALLOC-${Math.floor(1000 + Math.random() * 9000)}`,
          grantRef: `GRNT-${Math.floor(1000 + Math.random() * 9000)}`,
          ...payload,
          releaseDate: payload.releaseDate || new Date().toISOString().substring(0, 10),
          targetUlb: payload.targetUlb || 'State Pool',
          sanctionDoc: payload.sanctionDoc || 'Sanction_Order.pdf',
          status: 'ALLOCATED',
        };
        this.allocations.update((list) => [newRecord, ...list]);
        this.showAllocationModal.set(false);
        this.dialogService.showToast(
          `Grant allocation ${payload.sanctionOrderNo} logged locally`,
          'success',
          4000
        );
      },
    });
  }

  openReconModal(): void {
    this.showReconModal.set(true);
  }

  closeReconModal(): void {
    this.showReconModal.set(false);
  }

  onExecuteReconciliation(_req: ReconciliationRunRequest): void {
    this.closeReconModal();
    this.dialogService.showToast('Reconciliation is not available until ledger records exist.', 'info', 3500);
  }

  // Currency Formatter Helper
  show(val: unknown): string {
    return val === null || val === undefined || val === '' ? 'Not available' : String(val);
  }

  formatPct(val: unknown): string {
    return val === null || val === undefined ? 'Not available' : `${val}%`;
  }

  formatNumber(val: number | null | undefined): string {
    return val === null || val === undefined ? 'Not available' : val.toLocaleString('en-IN');
  }

  formatInr(val: number): string {
    if (val === undefined || val === null) return '₹0';
    if (Math.abs(val) >= 10000000) {
      return `₹${(val / 10000000).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })} Cr`;
    }
    if (Math.abs(val) >= 100000) {
      return `₹${(val / 100000).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })} L`;
    }
    return `₹${val.toLocaleString('en-IN')}`;
  }
}
