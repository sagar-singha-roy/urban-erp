import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { PagedTab } from '../../paged-tab';
import { WlPaginationComponent } from '../../wl-pagination/wl-pagination.component';
import { BrandingProfile, PageQuery, PagedResponse, TenantOption, WhiteLabelOptions } from '../../../../../../core/models/white-label.model';
import { BrandingFormDialogComponent } from '../../dialogs/branding-form-dialog/branding-form-dialog.component';

@Component({
  selector: 'app-wl-branding-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, BrandingFormDialogComponent],
  templateUrl: './branding-tab.component.html',
  styleUrl: './branding-tab.component.scss',
})
export class BrandingTabComponent extends PagedTab<BrandingProfile> {
  private service = inject(WhiteLabelService);
  readonly options = input.required<WhiteLabelOptions>();
  readonly tenants = input.required<TenantOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<BrandingProfile | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<BrandingProfile>> {
    return this.service.listBranding(query);
  }

  open(profile: BrandingProfile | null): void {
    this.selected.set(profile);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }
}
