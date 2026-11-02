import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CheckListComponent } from '../../../../../../shared/components/check-list/check-list.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../../../core/models/white-label.model';
import { AlertRule, QuotaOptions, RecipientOption } from '../../../../../../core/models/quota.model';

@Component({
  selector: 'app-alert-rule-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, CheckListComponent],
  templateUrl: './alert-rule-dialog.component.html',
  styleUrl: './alert-rule-dialog.component.scss',
})
export class AlertRuleDialogComponent implements OnInit {
  @Input() record: AlertRule | null = null;
  @Input({ required: true }) options!: QuotaOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Input({ required: true }) recipients!: RecipientOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(QuotaService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);

  form: AlertRule = {
    tenantLevel: 'State', stateTenantId: '', ulbTenantId: null, alertName: '', alertCode: '', resourceType: '', alertCondition: 'Usage Percentage', thresholdPercentage: null,
    thresholdValue: null, comparisonOperator: '>=', alertSeverity: '', notificationChannels: [], notificationRecipients: [], repeatIntervalMinutes: null, isActive: true, description: null,
  };

  get states(): TenantOption[] {
    return this.tenants.filter((t) => t.tenantLevel === 'State');
  }

  get ulbs(): TenantOption[] {
    return this.tenants.filter((t) => t.tenantLevel === 'ULB' && (!this.form.stateTenantId || t.stateTenantId === this.form.stateTenantId));
  }

  asOptions(values: string[]): { value: string; label: string }[] {
    return values.map((value) => ({ value, label: value }));
  }

  dateOnly(value: string | null | undefined): string {
    return value ? value.slice(0, 10) : '';
  }

  get recipientOptions(): { value: string; label: string }[] {
    return this.recipients.map((r) => ({ value: r.id, label: `${r.fullName} (${r.tenantId})` }));
  }

  ngOnInit(): void {
    if (this.record) this.form = { ...this.form, ...this.record };
  }

  private payload(): AlertRule {
    const f = this.form;
    return {
      tenantLevel: f.tenantLevel, stateTenantId: f.stateTenantId, ulbTenantId: f.ulbTenantId || null, alertName: f.alertName, alertCode: f.alertCode, resourceType: f.resourceType,
      alertCondition: f.alertCondition, thresholdPercentage: f.thresholdPercentage, thresholdValue: f.thresholdValue, comparisonOperator: f.comparisonOperator, alertSeverity: f.alertSeverity,
      notificationChannels: f.notificationChannels, notificationRecipients: f.notificationRecipients, repeatIntervalMinutes: f.repeatIntervalMinutes || null, isActive: f.isActive, description: f.description,
    };
  }

  submit(): void {
    const f = this.form;
    if (!f.stateTenantId || !f.alertName.trim() || !f.alertCode.trim() || !f.resourceType || !f.alertSeverity || !f.notificationChannels.length || !f.notificationRecipients.length) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if ('tenantLevel' in f && f.tenantLevel === 'ULB' && !f.ulbTenantId) {
      this.dialogs.showToast('Please select the ULB / City.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service.saveRule(this.payload(), this.record?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Alert rule saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this.'), 'error', 5000);
      },
    });
  }
}
