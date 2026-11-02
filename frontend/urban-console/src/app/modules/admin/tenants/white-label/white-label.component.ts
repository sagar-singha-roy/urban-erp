import { Component, OnInit, inject, signal, viewChild } from '@angular/core';
import { forkJoin } from 'rxjs';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { WhiteLabelService } from '../../../../core/services/white-label.service';
import { DialogService } from '../../../../core/services/dialog.service';
import { TenantOption, WhiteLabelOptions, apiError } from '../../../../core/models/white-label.model';
import { BrandingTabComponent } from './tabs/branding-tab/branding-tab.component';
import { AssetsTabComponent } from './tabs/assets-tab/assets-tab.component';
import { DomainsTabComponent } from './tabs/domains-tab/domains-tab.component';
import { CertificatesTabComponent } from './tabs/certificates-tab/certificates-tab.component';
import { MappingsTabComponent } from './tabs/mappings-tab/mappings-tab.component';

type TabId = 'branding' | 'assets' | 'domains' | 'certificates' | 'mappings';

@Component({
  selector: 'app-white-label',
  standalone: true,
  imports: [IconComponent, RefreshButtonComponent, BrandingTabComponent, AssetsTabComponent, DomainsTabComponent, CertificatesTabComponent, MappingsTabComponent],
  templateUrl: './white-label.component.html',
  styleUrl: './white-label.component.scss',
})
export class WhiteLabelComponent implements OnInit {
  private service = inject(WhiteLabelService);
  private dialogs = inject(DialogService);

  readonly tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'branding', label: 'Branding Configuration', icon: 'ri-palette-line' },
    { id: 'assets', label: 'Logo & Emblem', icon: 'ri-image-line' },
    { id: 'domains', label: 'Custom Domain', icon: 'ri-global-line' },
    { id: 'certificates', label: 'SSL Certificate', icon: 'ri-lock-2-line' },
    { id: 'mappings', label: 'Domain Mapping', icon: 'ri-route-line' },
  ];
  readonly activeTab = signal<TabId>('branding');
  readonly options = signal<WhiteLabelOptions | null>(null);
  readonly tenants = signal<TenantOption[]>([]);

  private branding = viewChild(BrandingTabComponent);
  private assets = viewChild(AssetsTabComponent);
  private domains = viewChild(DomainsTabComponent);
  private certificates = viewChild(CertificatesTabComponent);
  private mappings = viewChild(MappingsTabComponent);

  ngOnInit(): void {
    this.loadReferenceData();
  }

  loadReferenceData(): void {
    forkJoin({ options: this.service.getOptions(), tenants: this.service.getTenants() }).subscribe({
      next: ({ options, tenants }) => {
        this.options.set(options.data);
        this.tenants.set(tenants.data);
      },
      error: (err) => this.dialogs.showToast(apiError(err, 'Could not load this page.'), 'error', 4000),
    });
  }

  refresh(): void {
    this.loadReferenceData();
    (this.branding() ?? this.assets() ?? this.domains() ?? this.certificates() ?? this.mappings())?.load();
  }
}
