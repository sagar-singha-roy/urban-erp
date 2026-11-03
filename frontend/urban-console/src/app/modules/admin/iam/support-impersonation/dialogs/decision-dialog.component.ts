import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { DialogService } from '../../../../../core/services/dialog.service';
import { apiError } from '../../../../../core/models/white-label.model';
import {
  ApproverOption,
  HubProfile,
  ImpersonationRequest,
} from '../../../../../core/models/impersonation.model';
import { fromLocalInput, toLocalInput } from '../../cross-tenant-access/cross-tenant-utils';

const DEFAULT_VALIDITY_HOURS = 2;

/** Tab 2: one approver's decision. The approver is always the signed-in user. */
@Component({
  selector: 'app-imp-decision-dialog',
  standalone: true,
  imports: [FormsModule, IconComponent],
  template: `
    <div class="dialog-overlay" (click)="closed.emit()">
      <div
        class="dialog-card"
        (click)="$event.stopPropagation()"
        role="dialog"
        aria-modal="true"
        aria-labelledby="imp-decision-title"
      >
        <div class="dialog-header">
          <div>
            <h3 id="imp-decision-title">
              {{ stage === 2 ? 'Second Approval' : 'Approval Decision' }}
            </h3>
            <p>
              {{ request.requestNumber }}: {{ request.supportName }} asks to act as
              {{ request.targetName }} for {{ request.requestedMinutes }} minutes ({{
                request.accessMode
              }}).
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
            <div class="field wide">
              <label for="impJustificationView">Business Justification</label
              ><textarea
                id="impJustificationView"
                readonly
                [value]="request.businessJustification"
              ></textarea>
              <span class="hint"
                >Ticket {{ request.ticketReference }}. {{ request.requestType }}. Policy
                {{ request.policyCode }}.</span
              >
            </div>
            <div class="field">
              <label for="impApprover">Approver</label
              ><input
                id="impApprover"
                type="text"
                readonly
                [value]="me.fullName + ' (' + me.email + ')'"
              />
            </div>
            <div class="field">
              <label for="impDecision">Approval Status <span class="required">*</span></label>
              <select id="impDecision" name="decision" [(ngModel)]="decision">
                <option value="">Select</option>
                <option value="Approved">Approved</option>
                <option value="Rejected">Rejected</option>
              </select>
            </div>
            <div class="field wide">
              <label for="impComments"
                >Approval Comments
                @if (decision === 'Rejected') {
                  <span class="required">*</span>
                }
              </label>
              <textarea
                id="impComments"
                name="comments"
                maxlength="2000"
                [(ngModel)]="comments"
              ></textarea>
            </div>
            @if (decision === 'Approved') {
              <div class="field">
                <label for="impValidity">Approval Validity <span class="required">*</span></label>
                <input
                  id="impValidity"
                  type="datetime-local"
                  name="validity"
                  [(ngModel)]="validity"
                />
                <span class="hint"
                  >The session must start before this, within {{ maxHours }} hours.</span
                >
              </div>
              @if (stage === 1) {
                <div class="field">
                  <label class="toggle"
                    ><input
                      type="checkbox"
                      name="dual"
                      [(ngModel)]="dual"
                      [disabled]="request.dualApprovalRequired"
                    />
                    Dual Approval Required</label
                  >
                  <span class="hint">{{
                    request.dualApprovalRequired
                      ? 'The policy requires a second approver.'
                      : 'Turn on to require a second approver.'
                  }}</span>
                </div>
                @if (dual) {
                  <div class="field">
                    <label for="impSecond">Second Approver <span class="required">*</span></label>
                    <select id="impSecond" name="secondApprover" [(ngModel)]="secondApproverId">
                      <option value="">Select</option>
                      @for (a of secondChoices; track a.id) {
                        <option [value]="a.id">{{ a.fullName }} ({{ a.email }})</option>
                      }
                    </select>
                    @if (!secondChoices.length) {
                      <span class="hint"
                        >No other super admin can approve. Add one, or reject the request.</span
                      >
                    }
                  </div>
                }
              }
            }
            <div class="field">
              <label for="impTimestamp">Approval Timestamp</label
              ><input id="impTimestamp" type="text" readonly value="Set when you submit" />
            </div>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-outline" (click)="closed.emit()">Cancel</button>
            <button
              type="submit"
              class="btn btn-primary"
              [class.danger]="decision === 'Rejected'"
              [disabled]="isSaving()"
            >
              <span>Record Decision</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styleUrl: '../hub.scss',
})
export class DecisionDialogComponent implements OnInit {
  @Input({ required: true }) request!: ImpersonationRequest;
  @Input({ required: true }) me!: HubProfile;
  @Input({ required: true }) approvers!: ApproverOption[];
  @Input({ required: true }) maxHours!: number;
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(ImpersonationService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);

  decision = '';
  comments = '';
  validity = '';
  dual = false;
  secondApproverId = '';

  get stage(): number {
    return this.request.status === 'Awaiting Second Approval' ? 2 : 1;
  }

  get secondChoices(): ApproverOption[] {
    return this.approvers.filter((a) => a.id !== this.request.supportUserId);
  }

  ngOnInit(): void {
    this.dual = this.request.dualApprovalRequired;
    this.validity = toLocalInput(
      new Date(Date.now() + DEFAULT_VALIDITY_HOURS * 3600000).toISOString(),
    );
  }

  submit(): void {
    if (!this.decision) {
      this.dialogs.showToast('Choose Approved or Rejected.', 'warning');
      return;
    }
    if (this.decision === 'Rejected' && !this.comments.trim()) {
      this.dialogs.showToast('Say why the request is rejected.', 'warning');
      return;
    }
    if (this.decision === 'Approved' && this.stage === 1 && this.dual && !this.secondApproverId) {
      this.dialogs.showToast('Choose the second approver.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service
      .decide(this.request.id, {
        decision: this.decision,
        comments: this.comments.trim() || null,
        approvalValidUntil: this.decision === 'Approved' ? fromLocalInput(this.validity) : null,
        dualApprovalRequired: this.stage === 1 && this.dual,
        secondApproverId: this.stage === 1 && this.dual ? this.secondApproverId : null,
      })
      .subscribe({
        next: (res) => {
          this.isSaving.set(false);
          this.dialogs.showToast(`Request ${res.data.status.toLowerCase()}.`, 'success');
          this.saved.emit();
        },
        error: (err) => {
          this.isSaving.set(false);
          this.dialogs.showToast(apiError(err, 'Could not record this decision.'), 'error', 5000);
        },
      });
  }
}
