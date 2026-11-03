import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { PagedTab } from '../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../shared/components/wl-pagination/wl-pagination.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { PageQuery, PagedResponse } from '../../../../../core/models/white-label.model';
import {
  ImpersonationOptions,
  ImpersonationPolicy,
} from '../../../../../core/models/impersonation.model';
import { PolicyDialogComponent } from '../dialogs/policy-dialog.component';

/** Tab 4: impersonation policies. One active policy covers each tenant level. */
@Component({
  selector: 'app-imp-policy-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, PolicyDialogComponent],
  template: `
    <div class="wl-toolbar">
      <input
        class="wl-search"
        type="search"
        placeholder="Search policies"
        aria-label="Search policies"
        [ngModel]="search()"
        (ngModelChange)="onSearch($event)"
      />
      <button type="button" class="btn btn-primary" (click)="editing.set(null)">
        <app-icon name="ri-add-line" [size]="16"></app-icon><span>New Policy</span>
      </button>
    </div>
    <div class="wl-card">
      <div class="wl-scroll">
        <table class="wl-table">
          <thead>
            <tr>
              <th>Policy</th>
              <th>Support Roles</th>
              <th>Tenant Levels</th>
              <th>Max Session</th>
              <th>Approval</th>
              <th>Controls</th>
              <th>Write Actions</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (p of items(); track p.id) {
              <tr>
                <td>
                  {{ p.policyName }}<span class="wl-sub">{{ p.policyCode }}</span>
                </td>
                <td class="clip">{{ roleNames(p.allowedSupportRoles) }}</td>
                <td>{{ p.allowedTenantLevels.join(', ') }}</td>
                <td>{{ p.maxSessionMinutes }} min</td>
                <td>{{ p.approvalRequired ? (p.dualApproval ? 'Dual' : 'Single') : 'None' }}</td>
                <td class="clip">{{ controls(p) }}</td>
                <td class="clip">{{ p.writeActionsAllowed.join(', ') || 'Read only' }}</td>
                <td>
                  <span class="wl-status" [ngClass]="p.isActive ? 'good' : ''">{{
                    p.isActive ? 'Active' : 'Inactive'
                  }}</span>
                </td>
                <td>
                  <div class="wl-actions">
                    <button type="button" class="wl-link" (click)="editing.set(p)">Edit</button>
                  </div>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="9" class="wl-empty">
                  {{
                    isLoading()
                      ? 'Loading...'
                      : 'No policies yet. Nobody can impersonate until one is active.'
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
      <app-imp-policy-dialog
        [record]="editing() ?? null"
        [options]="options()"
        (saved)="editing.set(undefined); load()"
        (closed)="editing.set(undefined)"
      ></app-imp-policy-dialog>
    }
  `,
  styleUrl: '../hub.scss',
})
export class PolicyTabComponent extends PagedTab<ImpersonationPolicy> {
  private service = inject(ImpersonationService);
  readonly options = input.required<ImpersonationOptions>();
  readonly editing = signal<ImpersonationPolicy | null | undefined>(undefined);

  protected fetch(query: PageQuery): Observable<PagedResponse<ImpersonationPolicy>> {
    return this.service.listPolicies(query);
  }

  roleNames(codes: string[]): string {
    return codes.map((c) => this.options().roles.find((r) => r.code === c)?.name ?? c).join(', ');
  }

  controls(p: ImpersonationPolicy): string {
    const parts = [
      p.readOnlyDefault ? 'Read-only default' : '',
      p.maskSensitiveData ? 'Masking' : '',
      p.downloadDisabled ? 'No downloads' : '',
      p.sessionRecording ? 'Recording' : '',
    ];
    return parts.filter(Boolean).join(', ') || 'None';
  }
}
