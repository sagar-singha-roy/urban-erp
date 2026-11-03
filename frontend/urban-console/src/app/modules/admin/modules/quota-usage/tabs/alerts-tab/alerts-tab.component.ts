import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { PagedTab } from '../../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../../shared/components/wl-pagination/wl-pagination.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { PageQuery, PagedResponse, TenantOption, apiError } from '../../../../../../core/models/white-label.model';
import { AlertRule, QuotaOptions, AlertEvent, RecipientOption, ThresholdLevel } from '../../../../../../core/models/quota.model';
import { AlertRuleDialogComponent } from '../../dialogs/alert-rule-dialog/alert-rule-dialog.component';

@Component({
  selector: 'app-quota-alerts-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, AlertRuleDialogComponent],
  templateUrl: './alerts-tab.component.html',
  styleUrl: './alerts-tab.component.scss',
})
export class AlertsTabComponent extends PagedTab<AlertRule> {
  private service = inject(QuotaService);
  readonly options = input.required<QuotaOptions>();
  readonly tenants = input.required<TenantOption[]>();
  readonly recipients = input.required<RecipientOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<AlertRule | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<AlertRule>> {
    return this.service.listRules(query);
  }

  open(record: AlertRule | null): void {
    this.selected.set(record);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }

  readonly levels = signal<ThresholdLevel[]>([]);
  readonly events = signal<AlertEvent[]>([]);
  readonly eventTotal = signal(0);
  readonly eventPage = signal(1);
  readonly eventLimit = signal(10);
  private dialogsRef = inject(DialogService);

  override ngOnInit(): void {
    super.ngOnInit();
    this.loadLevels();
    this.loadEvents();
  }

  loadLevels(): void {
    this.service.getLevels().subscribe({ next: (res) => this.levels.set(res.data) });
  }

  loadEvents(): void {
    this.service.listEvents({ skip: (this.eventPage() - 1) * this.eventLimit(), limit: this.eventLimit() }).subscribe({
      next: (res) => {
        this.events.set(res.data);
        this.eventTotal.set(res.total);
      },
    });
  }

  saveLevel(level: ThresholdLevel, value: string): void {
    const percentage = Number(value);
    if (!(percentage > 0 && percentage <= 100)) {
      this.dialogsRef.showToast('Enter a percentage from 1 to 100.', 'warning');
      this.loadLevels();
      return;
    }
    this.service.updateLevel(level.id, percentage).subscribe({
      next: () => {
        this.dialogsRef.showToast(`${level.levelName} level saved.`, 'success');
        this.loadLevels();
      },
      error: (err) => this.dialogsRef.showToast(apiError(err, 'Could not save this level.'), 'error', 4000),
    });
  }

  acknowledge(event: AlertEvent): void {
    this.service.acknowledgeEvent(event.id).subscribe({
      next: () => this.loadEvents(),
      error: (err) => this.dialogsRef.showToast(apiError(err, 'Could not acknowledge this alert.'), 'error', 4000),
    });
  }
}
