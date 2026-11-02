import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { PagedTab } from '../../paged-tab';
import { WlPaginationComponent } from '../../wl-pagination/wl-pagination.component';
import { PageQuery, PagedResponse, TenantDomain, TenantOption, WhiteLabelOptions, apiError } from '../../../../../../core/models/white-label.model';
import { DomainFormDialogComponent } from '../../dialogs/domain-form-dialog/domain-form-dialog.component';

@Component({
  selector: 'app-wl-domains-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, DomainFormDialogComponent],
  templateUrl: './domains-tab.component.html',
  styleUrl: './domains-tab.component.scss',
})
export class DomainsTabComponent extends PagedTab<TenantDomain> {
  private service = inject(WhiteLabelService);
  readonly options = input.required<WhiteLabelOptions>();
  readonly tenants = input.required<TenantOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<TenantDomain | null>(null);
  readonly verifyingId = signal<string | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<TenantDomain>> {
    return this.service.listDomains(query);
  }

  open(domain: TenantDomain | null): void {
    this.selected.set(domain);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }

  verify(domain: TenantDomain): void {
    this.verifyingId.set(domain.id);
    this.service.verifyDomain(domain.id).subscribe({
      next: (res) => {
        this.verifyingId.set(null);
        const verified = res.data.verificationStatus === 'Verified';
        this.dialogs.showToast(res.data.lastCheckMessage || res.data.verificationStatus, verified ? 'success' : 'warning', 4000);
        this.load();
      },
      error: (err) => {
        this.verifyingId.set(null);
        this.dialogs.showToast(apiError(err, 'Verification could not run.'), 'error', 4000);
      },
    });
  }
}
