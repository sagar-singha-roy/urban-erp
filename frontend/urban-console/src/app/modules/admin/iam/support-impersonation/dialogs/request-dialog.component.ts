import {
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { DialogService } from '../../../../../core/services/dialog.service';
import { apiError } from '../../../../../core/models/white-label.model';
import {
  HubProfile,
  ImpersonationOptions,
  RequestPayload,
  TargetOption,
} from '../../../../../core/models/impersonation.model';

const SEARCH_DELAY_MS = 300;

/** Tab 1: ask to act as a user for a short, approved session. */
@Component({
  selector: 'app-imp-request-dialog',
  standalone: true,
  imports: [FormsModule, IconComponent],
  template: `
    <div class="dialog-overlay" (click)="closed.emit()">
      <div
        class="dialog-card"
        (click)="$event.stopPropagation()"
        role="dialog"
        aria-modal="true"
        aria-labelledby="imp-request-title"
      >
        <div class="dialog-header">
          <div>
            <h3 id="imp-request-title">New Impersonation Request</h3>
            <p>
              You never see the user's password. Approval gives you a short session of your own.
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
              <label for="impSupportUser">Support User</label
              ><input
                id="impSupportUser"
                type="text"
                readonly
                [value]="me.fullName + ' (' + me.email + ')'"
              />
            </div>
            <div class="field">
              <label for="impRequestedAt">Requested At</label
              ><input id="impRequestedAt" type="text" readonly value="Set when you submit" />
            </div>
            <div class="field wide">
              <label for="impTargetSearch">Target User <span class="required">*</span></label>
              <input
                id="impTargetSearch"
                type="search"
                placeholder="Search name or email"
                autocomplete="off"
                [ngModel]="term()"
                (ngModelChange)="onSearch($event)"
                name="targetSearch"
              />
              <select
                aria-label="Target user"
                name="targetUserId"
                [ngModel]="form.targetUserId"
                (ngModelChange)="pickTarget($event)"
              >
                <option value="">
                  {{ targets().length ? 'Select a user' : 'No matching users' }}
                </option>
                @for (t of targets(); track t.id) {
                  <option [value]="t.id">{{ t.fullName }} ({{ t.email }})</option>
                }
              </select>
            </div>
            <div class="field">
              <label for="impTargetEmail">Target Email</label
              ><input
                id="impTargetEmail"
                type="text"
                readonly
                [value]="target()?.email ?? ''"
                placeholder="Filled in from the user"
              />
            </div>
            <div class="field">
              <label for="impTenant">Target Tenant <span class="required">*</span></label>
              <select
                id="impTenant"
                name="targetTenantId"
                [(ngModel)]="form.targetTenantId"
                [disabled]="!target()"
              >
                <option value="">Select</option>
                @for (t of target()?.tenantIds ?? []; track t) {
                  <option [value]="t">{{ t }}</option>
                }</select
              ><span class="hint">Only the user's own tenants. The session covers one.</span>
            </div>
            <div class="field">
              <label for="impType">Request Type <span class="required">*</span></label>
              <select id="impType" name="requestType" [(ngModel)]="form.requestType">
                <option value="">Select</option>
                @for (o of options.requestTypes; track o) {
                  <option [value]="o">{{ o }}</option>
                }
              </select>
            </div>
            <div class="field">
              <label for="impTicket">Ticket Reference <span class="required">*</span></label
              ><input
                id="impTicket"
                type="text"
                name="ticketReference"
                maxlength="100"
                [(ngModel)]="form.ticketReference"
              />
            </div>
            <div class="field">
              <label for="impDuration">Requested Duration <span class="required">*</span></label>
              <select id="impDuration" name="requestedMinutes" [(ngModel)]="form.requestedMinutes">
                @for (d of options.durations; track d) {
                  <option [ngValue]="d">{{ d }} minutes</option>
                }
              </select>
            </div>
            <div class="field">
              <label for="impMode">Requested Access Mode <span class="required">*</span></label>
              <select id="impMode" name="accessMode" [(ngModel)]="form.accessMode">
                @for (m of options.accessModes; track m) {
                  <option [value]="m">{{ m }}</option>
                }</select
              ><span class="hint"
                >Restricted Actions allows only the actions the policy lists.</span
              >
            </div>
            <div class="field wide">
              <label for="impJustification"
                >Business Justification <span class="required">*</span></label
              >
              <textarea
                id="impJustification"
                name="businessJustification"
                maxlength="2000"
                [(ngModel)]="form.businessJustification"
              ></textarea>
              <span class="hint">At least 20 characters. Approvers and auditors read this.</span>
            </div>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-outline" (click)="closed.emit()">Cancel</button>
            <button type="submit" class="btn btn-primary" [disabled]="isSaving()">
              <app-icon name="ri-send-plane-line" [size]="16"></app-icon><span>Submit Request</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styleUrl: '../hub.scss',
})
export class RequestDialogComponent implements OnInit, OnDestroy {
  @Input({ required: true }) options!: ImpersonationOptions;
  @Input({ required: true }) me!: HubProfile;
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(ImpersonationService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  readonly term = signal('');
  readonly targets = signal<TargetOption[]>([]);
  readonly target = signal<TargetOption | null>(null);
  private timer?: ReturnType<typeof setTimeout>;

  form: RequestPayload = {
    targetUserId: '',
    targetTenantId: '',
    requestType: '',
    businessJustification: '',
    ticketReference: '',
    requestedMinutes: 15,
    accessMode: 'Read Only',
  };

  ngOnInit(): void {
    this.search('');
  }

  ngOnDestroy(): void {
    clearTimeout(this.timer);
  }

  onSearch(value: string): void {
    this.term.set(value);
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.search(value.trim()), SEARCH_DELAY_MS);
  }

  private search(value: string): void {
    this.service.findTargets(value).subscribe({ next: (res) => this.targets.set(res.data) });
  }

  pickTarget(id: string): void {
    const target = this.targets().find((t) => t.id === id) ?? null;
    this.target.set(target);
    this.form.targetUserId = target?.id ?? '';
    this.form.targetTenantId = target?.tenantIds[0] ?? '';
  }

  submit(): void {
    const f = this.form;
    if (
      !f.targetUserId ||
      !f.targetTenantId ||
      !f.requestType ||
      !f.ticketReference.trim() ||
      !f.accessMode
    ) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    if (f.businessJustification.trim().length < 20) {
      this.dialogs.showToast('Explain the reason in at least 20 characters.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service.createRequest(f).subscribe({
      next: (res) => {
        this.isSaving.set(false);
        this.dialogs.showToast(
          res.data.status === 'Approved'
            ? 'Request approved by policy. You can start the session.'
            : 'Request sent for approval.',
          'success',
        );
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not send this request.'), 'error', 5000);
      },
    });
  }
}
