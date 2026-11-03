import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CheckListComponent } from '../../../../../../shared/components/check-list/check-list.component';
import { CrossTenantService } from '../../../../../../core/services/cross-tenant.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../../../core/models/white-label.model';
import {
  AccessGrant,
  CrossTenantOptions,
  GrantPayload,
  UserOption,
} from '../../../../../../core/models/cross-tenant.model';
import { UserPickerComponent } from '../../shared/user-picker.component';
import { asUtc, fromLocalInput, tenantOptions, toLocalInput } from '../../cross-tenant-utils';

/** Tab 1: request new cross-tenant access, or change a pending or active record. */
@Component({
  selector: 'app-xt-grant-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, CheckListComponent, UserPickerComponent],
  templateUrl: './grant-dialog.component.html',
  styleUrl: './grant-dialog.component.scss',
})
export class GrantDialogComponent implements OnInit {
  @Input() record: AccessGrant | null = null;
  @Input({ required: true }) options!: CrossTenantOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Input({ required: true }) authorities!: UserOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(CrossTenantService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  readonly asUtc = asUtc;

  userEmail = '';
  userName = '';
  effectiveFrom = '';
  effectiveUntil = '';
  form: GrantPayload = {
    userProfileId: '',
    userType: '',
    homeTenantId: '',
    targetTenantIds: [],
    accessLevel: '',
    effectiveFrom: '',
    effectiveUntil: null,
    businessJustification: '',
    approvalAuthorityId: '',
    approvalReference: null,
  };

  ngOnInit(): void {
    const r = this.record;
    if (r) {
      this.form = {
        userProfileId: r.userProfileId,
        userType: r.userType,
        homeTenantId: r.homeTenantId,
        targetTenantIds: [...r.targetTenantIds],
        accessLevel: r.accessLevel,
        effectiveFrom: r.effectiveFrom,
        effectiveUntil: r.effectiveUntil,
        businessJustification: r.businessJustification,
        approvalAuthorityId: r.approvalAuthorityId,
        approvalReference: r.approvalReference,
      };
      this.userEmail = r.userEmail;
      this.userName = r.userName;
    }
    this.effectiveFrom = toLocalInput(r?.effectiveFrom) || toLocalInput(new Date().toISOString());
    this.effectiveUntil = toLocalInput(r?.effectiveUntil);
  }

  get targetOptions(): { value: string; label: string }[] {
    return tenantOptions(this.tenants.filter((t) => t.tenantId !== this.form.homeTenantId));
  }

  get authorityOptions(): UserOption[] {
    return this.authorities.filter((a) => a.id !== this.form.userProfileId);
  }

  onUser(user: UserOption | null): void {
    this.form.userProfileId = user?.id ?? '';
    this.userEmail = user?.email ?? '';
    this.userName = user?.fullName ?? '';
    if (user?.userType) this.form.userType = user.userType;
    if (user?.homeTenantId) this.onHome(user.homeTenantId);
  }

  onHome(tenantId: string): void {
    this.form.homeTenantId = tenantId;
    this.form.targetTenantIds = this.form.targetTenantIds.filter((t) => t !== tenantId);
  }

  submit(): void {
    const f = this.form;
    if (
      !f.userProfileId ||
      !f.userType ||
      !f.homeTenantId ||
      !f.targetTenantIds.length ||
      !f.accessLevel ||
      !this.effectiveFrom ||
      !f.approvalAuthorityId
    ) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if (f.businessJustification.trim().length < 10) {
      this.dialogs.showToast('Explain the business need in at least 10 characters.', 'warning');
      return;
    }
    const payload: GrantPayload = {
      ...f,
      effectiveFrom: fromLocalInput(this.effectiveFrom)!,
      effectiveUntil: fromLocalInput(this.effectiveUntil),
      approvalReference: f.approvalReference?.trim() || null,
    };
    this.isSaving.set(true);
    this.service.saveGrant(payload, this.record?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Access saved and sent for approval.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this access.'), 'error', 5000);
      },
    });
  }
}
