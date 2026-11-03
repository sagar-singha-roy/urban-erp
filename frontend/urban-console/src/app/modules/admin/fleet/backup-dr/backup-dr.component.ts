import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { BackupDrService } from '../../../../core/services/backup-dr.service';
import { DialogService } from '../../../../core/services/dialog.service';
import {
  BackupDrOverviewStats,
  BackupPolicyItem,
  BackupPolicyPayload,
  BackupJobItem,
  RestoreJobItem,
  RestoreJobPayload,
  PitrWindowStatus,
  DrillExecutionItem,
  DrillExecutionPayload,
} from '../../../../core/models/backup-dr.model';
import { PolicyDialogComponent } from './dialogs/policy-dialog/policy-dialog.component';
import { DataNoticeComponent } from '../../../../shared/components/data-notice/data-notice.component';
import { RestoreDialogComponent } from './dialogs/restore-dialog/restore-dialog.component';
import { DrillDialogComponent } from './dialogs/drill-dialog/drill-dialog.component';

@Component({
  selector: 'app-backup-dr',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent, RefreshButtonComponent,
    PolicyDialogComponent,
    RestoreDialogComponent,
    DataNoticeComponent,
    DrillDialogComponent,
  ],
  templateUrl: './backup-dr.component.html',
  styleUrl: './backup-dr.component.scss',
})
export class BackupDrComponent implements OnInit {
  private backupService = inject(BackupDrService);
  private dialogs = inject(DialogService);

  readonly activeTab = signal<'policies' | 'history' | 'restore' | 'pitr' | 'drills'>('policies');

  // Core Data
  readonly stats = signal<BackupDrOverviewStats | null>(null);
  readonly allPolicies = signal<BackupPolicyItem[]>([]);
  readonly allJobs = signal<BackupJobItem[]>([]);
  readonly allRestores = signal<RestoreJobItem[]>([]);
  readonly pitrStatus = signal<PitrWindowStatus | null>(null);
  readonly allDrills = signal<DrillExecutionItem[]>([]);
  readonly isLoading = signal<boolean>(false);

  // Dialog State
  readonly activeDialog = signal<'policy' | 'restore' | 'drill' | null>(null);

  // Filters: History
  jobSearch: string = '';
  selectedPolicyFilter: string = 'ALL';
  selectedEnvFilter: string = 'ALL';
  selectedDbFilter: string = 'ALL';
  selectedTypeFilter: string = 'ALL';
  selectedStatusFilter: string = 'ALL';

  // Filters: Policies
  policyStatusFilter: string = 'ALL';


  // Pagination for Jobs
  readonly currentPage = signal<number>(1);
  pageSize: number = 20;

  // Filtered Jobs Computation
  readonly filteredJobs = computed(() => {
    let list = this.allJobs();

    if (this.selectedPolicyFilter !== 'ALL') {
      list = list.filter((j) => j.policyCode === this.selectedPolicyFilter);
    }
    if (this.selectedEnvFilter !== 'ALL') {
      list = list.filter((j) => j.environment === this.selectedEnvFilter);
    }
    if (this.selectedDbFilter !== 'ALL') {
      list = list.filter((j) => j.databaseName === this.selectedDbFilter);
    }
    if (this.selectedTypeFilter !== 'ALL') {
      list = list.filter((j) => j.backupType === this.selectedTypeFilter);
    }
    if (this.selectedStatusFilter !== 'ALL') {
      list = list.filter((j) => j.executionStatus === this.selectedStatusFilter);
    }
    if (this.jobSearch && this.jobSearch.trim()) {
      const q = this.jobSearch.trim().toLowerCase();
      list = list.filter(
        (j) =>
          j.jobId.toLowerCase().includes(q) ||
          j.policyName.toLowerCase().includes(q) ||
          j.storageLocation.toLowerCase().includes(q)
      );
    }

    return list;
  });

  readonly totalPages = computed(() => {
    const total = this.filteredJobs().length;
    return total > 0 ? Math.ceil(total / this.pageSize) : 1;
  });

  readonly paginatedJobs = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.filteredJobs().slice(start, start + this.pageSize);
  });

  readonly paginationStart = computed(() => {
    return this.filteredJobs().length === 0 ? 0 : (this.currentPage() - 1) * this.pageSize + 1;
  });

  readonly paginationEnd = computed(() => {
    const end = this.currentPage() * this.pageSize;
    return Math.min(end, this.filteredJobs().length);
  });

  ngOnInit(): void {
    this.refreshAll();
  }

  refreshAll(): void {
    this.isLoading.set(true);
    this.loadStats();
    this.loadPolicies();
    this.loadJobs();
    this.loadRestores();
    this.loadPitrStatus();
    this.loadDrills();
    setTimeout(() => this.isLoading.set(false), 350);
  }

  loadStats(): void {
    this.backupService.getStats().subscribe({
      next: (s) => this.stats.set(s),
      error: () => this.stats.set(null),
    });
  }

  loadPolicies(): void {
    this.backupService.getPolicies().subscribe({
      next: (p) => this.allPolicies.set(p || []),
      error: () => this.allPolicies.set([]),
    });
  }

  loadJobs(): void {
    this.backupService.getJobs().subscribe({
      next: (j) => this.allJobs.set(j || []),
      error: () => this.allJobs.set([]),
    });
  }

  loadRestores(): void {
    this.backupService.getRestores().subscribe({
      next: (r) => this.allRestores.set(r || []),
      error: () => this.allRestores.set([]),
    });
  }

  loadPitrStatus(): void {
    this.backupService.getPitrStatus().subscribe({
      next: (ps) => this.pitrStatus.set(ps),
      error: () => this.pitrStatus.set(null),
    });
  }

  loadDrills(): void {
    this.backupService.getDrills().subscribe({
      next: (d) => this.allDrills.set(d || []),
      error: () => this.allDrills.set([]),
    });
  }

  setActiveTab(tab: 'policies' | 'history' | 'restore' | 'pitr' | 'drills'): void {
    this.activeTab.set(tab);
    this.currentPage.set(1);
  }

  goToPage(p: number): void {
    if (p >= 1 && p <= this.totalPages()) {
      this.currentPage.set(p);
    }
  }

  onPageSizeChange(): void {
    this.currentPage.set(1);
  }

  clearSearch(): void {
    this.jobSearch = '';
    this.currentPage.set(1);
  }

  // Dialog triggers
  openPolicyDialog(): void {
    this.activeDialog.set('policy');
  }

  runDrill(drill: { id: string }): void {
    this.backupService.runDrill(drill.id).subscribe({
      next: () => {
        this.dialogs.showToast('Drill started. Use Refresh to see its result.', 'success');
        this.loadDrills();
      },
      error: (err) => this.dialogs.showToast(err?.error?.detail || 'The drill could not be started.', 'error'),
    });
  }

  async approveRestore(restore: RestoreJobItem): Promise<void> {
    const confirmed = await this.dialogs.confirm({
      title: 'Approve restore',
      message: `Restore '${restore.sourceBackupId}' into a new scratch database? Existing databases are not changed.`,
      confirmText: 'Approve and Run',
      cancelText: 'Cancel',
      variant: 'primary',
    });
    if (!confirmed) return;
    this.backupService.approveRestore(restore.id).subscribe({
      next: () => {
        this.dialogs.showToast('Restore started. Use Refresh to see its result.', 'success');
        this.loadRestores();
      },
      error: (err) => this.dialogs.showToast(err?.error?.detail || 'The restore could not be approved.', 'error'),
    });
  }

  openRestoreDialog(): void {
    this.activeDialog.set('restore');
  }

  openDrillDialog(): void {
    this.activeDialog.set('drill');
  }

  closeDialog(): void {
    this.activeDialog.set(null);
  }

  onPolicyCreated(payload: BackupPolicyPayload): void {
    this.backupService.createPolicy(payload).subscribe({
      next: (pol) => {
        this.closeDialog();
        this.dialogs.showToast(`Backup policy '${pol.policyCode}' created successfully.`, 'success');
        this.refreshAll();
      },
      error: (err) => {
        const msg = err?.error?.detail || err?.message || 'Failed to create policy';
        this.dialogs.showToast(msg, 'error');
      },
    });
  }

  triggerBackup(policy: BackupPolicyItem): void {
    this.dialogs.showToast(`Initiating on-demand backup for policy '${policy.policyCode}'...`, 'info');
    this.backupService.triggerOnDemandBackup(policy.policyCode).subscribe({
      next: (job) => {
        this.dialogs.showToast(`Backup '${job.jobId}' started. Use Refresh to see its result.`, 'info');
        this.refreshAll();
      },
      error: (err) => {
        const msg = err?.error?.detail || err?.message || 'Backup execution failed';
        this.dialogs.showToast(msg, 'error');
      },
    });
  }

  onRestoreInitiated(payload: RestoreJobPayload): void {
    this.backupService.initiateRestore(payload).subscribe({
      next: (job) => {
        this.closeDialog();
        this.dialogs.showToast(`Restore request '${job.restoreJobName}' recorded. A second administrator must approve it.`, 'info');
        this.refreshAll();
      },
      error: (err) => {
        const msg = err?.error?.detail || err?.message || 'Restore execution failed';
        this.dialogs.showToast(msg, 'error');
      },
    });
  }

  onDrillScheduled(payload: DrillExecutionPayload): void {
    this.backupService.scheduleDrill(payload).subscribe({
      next: (drill) => {
        this.closeDialog();
        this.dialogs.showToast(`DR Drill '${drill.drillCode}' scheduled successfully.`, 'success');
        this.refreshAll();
      },
      error: (err) => {
        const msg = err?.error?.detail || err?.message || 'Failed to schedule drill';
        this.dialogs.showToast(msg, 'error');
      },
    });
  }
}

