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
  ComponentOption,
  CrossTenantOptions,
  PermissionRule,
  RulePayload,
} from '../../../../../../core/models/cross-tenant.model';
import { GrantPickerComponent } from '../../shared/grant-picker.component';
import { asOptions, asUtc, tenantName } from '../../cross-tenant-utils';

/** Tab 3: an Allow or Deny rule on modules, components and actions in one target tenant. */
@Component({
  selector: 'app-xt-permission-rule-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, CheckListComponent, GrantPickerComponent],
  templateUrl: './permission-rule-dialog.component.html',
  styleUrl: '../grant-dialog/grant-dialog.component.scss',
})
export class PermissionRuleDialogComponent implements OnInit {
  @Input() record: PermissionRule | null = null;
  @Input({ required: true }) options!: CrossTenantOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(CrossTenantService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  readonly asOptions = asOptions;
  readonly asUtc = asUtc;
  readonly grant = signal<AccessGrant | null>(null);
  readonly components = signal<ComponentOption[]>([]);

  form: RulePayload = {
    grantId: '',
    targetTenantId: '',
    moduleCodes: [],
    componentCodes: [],
    actionPermissions: [],
    dataAccessScope: '',
    accessDecision: 'Deny',
    restrictionReason: null,
  };

  readonly describeGrant = (g: AccessGrant): string =>
    g.targetTenantIds.map((t) => tenantName(this.tenants, t)).join(', ');

  ngOnInit(): void {
    const r = this.record;
    if (!r) return;
    this.form = {
      ...r,
      moduleCodes: [...r.moduleCodes],
      componentCodes: [...r.componentCodes],
      actionPermissions: [...r.actionPermissions],
    };
    this.service.getGrant(r.grantId).subscribe({ next: (res) => this.grant.set(res.data) });
    this.loadComponents();
  }

  onGrant(grant: AccessGrant | null): void {
    this.grant.set(grant);
    this.form.grantId = grant?.id ?? '';
    this.form.targetTenantId = grant?.targetTenantIds.length === 1 ? grant.targetTenantIds[0] : '';
  }

  /** The rule can name a target, or a ULB inside a target state. */
  get tenantChoices(): TenantOption[] {
    const targets = this.grant()?.targetTenantIds ?? [];
    return this.tenants.filter(
      (t) =>
        targets.includes(t.tenantId) ||
        (t.tenantLevel === 'ULB' && targets.includes(t.stateTenantId)),
    );
  }

  get moduleChoices(): { value: string; label: string }[] {
    return this.options.modules.map((m) => ({ value: m.code, label: `${m.code} ${m.name}` }));
  }

  get componentChoices(): { value: string; label: string }[] {
    return this.components().map((c) => ({ value: c.code, label: `${c.code} ${c.name}` }));
  }

  onModules(codes: string[]): void {
    this.form.moduleCodes = codes;
    this.form.componentCodes = this.form.componentCodes.filter((c) =>
      codes.includes(c.split('-')[0]),
    );
    this.loadComponents();
  }

  private loadComponents(): void {
    if (!this.form.moduleCodes.length) {
      this.components.set([]);
      return;
    }
    this.service
      .getComponents(this.form.moduleCodes)
      .subscribe({ next: (res) => this.components.set(res.data) });
  }

  submit(): void {
    const f = this.form;
    if (
      !f.grantId ||
      !f.targetTenantId ||
      !f.moduleCodes.length ||
      !f.actionPermissions.length ||
      !f.dataAccessScope ||
      !f.accessDecision
    ) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if (f.accessDecision === 'Deny' && !f.restrictionReason?.trim()) {
      this.dialogs.showToast('Give the reason for this restriction.', 'warning');
      return;
    }
    const payload: RulePayload = {
      grantId: f.grantId,
      targetTenantId: f.targetTenantId,
      moduleCodes: f.moduleCodes,
      componentCodes: f.componentCodes,
      actionPermissions: f.actionPermissions,
      dataAccessScope: f.dataAccessScope,
      accessDecision: f.accessDecision,
      restrictionReason: f.restrictionReason?.trim() || null,
    };
    this.isSaving.set(true);
    this.service.saveRule(payload, this.record?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Rule saved and waiting for review.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this rule.'), 'error', 5000);
      },
    });
  }
}
