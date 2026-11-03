import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { PagedTab } from '../../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../../shared/components/wl-pagination/wl-pagination.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { PageQuery, PagedResponse, TenantOption } from '../../../../../../core/models/white-label.model';
import { ApiPolicy, QuotaOptions } from '../../../../../../core/models/quota.model';
import { ApiPolicyDialogComponent } from '../../dialogs/api-policy-dialog/api-policy-dialog.component';

@Component({
  selector: 'app-quota-api-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, ApiPolicyDialogComponent],
  templateUrl: './api-tab.component.html',
  styleUrl: './api-tab.component.scss',
})
export class ApiTabComponent extends PagedTab<ApiPolicy> {
  private service = inject(QuotaService);
  readonly options = input.required<QuotaOptions>();
  readonly tenants = input.required<TenantOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<ApiPolicy | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<ApiPolicy>> {
    return this.service.listPolicies(query);
  }

  open(record: ApiPolicy | null): void {
    this.selected.set(record);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }
}
