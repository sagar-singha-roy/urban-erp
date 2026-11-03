import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CheckListComponent } from '../../../../../../shared/components/check-list/check-list.component';
import { CrossTenantService } from '../../../../../../core/services/cross-tenant.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../../../core/models/white-label.model';
import {
  CampaignPayload,
  CrossTenantOptions,
  UserOption,
} from '../../../../../../core/models/cross-tenant.model';
import { asOptions, fromLocalInput, tenantOptions } from '../../cross-tenant-utils';

const CERTIFIABLE_STATUSES = ['Active', 'Expired', 'Pending'];

/** Tab 4: start a certification round over the access records that match. */
@Component({
  selector: 'app-xt-campaign-dialog',
  standalone: true,
  imports: [FormsModule, IconComponent, CheckListComponent],
  template: `
    <div class="dialog-overlay" (click)="closed.emit()">
      <div
        class="dialog-card"
        (click)="$event.stopPropagation()"
        role="dialog"
        aria-modal="true"
        aria-labelledby="xt-campaign-title"
      >
        <div class="dialog-header">
          <div>
            <h3 id="xt-campaign-title">New Access Review Campaign</h3>
            <p>Every access record that matches these filters is added for review.</p>
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
              <label for="campaignName">Review Campaign Name <span class="required">*</span></label>
              <input
                id="campaignName"
                type="text"
                name="campaignName"
                maxlength="150"
                [(ngModel)]="form.campaignName"
              />
            </div>
            <div class="field">
              <label for="periodStart">Review Period Start <span class="required">*</span></label
              ><input id="periodStart" type="date" name="periodStart" [(ngModel)]="periodStart" />
            </div>
            <div class="field">
              <label for="periodEnd">Review Period End <span class="required">*</span></label
              ><input id="periodEnd" type="date" name="periodEnd" [(ngModel)]="periodEnd" />
            </div>
            <div class="field wide">
              <label>Tenant Scope</label>
              <app-check-list
                [options]="tenantChoices"
                [value]="form.tenantScope"
                (valueChange)="form.tenantScope = $event"
              ></app-check-list>
              <span class="hint">Leave empty to cover every tenant.</span>
            </div>
            <div class="field wide">
              <label>User Type <span class="required">*</span></label>
              <app-check-list
                [options]="asOptions(options.userTypes)"
                [value]="form.userTypes"
                (valueChange)="form.userTypes = $event"
              ></app-check-list>
            </div>
            <div class="field wide">
              <label>Access Status <span class="required">*</span></label>
              <app-check-list
                [options]="asOptions(statuses)"
                [value]="form.accessStatuses"
                (valueChange)="form.accessStatuses = $event"
              ></app-check-list>
            </div>
            <div class="field">
              <label for="reviewOwnerId">Review Owner <span class="required">*</span></label>
              <select id="reviewOwnerId" name="reviewOwnerId" [(ngModel)]="form.reviewOwnerId">
                <option value="">Select</option>
                @for (a of authorities; track a.id) {
                  <option [value]="a.id">{{ a.fullName }} ({{ a.email }})</option>
                }</select
              ><span class="hint">Only the owner can record decisions.</span>
            </div>
            <div class="field">
              <label for="reviewDeadline">Review Deadline <span class="required">*</span></label
              ><input
                id="reviewDeadline"
                type="date"
                name="reviewDeadline"
                [(ngModel)]="form.reviewDeadline"
              />
            </div>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-outline" (click)="closed.emit()">Cancel</button>
            <button type="submit" class="btn btn-primary" [disabled]="isSaving()">
              <app-icon name="ri-check-line" [size]="16"></app-icon><span>Start Campaign</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styleUrl: '../grant-dialog/grant-dialog.component.scss',
})
export class CampaignDialogComponent {
  @Input({ required: true }) options!: CrossTenantOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Input({ required: true }) authorities!: UserOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(CrossTenantService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  readonly asOptions = asOptions;
  readonly statuses = CERTIFIABLE_STATUSES;

  periodStart = '';
  periodEnd = '';
  form: CampaignPayload = {
    campaignName: '',
    periodStart: '',
    periodEnd: '',
    tenantScope: [],
    userTypes: [],
    accessStatuses: ['Active'],
    reviewOwnerId: '',
    reviewDeadline: '',
  };

  get tenantChoices(): { value: string; label: string }[] {
    return tenantOptions(this.tenants);
  }

  submit(): void {
    const f = this.form;
    if (
      !f.campaignName.trim() ||
      !this.periodStart ||
      !this.periodEnd ||
      !f.userTypes.length ||
      !f.accessStatuses.length ||
      !f.reviewOwnerId ||
      !f.reviewDeadline
    ) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    const payload: CampaignPayload = {
      ...f,
      campaignName: f.campaignName.trim(),
      periodStart: fromLocalInput(`${this.periodStart}T00:00`)!,
      periodEnd: fromLocalInput(`${this.periodEnd}T23:59`)!,
    };
    this.isSaving.set(true);
    this.service.createCampaign(payload).subscribe({
      next: (res) => {
        this.isSaving.set(false);
        this.dialogs.showToast(
          `Campaign started with ${res.data.totalItems} access records to review.`,
          'success',
        );
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not start this campaign.'), 'error', 5000);
      },
    });
  }
}
