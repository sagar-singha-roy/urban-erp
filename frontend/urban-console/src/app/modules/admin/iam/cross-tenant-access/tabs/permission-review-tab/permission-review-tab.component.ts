import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { PagedTab } from '../../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../../shared/components/wl-pagination/wl-pagination.component';
import { CrossTenantService } from '../../../../../../core/services/cross-tenant.service';
import {
  PageQuery,
  PagedResponse,
  TenantOption,
  apiError,
} from '../../../../../../core/models/white-label.model';
import {
  CrossTenantOptions,
  PermissionRule,
} from '../../../../../../core/models/cross-tenant.model';
import { PermissionRuleDialogComponent } from '../../dialogs/permission-rule-dialog/permission-rule-dialog.component';
import { asUtc, grantStatusClass, tenantName } from '../../cross-tenant-utils';

/** Tab 3: permission rules and their review. An approved Deny rule is enforced at once. */
@Component({
  selector: 'app-xt-permission-review-tab',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent,
    WlPaginationComponent,
    PermissionRuleDialogComponent,
  ],
  template: `
    <div class="wl-toolbar">
      <input
        class="wl-search"
        type="search"
        placeholder="Search users, tenants or decisions"
        aria-label="Search users, tenants or decisions"
        [ngModel]="search()"
        (ngModelChange)="onSearch($event)"
      />
      <select
        class="filter"
        aria-label="Filter by review status"
        [ngModel]="reviewStatus()"
        (ngModelChange)="setReviewStatus($event)"
      >
        <option value="">All review statuses</option>
        @for (s of options().reviewStatuses; track s) {
          <option [value]="s">{{ s }}</option>
        }
      </select>
      <button type="button" class="btn btn-primary" (click)="editing.set(null)">
        <app-icon name="ri-add-line" [size]="16"></app-icon><span>New Rule</span>
      </button>
    </div>
    <div class="wl-card">
      <div class="wl-scroll">
        <table class="wl-table">
          <thead>
            <tr>
              <th>Record ID</th>
              <th>User</th>
              <th>Tenant</th>
              <th>Modules</th>
              <th>Components</th>
              <th>Actions</th>
              <th>Data Scope</th>
              <th>Decision</th>
              <th>Review</th>
              <th>Reviewed</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (r of items(); track r.id) {
              <tr>
                <td>{{ r.recordNumber }}</td>
                <td>
                  {{ r.userEmail }}<span class="wl-sub">Written by {{ r.createdBy }}</span>
                </td>
                <td>{{ tenantName(r.targetTenantId) }}</td>
                <td>{{ r.moduleCodes.join(', ') }}</td>
                <td class="clip">{{ r.componentCodes.join(', ') || 'All in module' }}</td>
                <td>{{ r.actionPermissions.join(', ') }}</td>
                <td>{{ r.dataAccessScope }}</td>
                <td>
                  <span class="wl-status" [ngClass]="statusClass2(r.accessDecision)">{{
                    r.accessDecision
                  }}</span>
                  @if (r.restrictionReason) {
                    <span class="wl-sub">{{ r.restrictionReason }}</span>
                  }
                </td>
                <td>
                  <span class="wl-status" [ngClass]="statusClass2(r.reviewStatus)">{{
                    r.reviewStatus
                  }}</span>
                </td>
                <td>
                  {{ r.reviewedBy ?? '-'
                  }}<span class="wl-sub">{{
                    r.reviewedAt ? (asUtc(r.reviewedAt) | date: 'medium') : ''
                  }}</span>
                </td>
                <td>
                  <div class="wl-actions">
                    @if (r.reviewStatus === 'Pending') {
                      <button type="button" class="wl-link" (click)="review(r, 'Approved')">
                        Approve
                      </button>
                      <button type="button" class="wl-link" (click)="review(r, 'Rejected')">
                        Reject
                      </button>
                    }
                    <button type="button" class="wl-link" (click)="editing.set(r)">Edit</button>
                  </div>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="11" class="wl-empty">
                  {{ isLoading() ? 'Loading...' : 'No permission rules yet.' }}
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <app-wl-pagination
        [page]="page()"
        [limit]="limit()"
        [total]="total()"
        (pageChange)="onPage($event)"
        (limitChange)="onLimit($event)"
      ></app-wl-pagination>
    </div>
    @if (editing() !== undefined) {
      <app-xt-permission-rule-dialog
        [record]="editing() ?? null"
        [options]="options()"
        [tenants]="tenants()"
        (saved)="onSaved()"
        (closed)="editing.set(undefined)"
      ></app-xt-permission-rule-dialog>
    }
  `,
  styleUrl: '../tab.scss',
})
export class PermissionReviewTabComponent extends PagedTab<PermissionRule> {
  private service = inject(CrossTenantService);
  readonly options = input.required<CrossTenantOptions>();
  readonly tenants = input.required<TenantOption[]>();
  readonly editing = signal<PermissionRule | null | undefined>(undefined);
  readonly reviewStatus = signal('');
  readonly asUtc = asUtc;
  readonly statusClass2 = grantStatusClass;

  protected fetch(query: PageQuery): Observable<PagedResponse<PermissionRule>> {
    return this.service.listRules(query, this.reviewStatus() || undefined);
  }

  tenantName(id: string): string {
    return tenantName(this.tenants(), id);
  }

  setReviewStatus(value: string): void {
    this.reviewStatus.set(value);
    this.page.set(1);
    this.load();
  }

  review(rule: PermissionRule, status: string): void {
    this.service.reviewRule(rule.id, status).subscribe({
      next: () => {
        this.dialogs.showToast(`Rule ${status.toLowerCase()}.`, 'success');
        this.load();
      },
      error: (err) =>
        this.dialogs.showToast(apiError(err, 'Could not review this rule.'), 'error', 5000),
    });
  }

  onSaved(): void {
    this.editing.set(undefined);
    this.load();
  }
}
