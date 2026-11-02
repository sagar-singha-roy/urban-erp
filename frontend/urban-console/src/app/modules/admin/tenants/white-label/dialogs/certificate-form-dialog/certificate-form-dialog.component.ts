import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantCertificate, TenantDomain, TenantOption, WhiteLabelOptions, apiError } from '../../../../../../core/models/white-label.model';

const MANUAL_UPLOAD = 'Manual Upload';

@Component({
  selector: 'app-certificate-form-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './certificate-form-dialog.component.html',
  styleUrl: './certificate-form-dialog.component.scss',
})
export class CertificateFormDialogComponent implements OnInit {
  @Input() certificate: TenantCertificate | null = null;
  @Input({ required: true }) options!: WhiteLabelOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(WhiteLabelService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  readonly domains = signal<TenantDomain[]>([]);

  form = { tenantId: '', domainId: '', provider: '', certificateType: '', privateKey: '', autoRenewal: true, renewalNotificationDays: 30 };
  private files: Record<string, File> = {};

  get isManual(): boolean {
    return this.form.provider === MANUAL_UPLOAD;
  }

  ngOnInit(): void {
    if (this.certificate) {
      this.form.autoRenewal = this.certificate.autoRenewal;
      this.form.renewalNotificationDays = this.certificate.renewalNotificationDays;
    }
  }

  onTenantChange(): void {
    this.form.domainId = '';
    if (!this.form.tenantId) {
      this.domains.set([]);
      return;
    }
    this.service.listDomains({ tenantId: this.form.tenantId, skip: 0, limit: 100 }).subscribe({
      next: (res) => this.domains.set(res.data.filter((d) => d.verificationStatus === 'Verified')),
      error: () => this.domains.set([]),
    });
  }

  onFile(field: string, event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) this.files[field] = file;
    else delete this.files[field];
  }

  submit(): void {
    const f = this.form;
    if (this.certificate) {
      this.send(this.service.updateCertificate(this.certificate.id, { autoRenewal: f.autoRenewal, renewalNotificationDays: f.renewalNotificationDays }));
      return;
    }
    if (!f.domainId || !f.provider || !f.certificateType) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if (this.isManual && (!this.files['certificate'] || !f.privateKey.trim())) {
      this.dialogs.showToast('A manual upload needs the certificate and its private key.', 'warning');
      return;
    }
    const data = new FormData();
    data.append('domainId', f.domainId);
    data.append('provider', f.provider);
    data.append('certificateType', f.certificateType);
    data.append('autoRenewal', String(!this.isManual && f.autoRenewal));
    data.append('renewalNotificationDays', String(f.renewalNotificationDays));
    if (this.isManual) {
      data.append('privateKey', f.privateKey);
      for (const [field, file] of Object.entries(this.files)) data.append(field, file);
    }
    this.send(this.service.createCertificate(data));
  }

  private send(request: ReturnType<WhiteLabelService['createCertificate']>): void {
    this.isSaving.set(true);
    // The key leaves browser memory as soon as it has been sent, whatever the outcome.
    this.form.privateKey = '';
    request.subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Certificate saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this certificate.'), 'error', 5000);
      },
    });
  }
}
