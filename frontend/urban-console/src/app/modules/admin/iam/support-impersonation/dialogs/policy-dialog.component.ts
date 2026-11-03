import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { CheckListComponent } from '../../../../../shared/components/check-list/check-list.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { CrossTenantService } from '../../../../../core/services/cross-tenant.service';
import { DialogService } from '../../../../../core/services/dialog.service';
import { apiError } from '../../../../../core/models/white-label.model';
import { ComponentOption } from '../../../../../core/models/cross-tenant.model';
import {
  ImpersonationOptions,
  ImpersonationPolicy,
} from '../../../../../core/models/impersonation.model';
import { asOptions } from '../../cross-tenant-access/cross-tenant-utils';

/** Tab 4: who may impersonate, where, for how long, and with what limits. */
@Component({
  selector: 'app-imp-policy-dialog',
  standalone: true,
  imports: [FormsModule, IconComponent, CheckListComponent],
  template: `
    <div class="dialog-overlay" (click)="closed.emit()">
      <div
        class="dialog-card"
        (click)="$event.stopPropagation()"
        role="dialog"
        aria-modal="true"
        aria-labelledby="imp-policy-title"
      >
        <div class="dialog-header">
          <div>
            <h3 id="imp-policy-title">{{ record ? 'Edit' : 'New' }} Impersonation Policy</h3>
            <p>
              Each tenant level can have one active policy. Requests copy the policy when they are
              made.
            </p>
          </div>
          <button
            type="button"
            class="close-btn"
            (click)="closed.emit()"
            title="Close dialog"
            aria-label="Close dialog"
          >
            <app-icon name="ri-close-line" [size]="18"></app-icon>
          </button>
        </div>
        <form class="dialog-form" (ngSubmit)="submit()">
          <div class="dialog-body">
            <div class="field">
              <label for="polName">Policy Name <span class="required">*</span></label
              ><input
                id="polName"
                type="text"
                name="policyName"
                maxlength="150"
                [(ngModel)]="form.policyName"
              />
            </div>
            <div class="field">
              <label for="polCode">Policy Code</label
              ><input
                id="polCode"
                type="text"
                readonly
                [value]="record?.policyCode ?? 'Set on save'"
              />
            </div>
            <div class="field wide">
              <label>Allowed Support Roles <span class="required">*</span></label>
              <app-check-list
                [options]="roleChoices"
                [value]="form.allowedSupportRoles"
                (valueChange)="form.allowedSupportRoles = $event"
              ></app-check-list>
            </div>
            <div class="field wide">
              <label>Allowed Tenant Levels <span class="required">*</span></label>
              <app-check-list
                [options]="asOptions(options.tenantLevels)"
                [value]="form.allowedTenantLevels"
                (valueChange)="form.allowedTenantLevels = $event"
              ></app-check-list>
            </div>
            <div class="field">
              <label for="polMax"
                >Maximum Session Duration (minutes) <span class="required">*</span></label
              >
              <input
                id="polMax"
                type="number"
                min="5"
                max="60"
                name="maxSessionMinutes"
                [(ngModel)]="form.maxSessionMinutes"
              />
            </div>
            <div class="field wide toggles">
              <label class="toggle"
                ><input
                  type="checkbox"
                  name="approvalRequired"
                  [(ngModel)]="form.approvalRequired"
                  (ngModelChange)="!$event && (form.dualApproval = false)"
                />
                Approval Required</label
              >
              <label class="toggle"
                ><input
                  type="checkbox"
                  name="dualApproval"
                  [(ngModel)]="form.dualApproval"
                  [disabled]="!form.approvalRequired"
                />
                Dual Approval</label
              >
              <label class="toggle"
                ><input type="checkbox" name="readOnlyDefault" [(ngModel)]="form.readOnlyDefault" />
                Read-Only Default</label
              >
              <label class="toggle"
                ><input
                  type="checkbox"
                  name="maskSensitiveData"
                  [(ngModel)]="form.maskSensitiveData"
                />
                Sensitive Data Masking</label
              >
              <label class="toggle"
                ><input
                  type="checkbox"
                  name="downloadDisabled"
                  [(ngModel)]="form.downloadDisabled"
                />
                Download Disabled</label
              >
              <label class="toggle"
                ><input
                  type="checkbox"
                  name="sessionRecording"
                  [(ngModel)]="form.sessionRecording"
                />
                Session Recording</label
              >
              <label class="toggle"
                ><input type="checkbox" name="isActive" [(ngModel)]="form.isActive" /> Policy
                Status: Active</label
              >
            </div>
            @if (!form.approvalRequired) {
              <div class="wl-notice bad wide-notice">
                Without approval, any allowed support role can start a session straight away. Every
                session is still audited.
              </div>
            }
            @if (form.maskSensitiveData) {
              <div class="wl-notice wide-notice">
                Fields whose names contain {{ options.sensitiveFieldParts.join(', ') }} are partly
                hidden. A field named otherwise is not.
              </div>
            }
            <div class="field wide">
              <label for="polModule">Write Actions Allowed</label>
              <div class="inline-add">
                <select
                  id="polModule"
                  name="writeModule"
                  [ngModel]="module"
                  (ngModelChange)="onModule($event)"
                >
                  <option value="">Module</option>
                  @for (m of modules(); track m.code) {
                    <option [value]="m.code">{{ m.code }} {{ m.name }}</option>
                  }
                </select>
                <select
                  aria-label="Component"
                  name="writeComponent"
                  [(ngModel)]="component"
                  [disabled]="!module"
                >
                  <option value="">Component</option>
                  @for (c of components(); track c.code) {
                    <option [value]="c.code">{{ c.code }} {{ c.name }}</option>
                  }
                </select>
                <select aria-label="Action" name="writeAction" [(ngModel)]="action">
                  <option value="">Action</option>
                  @for (a of options.writeActionTypes; track a) {
                    <option [value]="a">{{ a }}</option>
                  }
                </select>
                <button type="button" class="btn btn-outline" (click)="addAction()">Add</button>
              </div>
              <div class="chips">
                @for (a of form.writeActionsAllowed; track a) {
                  <span class="chip"
                    >{{ a
                    }}<button
                      type="button"
                      (click)="removeAction(a)"
                      [attr.aria-label]="'Remove ' + a"
                    >
                      ✕
                    </button></span
                  >
                } @empty {
                  <span class="hint">None. Sessions under this policy are read only.</span>
                }
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-outline" (click)="closed.emit()">Cancel</button>
            <button type="submit" class="btn btn-primary" [disabled]="isSaving()">
              <app-icon name="ri-check-line" [size]="16"></app-icon><span>Save Policy</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styleUrl: '../hub.scss',
})
export class PolicyDialogComponent implements OnInit {
  @Input() record: ImpersonationPolicy | null = null;
  @Input({ required: true }) options!: ImpersonationOptions;
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(ImpersonationService);
  private catalogue = inject(CrossTenantService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  readonly modules = signal<{ code: string; name: string }[]>([]);
  readonly components = signal<ComponentOption[]>([]);
  readonly asOptions = asOptions;

  module = '';
  component = '';
  action = '';
  form: ImpersonationPolicy = {
    policyName: '',
    allowedSupportRoles: [],
    allowedTenantLevels: [],
    maxSessionMinutes: 15,
    approvalRequired: true,
    dualApproval: false,
    readOnlyDefault: true,
    maskSensitiveData: true,
    downloadDisabled: true,
    writeActionsAllowed: [],
    sessionRecording: true,
    isActive: true,
  };

  get roleChoices(): { value: string; label: string }[] {
    return this.options.roles.map((r) => ({ value: r.code, label: r.name }));
  }

  ngOnInit(): void {
    if (this.record)
      this.form = {
        ...this.record,
        allowedSupportRoles: [...this.record.allowedSupportRoles],
        allowedTenantLevels: [...this.record.allowedTenantLevels],
        writeActionsAllowed: [...this.record.writeActionsAllowed],
      };
    this.catalogue.getOptions().subscribe({ next: (res) => this.modules.set(res.data.modules) });
  }

  onModule(code: string): void {
    this.module = code;
    this.component = '';
    this.components.set([]);
    if (code)
      this.catalogue
        .getComponents([code])
        .subscribe({ next: (res) => this.components.set(res.data) });
  }

  addAction(): void {
    if (!this.component || !this.action) {
      this.dialogs.showToast('Choose a component and an action.', 'warning');
      return;
    }
    const value = `${this.component}:${this.action}`;
    if (!this.form.writeActionsAllowed.includes(value))
      this.form.writeActionsAllowed = [...this.form.writeActionsAllowed, value];
  }

  removeAction(value: string): void {
    this.form.writeActionsAllowed = this.form.writeActionsAllowed.filter((a) => a !== value);
  }

  submit(): void {
    const f = this.form;
    if (
      !f.policyName.trim() ||
      !f.allowedSupportRoles.length ||
      !f.allowedTenantLevels.length ||
      !(f.maxSessionMinutes >= 5 && f.maxSessionMinutes <= 60)
    ) {
      this.dialogs.showToast(
        'Complete the required fields. The maximum session is 5 to 60 minutes.',
        'warning',
      );
      return;
    }
    const payload: ImpersonationPolicy = {
      policyName: f.policyName.trim(),
      allowedSupportRoles: f.allowedSupportRoles,
      allowedTenantLevels: f.allowedTenantLevels,
      maxSessionMinutes: Number(f.maxSessionMinutes),
      approvalRequired: f.approvalRequired,
      dualApproval: f.approvalRequired && f.dualApproval,
      readOnlyDefault: f.readOnlyDefault,
      maskSensitiveData: f.maskSensitiveData,
      downloadDisabled: f.downloadDisabled,
      writeActionsAllowed: f.writeActionsAllowed,
      sessionRecording: f.sessionRecording,
      isActive: f.isActive,
    };
    this.isSaving.set(true);
    this.service.savePolicy(payload, this.record?.id).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Policy saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this policy.'), 'error', 5000);
      },
    });
  }
}
