import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { WhiteLabelService } from '../../../../../../core/services/white-label.service';
import { PagedTab } from '../../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../../shared/components/wl-pagination/wl-pagination.component';
import { PageQuery, PagedResponse, TenantCertificate, TenantOption, WhiteLabelOptions } from '../../../../../../core/models/white-label.model';
import { CertificateFormDialogComponent } from '../../dialogs/certificate-form-dialog/certificate-form-dialog.component';

@Component({
  selector: 'app-wl-certificates-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, CertificateFormDialogComponent],
  templateUrl: './certificates-tab.component.html',
  styleUrl: './certificates-tab.component.scss',
})
export class CertificatesTabComponent extends PagedTab<TenantCertificate> {
  private service = inject(WhiteLabelService);
  readonly options = input.required<WhiteLabelOptions>();
  readonly tenants = input.required<TenantOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<TenantCertificate | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<TenantCertificate>> {
    return this.service.listCertificates(query);
  }

  open(certificate: TenantCertificate | null): void {
    this.selected.set(certificate);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }
}
