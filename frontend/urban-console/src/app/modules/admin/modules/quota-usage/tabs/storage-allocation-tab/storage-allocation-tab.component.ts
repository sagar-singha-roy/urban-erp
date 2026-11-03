import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { PagedTab } from '../../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../../shared/components/wl-pagination/wl-pagination.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { PageQuery, PagedResponse, TenantOption } from '../../../../../../core/models/white-label.model';
import { StorageAllocation, QuotaOptions } from '../../../../../../core/models/quota.model';
import { StorageAllocationDialogComponent } from '../../dialogs/storage-allocation-dialog/storage-allocation-dialog.component';

@Component({
  selector: 'app-quota-storage-allocation-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, StorageAllocationDialogComponent],
  templateUrl: './storage-allocation-tab.component.html',
  styleUrl: './storage-allocation-tab.component.scss',
})
export class StorageAllocationTabComponent extends PagedTab<StorageAllocation> {
  private service = inject(QuotaService);
  readonly options = input.required<QuotaOptions>();
  readonly tenants = input.required<TenantOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<StorageAllocation | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<StorageAllocation>> {
    return this.service.listStorage(query);
  }

  open(record: StorageAllocation | null): void {
    this.selected.set(record);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }
}
