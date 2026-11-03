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
  CrossTenantOptions,
  ReviewCampaign,
  ReviewItem,
  UserOption,
} from '../../../../../../core/models/cross-tenant.model';
import { CampaignDialogComponent } from '../../dialogs/campaign-dialog/campaign-dialog.component';
import { ReviewDecisionDialogComponent } from '../../dialogs/review-decision-dialog/review-decision-dialog.component';
import { asUtc, grantStatusClass, tenantName } from '../../cross-tenant-utils';

const SEARCH_DELAY_MS = 300;

/** Tab 4: certification campaigns, and the review owner's decision on each access record in one. */
@Component({
  selector: 'app-xt-access-certification-tab',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent,
    WlPaginationComponent,
    CampaignDialogComponent,
    ReviewDecisionDialogComponent,
  ],
  templateUrl: './access-certification-tab.component.html',
  styleUrl: '../tab.scss',
})
export class AccessCertificationTabComponent extends PagedTab<ReviewCampaign> {
  private service = inject(CrossTenantService);
  readonly options = input.required<CrossTenantOptions>();
  readonly tenants = input.required<TenantOption[]>();
  readonly authorities = input.required<UserOption[]>();
  readonly asUtc = asUtc;
  readonly statusClass2 = grantStatusClass;

  readonly isCreating = signal(false);
  readonly campaign = signal<ReviewCampaign | null>(null);
  readonly reviewItems = signal<ReviewItem[]>([]);
  readonly itemTotal = signal(0);
  readonly itemPage = signal(1);
  readonly itemLimit = signal(10);
  readonly itemSearch = signal('');
  readonly deciding = signal<ReviewItem | null>(null);
  private itemTimer?: ReturnType<typeof setTimeout>;

  protected fetch(query: PageQuery): Observable<PagedResponse<ReviewCampaign>> {
    return this.service.listCampaigns(query);
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    clearTimeout(this.itemTimer);
  }

  tenantName(id: string): string {
    return tenantName(this.tenants(), id);
  }

  names(ids: string[]): string {
    return ids.map((id) => this.tenantName(id)).join(', ');
  }

  open(campaign: ReviewCampaign): void {
    this.campaign.set(campaign);
    this.itemPage.set(1);
    this.itemSearch.set('');
    this.loadItems();
  }

  loadItems(): void {
    const campaign = this.campaign();
    if (!campaign) return;
    this.service
      .listItems(campaign.id, {
        search: this.itemSearch().trim() || undefined,
        skip: (this.itemPage() - 1) * this.itemLimit(),
        limit: this.itemLimit(),
      })
      .subscribe({
        next: (res) => {
          this.reviewItems.set(res.data);
          this.itemTotal.set(res.total);
        },
        error: (err) =>
          this.dialogs.showToast(apiError(err, 'Could not load the review items.'), 'error', 4000),
      });
  }

  onItemSearch(value: string): void {
    this.itemSearch.set(value);
    clearTimeout(this.itemTimer);
    this.itemTimer = setTimeout(() => {
      this.itemPage.set(1);
      this.loadItems();
    }, SEARCH_DELAY_MS);
  }

  onItemPage(page: number): void {
    this.itemPage.set(page);
    this.loadItems();
  }

  onItemLimit(limit: number): void {
    this.itemLimit.set(limit);
    this.itemPage.set(1);
    this.loadItems();
  }

  onCreated(): void {
    this.isCreating.set(false);
    this.load();
  }

  /** A decision can finish the campaign, so the campaign row is refreshed from the reloaded list. */
  onDecided(): void {
    this.deciding.set(null);
    this.loadItems();
    const current = this.campaign();
    this.isLoading.set(true);
    this.fetch({
      search: this.search().trim() || undefined,
      skip: (this.page() - 1) * this.limit(),
      limit: this.limit(),
    }).subscribe({
      next: (res) => {
        this.items.set(res.data);
        this.total.set(res.total);
        this.isLoading.set(false);
        this.campaign.set(res.data.find((c) => c.id === current?.id) ?? current);
      },
      error: () => this.isLoading.set(false),
    });
  }
}
