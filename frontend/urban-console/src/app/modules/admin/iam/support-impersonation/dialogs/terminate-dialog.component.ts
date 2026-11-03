import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { DialogService } from '../../../../../core/services/dialog.service';
import { apiError } from '../../../../../core/models/white-label.model';
import { SupportSession } from '../../../../../core/models/impersonation.model';

/** Tab 3: end a live session. It stops working on the agent's next request. */
@Component({
  selector: 'app-imp-terminate-dialog',
  standalone: true,
  imports: [FormsModule, IconComponent],
  template: `
    <div class="dialog-overlay" (click)="closed.emit()">
      <div
        class="dialog-card narrow"
        (click)="$event.stopPropagation()"
        role="dialog"
        aria-modal="true"
        aria-labelledby="imp-terminate-title"
      >
        <div class="dialog-header">
          <div>
            <h3 id="imp-terminate-title">Terminate Session</h3>
            <p>
              {{ session.sessionNumber }}: {{ session.supportEmail }} acting as
              {{ session.targetEmail }}. It ends on the agent's next request.
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
              <label for="impReason">Termination Reason <span class="required">*</span></label>
              <textarea
                id="impReason"
                name="reason"
                maxlength="2000"
                [(ngModel)]="reason"
              ></textarea>
            </div>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-outline" (click)="closed.emit()">Cancel</button>
            <button type="submit" class="btn btn-primary danger" [disabled]="isSaving()">
              <span>Terminate</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styleUrl: '../hub.scss',
})
export class TerminateDialogComponent {
  @Input({ required: true }) session!: SupportSession;
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(ImpersonationService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  reason = '';

  submit(): void {
    if (this.reason.trim().length < 3) {
      this.dialogs.showToast('Give the reason for ending this session.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service.terminate(this.session.id, this.reason.trim()).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Session terminated.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not end this session.'), 'error', 5000);
      },
    });
  }
}
