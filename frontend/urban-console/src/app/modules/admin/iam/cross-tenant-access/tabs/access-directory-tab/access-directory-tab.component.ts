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
import {
  AccessGrant,
  CrossTenantOptions,
  GrantFilters,
  UserOption,
} from '../../../../../../core/models/cross-tenant.model';
import { GrantDialogComponent } from '../../dialogs/grant-dialog/grant-dialog.component';
import {
  GrantDecisionDialogComponent,
  GrantDecisionMode,
} from '../../dialogs/grant-decision-dialog/grant-decision-dialog.component';
import { asUtc, grantStatusClass, tenantName } from '../../cross-tenant-utils';

/** Tab 1: every cross-tenant access record, with approval and revocation. */
@Component({
  selector: 'app-xt-access-directory-tab',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent,
    WlPaginationComponent,
    GrantDialogComponent,
    GrantDecisionDialogComponent,
  ],
  templateUrl: './access-directory-tab.component.html',
  styleUrl: '../tab.scss',
})
export class AccessDirectoryTabComponent extends PagedTab<AccessGrant> {
  private service = inject(CrossTenantService);
  readonly options = input.required<CrossTenantOptions>();
  readonly tenants = input.required<TenantOption[]>();
  readonly authorities = input.required<UserOption[]>();

  readonly filters = signal<GrantFilters>({});
  readonly editing = signal<AccessGrant | null | undefined>(undefined);
  readonly deciding = signal<{ grant: AccessGrant; mode: GrantDecisionMode } | null>(null);
  readonly asUtc = asUtc;
  readonly statusClass2 = grantStatusClass;

  protected fetch(query: PageQuery): Observable<PagedResponse<AccessGrant>> {
    return this.service.listGrants(query, this.filters());
  }

  tenantName(id: string): string {
    return tenantName(this.tenants(), id);
  }

  setFilter(key: keyof GrantFilters, value: string): void {
    this.filters.update((f) => ({ ...f, [key]: value || undefined }));
    this.page.set(1);
    this.load();
  }

  onSaved(): void {
    this.editing.set(undefined);
    this.deciding.set(null);
    this.load();
  }
}
