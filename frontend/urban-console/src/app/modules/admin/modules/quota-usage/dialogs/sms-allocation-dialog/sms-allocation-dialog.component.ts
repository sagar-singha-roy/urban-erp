import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CheckListComponent } from '../../../../../../shared/components/check-list/check-list.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../../../core/models/white-label.model';
import { QuotaOptions, RecipientOption, SmsAllocation } from '../../../../../../core/models/quota.model';

@Component({
  selector: 'app-sms-allocation-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, CheckListComponent],
  templateUrl: './sms-allocation-dialog.component.html',
  styleUrl: './sms-allocation-dialog.component.scss',
})
export class SmsAllocationDialogComponent implements OnInit {
  @Input() record: SmsAllocation | null = null;
  @Input({ required: true }) options!: QuotaOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Input({ required: true }) recipients!: RecipientOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(QuotaService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);

  form: SmsAllocation = {
    stateTenantId: '', ulbTenantId: null, allocationName: '', smsProvider: '', dltEntityId: null, senderId: null, dltTemplateId: null,
    creditAllocation: null, validFrom: '', validUntil: '', smsCategories: [], lowCreditThreshold: null, notificationRecipients: [], allocationStatus: 'Draft',
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

  private payload(): SmsAllocation {
    const f = this.form;
    return {
      stateTenantId: f.stateTenantId, ulbTenantId: f.ulbTenantId || null, allocationName: f.allocationName, smsProvider: f.smsProvider, dltEntityId: f.dltEntityId || null,
      senderId: f.senderId || null, dltTemplateId: f.dltTemplateId || null, creditAllocation: f.creditAllocation, validFrom: `${this.dateOnly(f.validFrom)}T00:00:00`,
      validUntil: `${this.dateOnly(f.validUntil)}T23:59:59`, smsCategories: f.smsCategories, lowCreditThreshold: f.lowCreditThreshold, notificationRecipients: f.notificationRecipients, allocationStatus: f.allocationStatus,
    };
  }

  submit(): void {
    const f = this.form;
    if (!f.stateTenantId || !f.allocationName.trim() || !f.smsProvider || !f.creditAllocation || !f.validFrom || !f.validUntil) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if ('tenantLevel' in f && f.tenantLevel === 'ULB' && !f.ulbTenantId) {
      this.dialogs.showToast('Please select the ULB / City.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service.saveSms(this.payload(), this.record?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('SMS allocation saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this.'), 'error', 5000);
      },
    });
  }
}
