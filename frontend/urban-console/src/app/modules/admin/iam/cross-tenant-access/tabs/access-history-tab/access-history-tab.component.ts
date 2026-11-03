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
  HistoryEntry,
  HistoryFilters,
  actionLabel,
} from '../../../../../../core/models/cross-tenant.model';
import { asUtc, fromLocalInput, tenantName } from '../../cross-tenant-utils';

/** Tab 5: every change to cross-tenant access. A hash-chained copy is kept in the audit vault. */
@Component({
  selector: 'app-xt-access-history-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent],
  template: `
    <div class="wl-toolbar">
      <input
        class="wl-search"
        type="search"
        placeholder="Search users, changed by, tenants or references"
        aria-label="Search users, changed by, tenants or references"
        [ngModel]="search()"
        (ngModelChange)="onSearch($event)"
      />
      <select
        class="filter"
        aria-label="Filter by action"
        [ngModel]="action()"
        (ngModelChange)="setAction($event)"
      >
        <option value="">All actions</option>
        @for (a of actions(); track a) {
          <option [value]="a">{{ label(a) }}</option>
        }
      </select>
      <input
        class="filter filter-date"
        type="date"
        aria-label="From date"
        [ngModel]="dateFrom()"
        (ngModelChange)="setDates($event, dateTo())"
      />
      <input
        class="filter filter-date"
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
              <th>Timestamp</th>
              <th>User</th>
              <th>Home Tenant</th>
              <th>Target Tenant</th>
              <th>Previous Access Level</th>
              <th>New Access Level</th>
              <th>Previous Scope</th>
              <th>New Scope</th>
              <th>Action Performed</th>
              <th>Changed By</th>
              <th>IP Address</th>
              <th>Reason</th>
              <th>Approval Reference</th>
            </tr>
          </thead>
          <tbody>
            @for (h of items(); track h.id) {
              <tr>
                <td>{{ asUtc(h.createdAt) | date: 'medium' }}</td>
                <td>{{ h.userEmail }}</td>
                <td>{{ tenantName(h.homeTenantId) }}</td>
                <td class="clip">{{ names(h.targetTenantIds) }}</td>
                <td>{{ h.previousAccessLevel ?? '-' }}</td>
                <td>{{ h.newAccessLevel ?? '-' }}</td>
                <td class="clip">{{ h.previousScope ?? '-' }}</td>
                <td class="clip">{{ h.newScope ?? '-' }}</td>
                <td>{{ label(h.action) }}</td>
                <td>{{ h.changedBy }}</td>
                <td>{{ h.ipAddress ?? '-' }}</td>
                <td class="clip">{{ h.reason ?? '' }}</td>
                <td>{{ h.approvalReference ?? '-' }}</td>
              </tr>
            } @empty {
              <tr>
                <td colspan="13" class="wl-empty">
                  {{ isLoading() ? 'Loading...' : 'No access changes match.' }}
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
  `,
  styleUrl: '../tab.scss',
})
export class AccessHistoryTabComponent extends PagedTab<HistoryEntry> {
  private service = inject(CrossTenantService);
  readonly tenants = input.required<TenantOption[]>();
  readonly asUtc = asUtc;
  readonly label = actionLabel;

  readonly actions = signal<string[]>([]);
  readonly action = signal('');
  readonly dateFrom = signal('');
  readonly dateTo = signal('');
  readonly isExporting = signal(false);

  override ngOnInit(): void {
    super.ngOnInit();
    this.service.getHistoryActions().subscribe({ next: (res) => this.actions.set(res.data) });
  }

  private filters(): HistoryFilters {
    return {
      action: this.action() || undefined,
      dateFrom: this.dateFrom()
        ? (fromLocalInput(`${this.dateFrom()}T00:00`) ?? undefined)
        : undefined,
      dateTo: this.dateTo() ? (fromLocalInput(`${this.dateTo()}T23:59`) ?? undefined) : undefined,
    };
  }

  protected fetch(query: PageQuery): Observable<PagedResponse<HistoryEntry>> {
    return this.service.listHistory(query, this.filters());
  }

  tenantName(id: string | null): string {
    return tenantName(this.tenants(), id);
  }

  names(ids: string[]): string {
    return ids.map((id) => this.tenantName(id)).join(', ');
  }

  setAction(value: string): void {
    this.action.set(value);
    this.page.set(1);
    this.load();
  }

  setDates(from: string, to: string): void {
    this.dateFrom.set(from);
    this.dateTo.set(to);
    this.page.set(1);
    this.load();
  }

  export(): void {
    this.isExporting.set(true);
    this.service.exportHistory(this.search().trim(), this.filters()).subscribe({
      next: (blob) => {
        this.isExporting.set(false);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'cross-tenant-access-history.csv';
        link.click();
        URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.isExporting.set(false);
        this.dialogs.showToast(apiError(err, 'Could not export the history.'), 'error', 4000);
      },
    });
  }
}
