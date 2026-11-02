import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { CheckListComponent } from '../../../../../../shared/components/check-list/check-list.component';
import { PagedTab } from '../../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../../shared/components/wl-pagination/wl-pagination.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { PageQuery, PagedResponse, TenantOption } from '../../../../../../core/models/white-label.model';
import { QuotaOptions, StorageUsageFilters, StorageUsageRow, ThresholdLevel, formatBytes } from '../../../../../../core/models/quota.model';

@Component({
  selector: 'app-quota-storage-usage-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, WlPaginationComponent, CheckListComponent],
  templateUrl: './storage-usage-tab.component.html',
  styleUrl: './storage-usage-tab.component.scss',
})
export class StorageUsageTabComponent extends PagedTab<StorageUsageRow> {
  private service = inject(QuotaService);
  readonly options = input.required<QuotaOptions>();
  readonly tenants = input.required<TenantOption[]>();
  readonly levels = signal<ThresholdLevel[]>([]);
  readonly expanded = signal<string | null>(null);
  readonly formatBytes = formatBytes;

  filters: StorageUsageFilters = { modules: [] };

  override ngOnInit(): void {
    super.ngOnInit();
    this.service.getLevels().subscribe({ next: (res) => this.levels.set(res.data) });
  }

  get states(): TenantOption[] {
    return this.tenants().filter((t) => t.tenantLevel === 'State');
  }

  get ulbs(): TenantOption[] {
    return this.tenants().filter((t) => t.tenantLevel === 'ULB' && (!this.filters.stateTenantId || t.stateTenantId === this.filters.stateTenantId));
  }

  get moduleOptions(): { value: string; label: string }[] {
    return this.options().modules.map((m) => ({ value: m, label: m }));
  }

  protected fetch(query: PageQuery): Observable<PagedResponse<StorageUsageRow>> {
    return this.service.storageUsage(query, this.filters);
  }

  apply(): void {
    this.page.set(1);
    this.load();
  }

  clear(): void {
    this.filters = { modules: [] };
    this.apply();
  }

  moduleEntries(row: StorageUsageRow): [string, number][] {
    return Object.entries(row.moduleUsage);
  }

  usageClass(status: string): string {
    if (status === 'Normal') return 'good';
    if (status === 'Not Connected') return '';
    const highest = this.levels().at(-1)?.levelName;
    return status === highest ? 'bad' : 'warn';
  }
}
