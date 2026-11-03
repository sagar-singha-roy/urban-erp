import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { AssetSet, TenantOption, WhiteLabelOptions, apiError } from '../../../../../../core/models/white-label.model';

const MAX_FILE_BYTES = 2 * 1024 * 1024;

@Component({
  selector: 'app-asset-form-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './asset-form-dialog.component.html',
  styleUrl: './asset-form-dialog.component.scss',
})
export class AssetFormDialogComponent implements OnInit {
  @Input() assets: AssetSet | null = null;
  @Input({ required: true }) options!: WhiteLabelOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(WhiteLabelService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);

  form = { tenantId: '', logoType: '', altText: '', effectiveFrom: '', assetStatus: 'Draft' };
  private files: Record<string, File> = {};

  ngOnInit(): void {
    if (this.assets) {
      this.form = {
        tenantId: this.assets.tenantId,
        logoType: this.assets.logoType,
        altText: this.assets.altText,
        effectiveFrom: this.assets.effectiveFrom?.slice(0, 10) ?? '',
        assetStatus: this.assets.assetStatus,
      };
    }
  }

  onFile(field: string, event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file && file.size > MAX_FILE_BYTES) {
      this.dialogs.showToast('Each file must be 2 MB or smaller.', 'warning');
      input.value = '';
      return;
    }
    if (file) this.files[field] = file;
    else delete this.files[field];
  }

  submit(): void {
    const f = this.form;
    const effectiveFrom = f.effectiveFrom ? `${f.effectiveFrom}T00:00:00` : null;
    if (!f.altText.trim()) {
      this.dialogs.showToast('Alt text is required.', 'warning');
      return;
    }
    if (this.assets) {
      this.finish(this.service.updateAssets(this.assets.id, { altText: f.altText, effectiveFrom, assetStatus: f.assetStatus }));
      return;
    }
    if (!f.tenantId || !f.logoType || !this.files['logo']) {
      this.dialogs.showToast('Tenant, logo type and logo file are required.', 'warning');
      return;
    }
    if (f.logoType === 'Official Emblem' && !this.files['emblem']) {
      this.dialogs.showToast('An emblem file is required for an Official Emblem.', 'warning');
      return;
    }
    const data = new FormData();
    data.append('tenantId', f.tenantId);
    data.append('logoType', f.logoType);
    data.append('altText', f.altText);
    data.append('assetStatus', f.assetStatus);
    if (effectiveFrom) data.append('effectiveFrom', effectiveFrom);
    for (const [field, file] of Object.entries(this.files)) data.append(field, file);
    this.finish(this.service.uploadAssets(data));
  }

  private finish(request: ReturnType<WhiteLabelService['uploadAssets']>): void {
    this.isSaving.set(true);
    request.subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Assets saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save these assets.'), 'error', 5000);
      },
    });
  }
}
