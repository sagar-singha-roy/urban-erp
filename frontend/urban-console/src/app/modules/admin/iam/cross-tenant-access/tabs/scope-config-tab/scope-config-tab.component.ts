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
} from '../../../../../../core/models/white-label.model';
import { AccessScope, CrossTenantOptions } from '../../../../../../core/models/cross-tenant.model';
import { ScopeDialogComponent } from '../../dialogs/scope-dialog/scope-dialog.component';
import { asUtc, tenantName } from '../../cross-tenant-utils';

/** Tab 2: the scope set on each access record. */
@Component({
  selector: 'app-xt-scope-config-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, ScopeDialogComponent],
  template: `
    <div class="wl-toolbar">
      <input
        class="wl-search"
        type="search"
        placeholder="Search users, states or scope levels"
        aria-label="Search users, states or scope levels"
        [ngModel]="search()"
        (ngModelChange)="onSearch($event)"
      />
      <button type="button" class="btn btn-primary" (click)="editing.set(null)">
        <app-icon name="ri-node-tree" [size]="16"></app-icon><span>Configure Scope</span>
      </button>
    </div>
    <div class="wl-card">
      <div class="wl-scroll">
        <table class="wl-table">
          <thead>
            <tr>
              <th>Record ID</th>
              <th>User</th>
              <th>Access Scope</th>
              <th>State</th>
              <th>ULB / City</th>
              <th>Areas</th>
              <th>Scope Mode</th>
              <th>Child Tenants</th>
              <th>Restrictions</th>
              <th>Effective</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (s of items(); track s.id) {
              <tr>
                <td>{{ s.recordNumber }}</td>
                <td>
                  {{ s.userName }}<span class="wl-sub">{{ s.userEmail }}</span>
                </td>
                <td>{{ s.accessScope }}</td>
                <td>{{ tenantName(s.stateTenantId) }}</td>
                <td class="clip">
                  {{ s.ulbTenantIds.length ? names(s.ulbTenantIds) : 'All reached' }}
                </td>
                <td>
                  {{ s.departmentIds.length }} departments<span class="wl-sub"
                    >{{ s.zoneIds.length }} zones, {{ s.wardIds.length }} wards</span
                  >
                </td>
                <td>{{ s.scopeMode }}</td>
                <td>{{ s.includeChildTenants ? 'Included' : 'Excluded' }}</td>
                <td class="clip">{{ s.restrictedComponents.join(', ') || 'None' }}</td>
                <td>
                  {{ asUtc(s.effectiveDate) | date: 'mediumDate'
                  }}<span class="wl-sub">{{
                    s.expiryDate
                      ? 'expires ' + (asUtc(s.expiryDate) | date: 'mediumDate')
                      : 'No expiry'
                  }}</span>
                </td>
                <td>
                  <div class="wl-actions">
                    <button type="button" class="wl-link" (click)="editing.set(s)">Edit</button>
                  </div>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="11" class="wl-empty">
                  {{
                    isLoading()
                      ? 'Loading...'
                      : 'No scopes yet. Without one, access covers the whole target tenant.'
                  }}
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
      <app-xt-scope-dialog
        [record]="editing() ?? null"
        [options]="options()"
        [tenants]="tenants()"
        (saved)="onSaved()"
        (closed)="editing.set(undefined)"
      ></app-xt-scope-dialog>
    }
  `,
  styleUrl: '../tab.scss',
})
export class ScopeConfigTabComponent extends PagedTab<AccessScope> {
  private service = inject(CrossTenantService);
  readonly options = input.required<CrossTenantOptions>();
  readonly tenants = input.required<TenantOption[]>();
  readonly editing = signal<AccessScope | null | undefined>(undefined);
  readonly asUtc = asUtc;

  protected fetch(query: PageQuery): Observable<PagedResponse<AccessScope>> {
    return this.service.listScopes(query);
  }

  tenantName(id: string): string {
    return tenantName(this.tenants(), id);
  }

  names(ids: string[]): string {
    return ids.map((id) => this.tenantName(id)).join(', ');
  }

  onSaved(): void {
    this.editing.set(undefined);
    this.load();
  }
}
