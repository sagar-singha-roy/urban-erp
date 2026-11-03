import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { PagedTab } from '../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../shared/components/wl-pagination/wl-pagination.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { PageQuery, PagedResponse } from '../../../../../core/models/white-label.model';
import {
  HubProfile,
  ImpersonationOptions,
  SupportSession,
} from '../../../../../core/models/impersonation.model';
import { TerminateDialogComponent } from '../dialogs/terminate-dialog.component';
import { asUtc, grantStatusClass } from '../../cross-tenant-access/cross-tenant-utils';

/** Tab 3: support sessions. A session's status is checked on every request it makes. */
@Component({
  selector: 'app-imp-sessions-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, WlPaginationComponent, TerminateDialogComponent],
  template: `
    <div class="wl-toolbar">
      <input
        class="wl-search"
        type="search"
        placeholder="Search agents, users or tenants"
        aria-label="Search agents, users or tenants"
        [ngModel]="search()"
        (ngModelChange)="onSearch($event)"
      />
      <select
        class="filter"
        aria-label="Filter by session status"
        [ngModel]="status()"
        (ngModelChange)="setStatus($event)"
      >
        <option value="">All sessions</option>
        @for (s of options().sessionStatuses; track s) {
          <option [value]="s">{{ s }}</option>
        }
      </select>
    </div>
    <div class="wl-card">
      <div class="wl-scroll">
        <table class="wl-table">
          <thead>
            <tr>
              <th>Session ID</th>
              <th>Request ID</th>
              <th>Support Agent</th>
              <th>Target User</th>
              <th>Tenant Context</th>
              <th>Session Start</th>
              <th>Session Expiry</th>
              <th>Mode</th>
              <th>Status</th>
              <th>Termination Reason</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (s of items(); track s.id) {
              <tr>
                <td>{{ s.sessionNumber }}</td>
                <td>{{ s.requestNumber }}</td>
                <td>{{ s.supportEmail }}</td>
                <td>
                  {{ s.targetName }}<span class="wl-sub">{{ s.targetEmail }}</span>
                </td>
                <td>{{ s.tenantId }}</td>
                <td>{{ asUtc(s.startedAt) | date: 'medium' }}</td>
                <td>{{ asUtc(s.expiresAt) | date: 'medium' }}</td>
                <td>{{ s.accessMode }}</td>
                <td>
                  <span
                    class="wl-status"
                    [ngClass]="s.status === 'Active' ? 'warn' : statusClass2(s.status)"
                    >{{ s.status }}</span
                  >
                </td>
                <td class="clip">
                  {{ s.terminationReason ?? '' }}
                  @if (s.terminatedBy) {
                    <span class="wl-sub">by {{ s.terminatedBy }}</span>
                  }
                </td>
                <td>
                  <div class="wl-actions">
                    @if (
                      s.status === 'Active' && (me().isSuperAdmin || s.supportEmail === me().email)
                    ) {
                      <button type="button" class="wl-link" (click)="ending.set(s)">
                        Terminate
                      </button>
                    }
                  </div>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="11" class="wl-empty">
                  {{ isLoading() ? 'Loading...' : 'No support sessions yet.' }}
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
    @if (ending(); as s) {
      <app-imp-terminate-dialog
        [session]="s"
        (saved)="ending.set(null); load()"
        (closed)="ending.set(null)"
      ></app-imp-terminate-dialog>
    }
  `,
  styleUrl: '../hub.scss',
})
export class SessionsTabComponent extends PagedTab<SupportSession> {
  private service = inject(ImpersonationService);
  readonly options = input.required<ImpersonationOptions>();
  readonly me = input.required<HubProfile>();
  readonly status = signal('');
  readonly ending = signal<SupportSession | null>(null);
  readonly asUtc = asUtc;
  readonly statusClass2 = grantStatusClass;

  protected fetch(query: PageQuery): Observable<PagedResponse<SupportSession>> {
    return this.service.listSessions(query, this.status() || undefined);
  }

  setStatus(value: string): void {
    this.status.set(value);
    this.page.set(1);
    this.load();
  }
}
