import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CheckListComponent } from '../../../../../../shared/components/check-list/check-list.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../../../core/models/white-label.model';
import { ApiPolicy, QuotaOptions } from '../../../../../../core/models/quota.model';

@Component({
  selector: 'app-api-policy-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, CheckListComponent],
  templateUrl: './api-policy-dialog.component.html',
  styleUrl: './api-policy-dialog.component.scss',
})
export class ApiPolicyDialogComponent implements OnInit {
  @Input() record: ApiPolicy | null = null;
  @Input({ required: true }) options!: QuotaOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(QuotaService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);

  form: ApiPolicy = {
    tenantLevel: 'State', stateTenantId: '', ulbTenantId: null, apiGateway: '', apiServices: [], apiCategory: null, rateLimitPerMinute: null, rateLimitPerHour: null,
    rateLimitPerDay: null, burstLimit: null, concurrentLimit: null, quotaPeriod: '', effectiveFrom: '', effectiveUntil: null, policyStatus: 'Draft',
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

  ngOnInit(): void {
    if (this.record) this.form = { ...this.form, ...this.record };
  }

  private payload(): ApiPolicy {
    const f = this.form;
    return {
      tenantLevel: f.tenantLevel, stateTenantId: f.stateTenantId, ulbTenantId: f.ulbTenantId || null, apiGateway: f.apiGateway, apiServices: f.apiServices, apiCategory: f.apiCategory,
      rateLimitPerMinute: f.rateLimitPerMinute, rateLimitPerHour: f.rateLimitPerHour || null, rateLimitPerDay: f.rateLimitPerDay || null, burstLimit: f.burstLimit || null,
      concurrentLimit: f.concurrentLimit || null, quotaPeriod: f.quotaPeriod, effectiveFrom: `${this.dateOnly(f.effectiveFrom)}T00:00:00`,
      effectiveUntil: f.effectiveUntil ? `${this.dateOnly(f.effectiveUntil)}T23:59:59` : null, policyStatus: f.policyStatus,
    };
  }

  submit(): void {
    const f = this.form;
    if (!f.stateTenantId || !f.apiGateway || !f.rateLimitPerMinute || !f.quotaPeriod || !f.effectiveFrom) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if ('tenantLevel' in f && f.tenantLevel === 'ULB' && !f.ulbTenantId) {
      this.dialogs.showToast('Please select the ULB / City.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service.savePolicy(this.payload(), this.record?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('API policy saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this.'), 'error', 5000);
      },
    });
  }
}
