import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CheckListComponent } from '../../../../../../shared/components/check-list/check-list.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../../../core/models/white-label.model';
import { ModuleAllocation, QuotaOptions, StorageAllocation } from '../../../../../../core/models/quota.model';

@Component({
  selector: 'app-storage-allocation-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, CheckListComponent],
  templateUrl: './storage-allocation-dialog.component.html',
  styleUrl: './storage-allocation-dialog.component.scss',
})
export class StorageAllocationDialogComponent implements OnInit {
  @Input() record: StorageAllocation | null = null;
  @Input({ required: true }) options!: QuotaOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(QuotaService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);

  form: StorageAllocation = {
    tenantLevel: 'State', stateTenantId: '', ulbTenantId: null, allocationName: '', storageType: '', storageProvider: '', storageBucket: '',
    allocationAmount: null, storageUnit: 'GB', maxFileSizeMb: null, allowedFileTypes: [], moduleAllocations: [], effectiveFrom: '', effectiveUntil: null,
    allocationStatus: 'Draft', remarks: null,
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

  /** Rows are edited in GB and stored in bytes. */
  moduleRows: { moduleCode: string; gb: number | null }[] = [];

  ngOnInit(): void {
    if (this.record) {
      this.form = { ...this.form, ...this.record };
      this.moduleRows = (this.record.moduleAllocations ?? []).map((m: ModuleAllocation) => ({ moduleCode: m.moduleCode, gb: +(m.allocationBytes / 1024 ** 3).toFixed(3) }));
    }
  }

  addModule(): void {
    this.moduleRows = [...this.moduleRows, { moduleCode: '', gb: null }];
  }

  removeModule(index: number): void {
    this.moduleRows = this.moduleRows.filter((_, i) => i !== index);
  }

  private payload(): StorageAllocation {
    const { id, tenantId, ...rest } = this.form;
    return {
      ...rest,
      effectiveFrom: `${this.dateOnly(rest.effectiveFrom)}T00:00:00`,
      effectiveUntil: rest.effectiveUntil ? `${this.dateOnly(rest.effectiveUntil)}T23:59:59` : null,
      moduleAllocations: this.moduleRows.filter((m) => m.moduleCode && m.gb).map((m) => ({ moduleCode: m.moduleCode, allocationBytes: Math.round((m.gb as number) * 1024 ** 3) })),
    };
  }

  submit(): void {
    const f = this.form;
    if (!f.stateTenantId || !f.allocationName.trim() || !f.storageType || !f.storageProvider || !f.storageBucket.trim() || !f.allocationAmount || !f.maxFileSizeMb || !f.allowedFileTypes.length || !f.effectiveFrom) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if ('tenantLevel' in f && f.tenantLevel === 'ULB' && !f.ulbTenantId) {
      this.dialogs.showToast('Please select the ULB / City.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service.saveStorage(this.payload(), this.record?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Storage allocation saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this.'), 'error', 5000);
      },
    });
  }
}
