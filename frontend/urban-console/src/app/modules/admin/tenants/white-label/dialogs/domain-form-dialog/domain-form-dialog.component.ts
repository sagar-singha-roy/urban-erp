import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantDomain, TenantOption, WhiteLabelOptions, apiError } from '../../../../../../core/models/white-label.model';

@Component({
  selector: 'app-domain-form-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './domain-form-dialog.component.html',
  styleUrl: './domain-form-dialog.component.scss',
})
export class DomainFormDialogComponent implements OnInit {
  @Input() domain: TenantDomain | null = null;
  @Input({ required: true }) options!: WhiteLabelOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(WhiteLabelService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);

  form = {
    tenantId: '', domainName: '', domainType: '', subdomain: null as string | null, rootDomain: null as string | null,
    dnsProvider: null as string | null, dnsRecordType: '', dnsHost: '', dnsTarget: '', verificationMethod: '', isPrimary: false, domainStatus: 'Pending',
  };

  ngOnInit(): void {
    if (this.domain) this.form = { ...this.form, ...this.domain };
  }

  submit(): void {
    const f = this.form;
    if (!f.tenantId || !f.domainName.trim() || !f.domainType || !f.dnsRecordType || !f.dnsHost.trim() || !f.dnsTarget.trim() || !f.verificationMethod) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if (f.domainType === 'Subdomain' && !f.rootDomain) {
      this.dialogs.showToast('Root domain is required for a subdomain.', 'warning');
      return;
    }
    this.isSaving.set(true);
    const request = this.domain
      ? this.service.updateDomain(this.domain.id, {
          dnsProvider: f.dnsProvider, dnsRecordType: f.dnsRecordType, dnsHost: f.dnsHost, dnsTarget: f.dnsTarget,
          verificationMethod: f.verificationMethod, isPrimary: f.isPrimary, domainStatus: f.domainStatus,
        })
      : this.service.createDomain({
          tenantId: f.tenantId, domainName: f.domainName, domainType: f.domainType, subdomain: f.subdomain, rootDomain: f.rootDomain,
          dnsProvider: f.dnsProvider, dnsRecordType: f.dnsRecordType, dnsHost: f.dnsHost, dnsTarget: f.dnsTarget,
          verificationMethod: f.verificationMethod, isPrimary: f.isPrimary,
        });
    request.subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast(this.domain ? 'Domain saved.' : 'Domain claimed. Publish the verification record, then verify.', 'success', 4000);
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this domain.'), 'error', 5000);
      },
    });
  }
}
