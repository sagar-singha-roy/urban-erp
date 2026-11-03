import { Component, OnInit, inject, signal, viewChild } from '@angular/core';
import { forkJoin } from 'rxjs';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { CrossTenantService } from '../../../../core/services/cross-tenant.service';
import { WhiteLabelService } from '../../../../core/services/white-label.service';
import { DialogService } from '../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../core/models/white-label.model';
import { CrossTenantOptions, UserOption } from '../../../../core/models/cross-tenant.model';
import { AccessDirectoryTabComponent } from './tabs/access-directory-tab/access-directory-tab.component';
import { ScopeConfigTabComponent } from './tabs/scope-config-tab/scope-config-tab.component';
import { PermissionReviewTabComponent } from './tabs/permission-review-tab/permission-review-tab.component';
import { AccessCertificationTabComponent } from './tabs/access-certification-tab/access-certification-tab.component';
import { AccessHistoryTabComponent } from './tabs/access-history-tab/access-history-tab.component';

type TabId = 'directory' | 'scope' | 'permissions' | 'certification' | 'history';

/** ADM-R02 Cross-Tenant Access Management. */
@Component({
  selector: 'app-cross-tenant-access',
  standalone: true,
  imports: [
    IconComponent,
    RefreshButtonComponent,
    AccessDirectoryTabComponent,
    ScopeConfigTabComponent,
    PermissionReviewTabComponent,
    AccessCertificationTabComponent,
    AccessHistoryTabComponent,
  ],
  templateUrl: './cross-tenant-access.component.html',
  styleUrl: './cross-tenant-access.component.scss',
})
export class CrossTenantAccessComponent implements OnInit {
  private service = inject(CrossTenantService);
  private whiteLabel = inject(WhiteLabelService);
  private dialogs = inject(DialogService);

  readonly tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'directory', label: 'Access Directory', icon: 'ri-shield-user-line' },
    { id: 'scope', label: 'Tenant Scope', icon: 'ri-node-tree' },
    { id: 'permissions', label: 'Permission Review', icon: 'ri-lock-2-line' },
    { id: 'certification', label: 'Review & Certification', icon: 'ri-checkbox-multiple-line' },
    { id: 'history', label: 'History & Audit', icon: 'ri-history-line' },
  ];
  readonly activeTab = signal<TabId>('directory');
  readonly options = signal<CrossTenantOptions | null>(null);
  readonly tenants = signal<TenantOption[]>([]);
  readonly authorities = signal<UserOption[]>([]);

  private directory = viewChild(AccessDirectoryTabComponent);
  private scope = viewChild(ScopeConfigTabComponent);
  private permissions = viewChild(PermissionReviewTabComponent);
  private certification = viewChild(AccessCertificationTabComponent);
  private history = viewChild(AccessHistoryTabComponent);

  ngOnInit(): void {
    this.loadReferenceData();
  }

  loadReferenceData(): void {
    forkJoin({
      options: this.service.getOptions(),
      tenants: this.whiteLabel.getTenants(),
      authorities: this.service.getAuthorities(),
    }).subscribe({
      next: ({ options, tenants, authorities }) => {
        this.options.set(options.data);
        this.tenants.set(tenants.data);
        this.authorities.set(authorities.data);
      },
      error: (err) =>
        this.dialogs.showToast(apiError(err, 'Could not load this page.'), 'error', 4000),
    });
  }

  refresh(): void {
    this.loadReferenceData();
    (
      this.directory() ??
      this.scope() ??
      this.permissions() ??
      this.certification() ??
      this.history()
    )?.load();
  }
}
