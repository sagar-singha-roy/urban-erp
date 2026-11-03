import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { PagedTab } from '../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../shared/components/wl-pagination/wl-pagination.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { PageQuery, PagedResponse, apiError } from '../../../../../core/models/white-label.model';
import { AuditEntry } from '../../../../../core/models/impersonation.model';
import { ActionsDialogComponent } from '../dialogs/actions-dialog.component';
import {
  asUtc,
  fromLocalInput,
  grantStatusClass,
} from '../../cross-tenant-access/cross-tenant-utils';

/** Tab 5: one row per session, with its approvals and recorded activity. A hash-chained copy sits in the audit vault. */
@Component({
  selector: 'app-imp-audit-tab',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent,
    WlPaginationComponent,
    ActionsDialogComponent,
  ],
  template: `
    <div class="wl-toolbar">
      <input
        class="wl-search"
        type="search"
        placeholder="Search agents, users, tenants or IP addresses"
        aria-label="Search agents, users, tenants or IP addresses"
        [ngModel]="search()"
        (ngModelChange)="onSearch($event)"
      />
      <input
        class="filter"
        type="date"
        aria-label="From date"
        [ngModel]="dateFrom()"
        (ngModelChange)="setDates($event, dateTo())"
      />
      <input
        class="filter"
        type="date"
        aria-label="To date"
        [ngModel]="dateTo()"
        (ngModelChange)="setDates(dateFrom(), $event)"
      />
      <button type="button" class="btn btn-outline" (click)="export()" [disabled]="isExporting()">
        <app-icon name="ri-download-2-line" [size]="16"></app-icon><span>Export CSV</span>
      </button>
    </div>
    <div class="wl-card">
      <div class="wl-scroll">
        <table class="wl-table">
          <thead>
            <tr>
              <th>Request ID</th>
              <th>Support Agent</th>
              <th>Target User</th>
              <th>Tenant</th>
              <th>Session ID</th>
              <th>Login Time</th>
              <th>Logout Time</th>
              <th>Actions Performed</th>
              <th>IP Address</th>
              <th>Device Information</th>
              <th>Approval Reference</th>
              <th>Termination Reason</th>
              <th>Audit Event ID</th>
            </tr>
          </thead>
          <tbody>
            @for (a of items(); track a.sessionId) {
              <tr>
                <td>{{ a.requestNumber }}</td>
                <td>{{ a.supportEmail }}</td>
                <td>{{ a.targetEmail }}</td>
                <td>{{ a.tenantId }}</td>
                <td>
                  {{ a.sessionNumber
                  }}<span class="wl-sub"
                    ><span
                      class="wl-status"
                      [ngClass]="a.status === 'Active' ? 'warn' : statusClass2(a.status)"
                      >{{ a.status }}</span
                    ></span
                  >
                </td>
                <td>{{ asUtc(a.loginTime) | date: 'medium' }}</td>
                <td>
                  {{ a.logoutTime ? (asUtc(a.logoutTime) | date: 'medium') : 'Still active' }}
                </td>
                <td>
                  <button
                    type="button"
                    class="wl-link"
                    (click)="viewing.set(a)"
                    [attr.aria-label]="
                      'View ' + a.actionsPerformed + ' actions for ' + a.sessionNumber
                    "
                  >
                    {{ a.actionsPerformed }} actions
                  </button>
                </td>
                <td>{{ a.ipAddress ?? '-' }}</td>
                <td class="clip">{{ a.device ?? '-' }}</td>
                <td class="clip">{{ a.approvalReference }}</td>
                <td class="clip">{{ a.terminationReason ?? '' }}</td>
                <td>{{ a.auditEventId ?? '-' }}</td>
              </tr>
            } @empty {
              <tr>
                <td colspan="13" class="wl-empty">
                  {{ isLoading() ? 'Loading...' : 'No support sessions match.' }}
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
    @if (viewing(); as entry) {
      <app-imp-actions-dialog [entry]="entry" (closed)="viewing.set(null)"></app-imp-actions-dialog>
    }
  `,
  styleUrl: '../hub.scss',
})
export class AuditTabComponent extends PagedTab<AuditEntry> {
  private service = inject(ImpersonationService);
  readonly dateFrom = signal('');
  readonly dateTo = signal('');
  readonly isExporting = signal(false);
  readonly viewing = signal<AuditEntry | null>(null);
  readonly asUtc = asUtc;
  readonly statusClass2 = grantStatusClass;

  private range(): [string | undefined, string | undefined] {
    return [
      this.dateFrom() ? (fromLocalInput(`${this.dateFrom()}T00:00`) ?? undefined) : undefined,
      this.dateTo() ? (fromLocalInput(`${this.dateTo()}T23:59`) ?? undefined) : undefined,
    ];
  }

  protected fetch(query: PageQuery): Observable<PagedResponse<AuditEntry>> {
    return this.service.listAudit(query, ...this.range());
  }

  setDates(from: string, to: string): void {
    this.dateFrom.set(from);
    this.dateTo.set(to);
    this.page.set(1);
    this.load();
  }

  export(): void {
    this.isExporting.set(true);
    this.service.exportAudit(this.search().trim(), ...this.range()).subscribe({
      next: (blob) => {
        this.isExporting.set(false);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'impersonation-audit.csv';
        link.click();
        URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.isExporting.set(false);
        this.dialogs.showToast(apiError(err, 'Could not export the audit log.'), 'error', 4000);
      },
    });
  }
}
