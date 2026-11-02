import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { BrandingProfile, TenantOption, WhiteLabelOptions, apiError } from '../../../../../../core/models/white-label.model';

@Component({
  selector: 'app-branding-form-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './branding-form-dialog.component.html',
  styleUrl: './branding-form-dialog.component.scss',
})
export class BrandingFormDialogComponent implements OnInit {
  @Input() profile: BrandingProfile | null = null;
  @Input({ required: true }) options!: WhiteLabelOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(WhiteLabelService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);

  form: BrandingProfile = {
    tenantLevel: 'State', stateTenantId: '', ulbTenantId: null, profileName: '', displayName: '', tagline: null,
    primaryColour: '', secondaryColour: '', accentColour: null, headerBackgroundColour: null, sidebarBackgroundColour: null,
    fontFamily: null, loginPageTitle: null, loginPageMessage: null, footerText: null, customCss: null, brandingStatus: 'Draft',
  };

  get states(): TenantOption[] {
    return this.tenants.filter((t) => t.tenantLevel === 'State');
  }

  get ulbs(): TenantOption[] {
    return this.tenants.filter((t) => t.tenantLevel === 'ULB' && (!this.form.stateTenantId || t.stateTenantId === this.form.stateTenantId));
  }

  ngOnInit(): void {
    if (this.profile) this.form = { ...this.form, ...this.profile };
  }

  submit(): void {
    const f = this.form;
    if (!f.stateTenantId || !f.profileName.trim() || !f.displayName.trim() || !f.primaryColour || !f.secondaryColour) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if (f.tenantLevel === 'ULB' && !f.ulbTenantId) {
      this.dialogs.showToast('Please select the ULB / City.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service.saveBranding(f, this.profile?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Branding profile saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this profile.'), 'error', 5000);
      },
    });
  }
}
