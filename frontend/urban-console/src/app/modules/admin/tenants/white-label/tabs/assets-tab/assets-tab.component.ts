import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { PagedTab } from '../../paged-tab';
import { WlPaginationComponent } from '../../wl-pagination/wl-pagination.component';
import { AssetSet, PageQuery, PagedResponse, TenantOption, WhiteLabelOptions } from '../../../../../../core/models/white-label.model';
import { AssetFormDialogComponent } from '../../dialogs/asset-form-dialog/asset-form-dialog.component';

@Component({
  selector: 'app-wl-assets-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, AssetFormDialogComponent],
  templateUrl: './assets-tab.component.html',
  styleUrl: './assets-tab.component.scss',
})
export class AssetsTabComponent extends PagedTab<AssetSet> {
  private service = inject(WhiteLabelService);
  readonly options = input.required<WhiteLabelOptions>();
  readonly tenants = input.required<TenantOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<AssetSet | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<AssetSet>> {
    return this.service.listAssets(query);
  }

  previewUrl(fileId: string): string {
    return this.service.assetPreviewUrl(fileId);
  }

  open(assets: AssetSet | null): void {
    this.selected.set(assets);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }
}
