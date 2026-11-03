import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { PagedTab } from '../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../shared/components/wl-pagination/wl-pagination.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { supportSession } from '../../../../../core/services/support-session.state';
import { PageQuery, PagedResponse, apiError } from '../../../../../core/models/white-label.model';
import {
  HubProfile,
  ImpersonationOptions,
  ImpersonationRequest,
} from '../../../../../core/models/impersonation.model';
import { RequestDialogComponent } from '../dialogs/request-dialog.component';
import { asUtc, grantStatusClass } from '../../cross-tenant-access/cross-tenant-utils';

const OPEN = ['Pending', 'Awaiting Second Approval', 'Approved'];

/** Tab 1: impersonation requests. Support staff see their own; super admins see all. */
@Component({
  selector: 'app-imp-requests-tab',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent,
    WlPaginationComponent,
    RequestDialogComponent,
  ],
  template: `
    <div class="wl-toolbar">
      <input
        class="wl-search"
        type="search"
        placeholder="Search users, tickets, tenants or request IDs"
        aria-label="Search users, tickets, tenants or request IDs"
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
      @if (me().canRequest) {
        <button type="button" class="btn btn-primary" (click)="isCreating.set(true)">
          <app-icon name="ri-add-line" [size]="16"></app-icon><span>New Request</span>
        </button>
      }
    </div>
    @if (!me().canRequest) {
      <div class="wl-notice">
        Your role is not in an active impersonation policy, so you can review requests but not make
        them.
      </div>
    }
    <div class="wl-card">
      <div class="wl-scroll">
        <table class="wl-table">
          <thead>
            <tr>
              <th>Request ID</th>
              <th>Support User</th>
              <th>Target User</th>
              <th>Tenant</th>
              <th>Type</th>
              <th>Ticket</th>
              <th>Duration</th>
              <th>Mode</th>
              <th>Status</th>
              <th>Requested At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (r of items(); track r.id) {
              <tr>
                <td>
                  {{ r.requestNumber }}<span class="wl-sub">{{ r.policyCode }}</span>
                </td>
                <td>
                  {{ r.supportName }}<span class="wl-sub">{{ r.supportEmail }}</span>
                </td>
                <td>
                  {{ r.targetName }}<span class="wl-sub">{{ r.targetEmail }}</span>
                </td>
                <td>
                  {{ r.targetTenantId }}<span class="wl-sub">{{ r.targetTenantLevel }}</span>
                </td>
                <td>{{ r.requestType }}</td>
                <td>{{ r.ticketReference }}</td>
                <td>{{ r.requestedMinutes }} min</td>
                <td>{{ r.accessMode }}</td>
                <td>
                  <span class="wl-status" [ngClass]="statusClass2(r.status)">{{ r.status }}</span>
                  @if (r.status === 'Approved' && r.approvalValidUntil) {
                    <span class="wl-sub"
                      >Start by {{ asUtc(r.approvalValidUntil) | date: 'short' }}</span
                    >
                  }
                </td>
                <td>{{ asUtc(r.requestedAt) | date: 'medium' }}</td>
                <td>
                  <div class="wl-actions">
                    @if (isMine(r) && r.status === 'Approved') {
                      <button
                        type="button"
                        class="wl-link"
                        (click)="start(r)"
                        [disabled]="isStarting()"
                      >
                        Start session
                      </button>
                    }
                    @if ((isMine(r) || me().isSuperAdmin) && isOpen(r)) {
                      <button type="button" class="wl-link" (click)="cancel(r)">Cancel</button>
                    }
                  </div>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="11" class="wl-empty">
                  {{ isLoading() ? 'Loading...' : 'No impersonation requests yet.' }}
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
    @if (isCreating()) {
      <app-imp-request-dialog
        [options]="options()"
        [me]="me()"
        (saved)="isCreating.set(false); load()"
        (closed)="isCreating.set(false)"
      ></app-imp-request-dialog>
    }
  `,
  styleUrl: '../hub.scss',
})
export class RequestsTabComponent extends PagedTab<ImpersonationRequest> {
  private service = inject(ImpersonationService);
  private router = inject(Router);
  readonly options = input.required<ImpersonationOptions>();
  readonly me = input.required<HubProfile>();
  readonly status = signal('');
  readonly isCreating = signal(false);
  readonly isStarting = signal(false);
  readonly asUtc = asUtc;
  readonly statusClass2 = grantStatusClass;

  protected fetch(query: PageQuery): Observable<PagedResponse<ImpersonationRequest>> {
    return this.service.listRequests(query, this.status() || undefined);
  }

  isMine(r: ImpersonationRequest): boolean {
    return r.supportUserId === this.me().userId;
  }

  isOpen(r: ImpersonationRequest): boolean {
    return OPEN.includes(r.status);
  }

  setStatus(value: string): void {
    this.status.set(value);
    this.page.set(1);
    this.load();
  }

  async start(r: ImpersonationRequest): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: 'Start support session?',
      message: `You will act as ${r.targetName} in ${r.targetTenantId} for up to ${r.requestedMinutes} minutes (${r.accessMode}). Everything you do is recorded.`,
      confirmText: 'Start session',
    });
    if (!ok) return;
    this.isStarting.set(true);
    this.service.startSession(r.id).subscribe({
      next: () => {
        this.service.currentSession().subscribe({
          next: (res) => {
            supportSession.set(res.data.active ? res.data : null);
            this.isStarting.set(false);
            this.router.navigate(['/dashboard']);
          },
          error: () => this.isStarting.set(false),
        });
      },
      error: (err) => {
        this.isStarting.set(false);
        this.dialogs.showToast(apiError(err, 'Could not start this session.'), 'error', 5000);
      },
    });
  }

  async cancel(r: ImpersonationRequest): Promise<void> {
    if (
      !(await this.dialogs.confirm({
        title: 'Cancel request?',
        message: `${r.requestNumber} will be closed and cannot be started.`,
        confirmText: 'Cancel request',
      }))
    )
      return;
    this.service.cancelRequest(r.id).subscribe({
      next: () => {
        this.dialogs.showToast('Request cancelled.', 'success');
        this.load();
      },
      error: (err) =>
        this.dialogs.showToast(apiError(err, 'Could not cancel this request.'), 'error', 5000),
    });
  }
}
