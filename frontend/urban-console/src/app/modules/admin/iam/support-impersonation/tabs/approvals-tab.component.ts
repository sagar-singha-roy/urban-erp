import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { PagedTab } from '../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../shared/components/wl-pagination/wl-pagination.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { PageQuery, PagedResponse } from '../../../../../core/models/white-label.model';
import {
  ApproverOption,
  HubProfile,
  ImpersonationOptions,
  ImpersonationRequest,
} from '../../../../../core/models/impersonation.model';
import { DecisionDialogComponent } from '../dialogs/decision-dialog.component';
import { asUtc, grantStatusClass } from '../../cross-tenant-access/cross-tenant-utils';

/** Tab 2: approval management. Approvers decide as themselves; requesters never decide their own requests. */
@Component({
  selector: 'app-imp-approvals-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, WlPaginationComponent, DecisionDialogComponent],
  template: `
    <div class="wl-toolbar">
      <input
        class="wl-search"
        type="search"
        placeholder="Search users, tickets or request IDs"
        aria-label="Search users, tickets or request IDs"
        [ngModel]="search()"
        (ngModelChange)="onSearch($event)"
      />
      <select
        class="filter"
        aria-label="Filter by status"
        [ngModel]="status()"
        (ngModelChange)="setStatus($event)"
      >
        <option value="">All statuses</option>
        @for (s of options().requestStatuses; track s) {
          <option [value]="s">{{ s }}</option>
        }
      </select>
    </div>
    <div class="wl-card">
      <div class="wl-scroll">
        <table class="wl-table">
          <thead>
            <tr>
              <th>Request ID</th>
              <th>Requested By</th>
              <th>Target</th>
              <th>Justification</th>
              <th>Duration / Mode</th>
              <th>Status</th>
              <th>Approvals</th>
              <th>Approval Validity</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (r of items(); track r.id) {
              <tr>
                <td>
                  {{ r.requestNumber }}<span class="wl-sub">{{ r.ticketReference }}</span>
                </td>
                <td>
                  {{ r.supportName }}<span class="wl-sub">{{ r.supportEmail }}</span>
                </td>
                <td>
                  {{ r.targetName
                  }}<span class="wl-sub">{{ r.targetEmail }}, {{ r.targetTenantId }}</span>
                </td>
                <td class="clip">{{ r.businessJustification }}</td>
                <td>
                  {{ r.requestedMinutes }} min<span class="wl-sub">{{ r.accessMode }}</span>
                </td>
                <td>
                  <span class="wl-status" [ngClass]="statusClass2(r.status)">{{ r.status }}</span>
                  @if (r.dualApprovalRequired) {
                    <span class="wl-sub"
                      >Dual approval{{
                        r.secondApproverEmail ? ': ' + r.secondApproverEmail : ''
                      }}</span
                    >
                  }
                </td>
                <td>
                  @for (a of r.approvals; track a.stage) {
                    <span class="wl-sub"
                      >{{ a.stage }}. {{ a.decision }} by {{ a.approverEmail }},
                      {{ asUtc(a.decidedAt) | date: 'short' }}</span
                    >
                  } @empty {
                    -
                  }
                </td>
                <td>
                  {{ r.approvalValidUntil ? (asUtc(r.approvalValidUntil) | date: 'medium') : '-' }}
                </td>
                <td>
                  <div class="wl-actions">
                    @if (canDecide(r)) {
                      <button type="button" class="wl-link" (click)="deciding.set(r)">
                        Decide
                      </button>
                    }
                  </div>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="9" class="wl-empty">
                  {{ isLoading() ? 'Loading...' : 'No requests match.' }}
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
    @if (deciding(); as r) {
      <app-imp-decision-dialog
        [request]="r"
        [me]="me()"
        [approvers]="approvers()"
        [maxHours]="options().maxApprovalHours"
        (saved)="deciding.set(null); load()"
        (closed)="deciding.set(null)"
      ></app-imp-decision-dialog>
    }
  `,
  styleUrl: '../hub.scss',
})
export class ApprovalsTabComponent extends PagedTab<ImpersonationRequest> {
  private service = inject(ImpersonationService);
  readonly options = input.required<ImpersonationOptions>();
  readonly me = input.required<HubProfile>();
  readonly status = signal('Pending');
  readonly deciding = signal<ImpersonationRequest | null>(null);
  readonly approvers = signal<ApproverOption[]>([]);
  readonly asUtc = asUtc;
  readonly statusClass2 = grantStatusClass;

  override ngOnInit(): void {
    super.ngOnInit();
    this.service.getApprovers().subscribe({ next: (res) => this.approvers.set(res.data) });
  }

  protected fetch(query: PageQuery): Observable<PagedResponse<ImpersonationRequest>> {
    return this.service.listRequests(query, this.status() || undefined);
  }

  canDecide(r: ImpersonationRequest): boolean {
    const me = this.me();
    if (r.supportUserId === me.userId) return false;
    if (r.status === 'Pending') return true;
    return r.status === 'Awaiting Second Approval' && r.secondApproverEmail === me.email;
  }

  setStatus(value: string): void {
    this.status.set(value);
    this.page.set(1);
    this.load();
  }
}
