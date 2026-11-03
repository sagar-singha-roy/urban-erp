import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CrossTenantService } from '../../../../../../core/services/cross-tenant.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { ApiResponse, apiError } from '../../../../../../core/models/white-label.model';
import { AccessGrant } from '../../../../../../core/models/cross-tenant.model';

export type GrantDecisionMode = 'approve' | 'reject' | 'revoke';

const COPY: Record<
  GrantDecisionMode,
  { title: string; intro: string; label: string; button: string; done: string }
> = {
  approve: {
    title: 'Approve Access',
    intro: 'The user can reach the target tenants from their next request.',
    label: 'Approval Note',
    button: 'Approve',
    done: 'Access approved.',
  },
  reject: {
    title: 'Reject Access',
    intro: 'The request closes and the user gets no access.',
    label: 'Reason for Rejection',
    button: 'Reject',
    done: 'Access rejected.',
  },
  revoke: {
    title: 'Revoke Access',
    intro: 'Access ends at once, including for anyone signed in now.',
    label: 'Reason for Revocation',
    button: 'Revoke',
    done: 'Access revoked.',
  },
};

@Component({
  selector: 'app-xt-grant-decision-dialog',
  standalone: true,
  imports: [FormsModule, IconComponent],
  templateUrl: './grant-decision-dialog.component.html',
  styleUrl: '../grant-dialog/grant-dialog.component.scss',
})
export class GrantDecisionDialogComponent {
  @Input({ required: true }) grant!: AccessGrant;
  @Input({ required: true }) mode!: GrantDecisionMode;
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(CrossTenantService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  reason = '';

  get copy() {
    return COPY[this.mode];
  }

  submit(): void {
    const reason = this.reason.trim();
    if (this.mode !== 'approve' && reason.length < 3) {
      this.dialogs.showToast('Please give a reason.', 'warning');
      return;
    }
    const call: Observable<ApiResponse<AccessGrant>> =
      this.mode === 'approve'
        ? this.service.approveGrant(this.grant.id, reason || null)
        : this.mode === 'reject'
          ? this.service.rejectGrant(this.grant.id, reason)
          : this.service.revokeGrant(this.grant.id, reason);
    this.isSaving.set(true);
    call.subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast(this.copy.done, 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not record this decision.'), 'error', 5000);
      },
    });
  }
}
