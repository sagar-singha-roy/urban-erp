import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { PagedTab } from '../../paged-tab';
import { WlPaginationComponent } from '../../wl-pagination/wl-pagination.component';
import { DomainMapping, PageQuery, PagedResponse, RoutingStatus, TenantOption, WhiteLabelOptions } from '../../../../../../core/models/white-label.model';
import { MappingFormDialogComponent } from '../../dialogs/mapping-form-dialog/mapping-form-dialog.component';

@Component({
  selector: 'app-wl-mappings-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, MappingFormDialogComponent],
  templateUrl: './mappings-tab.component.html',
  styleUrl: './mappings-tab.component.scss',
})
export class MappingsTabComponent extends PagedTab<DomainMapping> {
  private service = inject(WhiteLabelService);
  readonly options = input.required<WhiteLabelOptions>();
  readonly tenants = input.required<TenantOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<DomainMapping | null>(null);
  readonly routing = signal<RoutingStatus | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<DomainMapping>> {
    this.service.getRoutingStatus().subscribe({ next: (res) => this.routing.set(res.data), error: () => this.routing.set(null) });
    return this.service.listMappings(query);
  }

  open(mapping: DomainMapping | null): void {
    this.selected.set(mapping);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }
}
