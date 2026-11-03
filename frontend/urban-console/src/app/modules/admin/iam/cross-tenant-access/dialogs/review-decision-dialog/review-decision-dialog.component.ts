import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CrossTenantService } from '../../../../../../core/services/cross-tenant.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { apiError } from '../../../../../../core/models/white-label.model';
import { ReviewItem } from '../../../../../../core/models/cross-tenant.model';

/** Tab 4: the review owner's decision on one access record. */
@Component({
  selector: 'app-xt-review-decision-dialog',
  standalone: true,
  imports: [FormsModule, IconComponent],
  template: `
    <div class="dialog-overlay" (click)="closed.emit()">
      <div
        class="dialog-card narrow"
        (click)="$event.stopPropagation()"
        role="dialog"
        aria-modal="true"
        aria-labelledby="xt-review-title"
      >
        <div class="dialog-header">
          <div>
            <h3 id="xt-review-title">Review Decision</h3>
            <p>Revoke ends the access now. Modify keeps it until the access record is edited.</p>
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
              <label for="reviewRecord">Access Record</label>
              <input
                id="reviewRecord"
                type="text"
                readonly
                [value]="
                  item.recordNumber +
                  ': ' +
                  item.userName +
                  ', ' +
                  item.accessLevel +
                  ' (' +
                  item.grantStatus +
                  ')'
                "
              />
            </div>
            <div class="field wide">
              <label for="reviewDecision">Review Decision <span class="required">*</span></label>
              <select id="reviewDecision" name="reviewDecision" [(ngModel)]="decision">
                <option value="">Select</option>
                @for (d of decisions; track d) {
                  <option [value]="d">{{ d }}</option>
                }
              </select>
            </div>
            <div class="field wide">
              <label for="reviewComments"
                >Reviewer Comments
                @if (decision && decision !== 'Retain') {
                  <span class="required">*</span>
                }
              </label>
              <textarea
                id="reviewComments"
                name="reviewComments"
                maxlength="2000"
                [(ngModel)]="comments"
              ></textarea>
            </div>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-outline" (click)="closed.emit()">Cancel</button>
            <button
              type="submit"
              class="btn btn-primary"
              [class.danger]="decision === 'Revoke'"
              [disabled]="isSaving()"
            >
              <span>Record Decision</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styleUrl: '../grant-dialog/grant-dialog.component.scss',
})
export class ReviewDecisionDialogComponent {
  @Input({ required: true }) campaignId!: string;
  @Input({ required: true }) item!: ReviewItem;
  @Input({ required: true }) decisions!: string[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(CrossTenantService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  decision = '';
  comments = '';

  submit(): void {
    if (!this.decision) {
      this.dialogs.showToast('Choose a decision.', 'warning');
      return;
    }
    if (this.decision !== 'Retain' && !this.comments.trim()) {
      this.dialogs.showToast('Add a comment when modifying or revoking access.', 'warning');
      return;
    }
    this.isSaving.set(true);
    this.service
      .decideItem(this.campaignId, this.item.id, this.decision, this.comments.trim() || null)
      .subscribe({
        next: () => {
          this.isSaving.set(false);
          this.dialogs.showToast('Decision recorded.', 'success');
          this.saved.emit();
        },
        error: (err) => {
          this.isSaving.set(false);
          this.dialogs.showToast(apiError(err, 'Could not record this decision.'), 'error', 5000);
        },
      });
  }
}
