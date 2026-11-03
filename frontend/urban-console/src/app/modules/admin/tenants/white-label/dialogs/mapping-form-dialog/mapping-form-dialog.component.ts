import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { DomainMapping, TenantDomain, TenantOption, WhiteLabelOptions, apiError } from '../../../../../../core/models/white-label.model';

@Component({
  selector: 'app-mapping-form-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './mapping-form-dialog.component.html',
  styleUrl: './mapping-form-dialog.component.scss',
})
export class MappingFormDialogComponent implements OnInit {
  @Input() mapping: DomainMapping | null = null;
  @Input({ required: true }) options!: WhiteLabelOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(WhiteLabelService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  readonly domains = signal<TenantDomain[]>([]);

  form: DomainMapping = {
    mappingName: '', tenantId: '', domainId: '', targetApplication: '', targetService: '', targetRoute: null, routingStrategy: '',
    sslRequired: true, forceHttps: true, isPrimary: false, mappingStatus: 'Draft', effectiveFrom: null,
  };

  ngOnInit(): void {
    if (this.mapping) {
      this.form = { ...this.mapping, effectiveFrom: this.mapping.effectiveFrom?.slice(0, 10) ?? null };
      this.loadDomains();
    }
  }

  onTenantChange(): void {
    this.form.domainId = '';
    this.loadDomains();
  }

  private loadDomains(): void {
    if (!this.form.tenantId) {
      this.domains.set([]);
      return;
    }
    this.service.listDomains({ tenantId: this.form.tenantId, skip: 0, limit: 100 }).subscribe({
      next: (res) => this.domains.set(res.data),
      error: () => this.domains.set([]),
    });
  }

  submit(): void {
    const f = this.form;
    if (!f.mappingName.trim() || !f.tenantId || !f.domainId || !f.targetApplication || !f.targetService || !f.routingStrategy) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    const payload: DomainMapping = { ...f, effectiveFrom: f.effectiveFrom ? `${f.effectiveFrom}T00:00:00` : null, targetRoute: f.targetRoute?.trim() || null };
    delete payload.id;
    delete payload.domainName;
    this.isSaving.set(true);
    this.service.saveMapping(payload, this.mapping?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Mapping saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this mapping.'), 'error', 5000);
      },
    });
  }
}
