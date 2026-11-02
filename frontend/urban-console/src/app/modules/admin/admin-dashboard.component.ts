import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { TenantManagementComponent } from './tenants/tenant-management.component';
import { UlbManagementComponent } from './ulbs/ulb-management.component';
import { TenantLifecycleComponent } from './tenants/tenant-lifecycle/tenant-lifecycle.component';
import { WhiteLabelComponent } from './tenants/white-label/white-label.component';
import { QuotaUsageComponent } from './modules/quota-usage/quota-usage.component';
import { ModuleCatalogueComponent } from './modules/module-catalogue/module-catalogue.component';
import { ComponentRegistryComponent } from './modules/component-registry/component-registry.component';
import { ActionDependencyRegistryComponent } from './modules/action-dependency-registry/action-dependency-registry.component';
import { StateSubscriptionAllocatorComponent } from './modules/state-subscription-allocator/state-subscription-allocator.component';
import { CascadeDelegationComponent } from './modules/cascade-delegation/cascade-delegation.component';
import { SsoConfigComponent } from './iam/sso-config/sso-config.component';
import { IdentityFederationComponent } from './iam/identity-federation/identity-federation.component';
import { MfaSessionPolicyComponent } from './iam/mfa-session-policy/mfa-session-policy.component';
import { RolesMatrixComponent } from './iam/roles-matrix/roles-matrix.component';
import { UserManagementComponent } from './iam/user-management/user-management.component';
import { RlsPoliciesComponent } from './security/rls-policies/rls-policies.component';
import { IsolationTestsComponent } from './security/isolation-tests/isolation-tests.component';
import { IsolationFindingsComponent } from './security/isolation-findings/isolation-findings.component';
import { AuditVaultComponent } from './compliance/audit-vault/audit-vault.component';
import { MicroservicesComponent } from './fleet/microservices/microservices.component';
import { BackupDrComponent } from './fleet/backup-dr/backup-dr.component';
import { GlobalCommandDashboardComponent } from './executive/global-command-dashboard/global-command-dashboard.component';
import { BenchmarkingMatrixComponent } from './executive/benchmarking-matrix/benchmarking-matrix.component';
import { GisViewerComponent } from './executive/gis-viewer/gis-viewer.component';
import { FinancialLedgerComponent } from './executive/financial-ledger/financial-ledger.component';
import { SUPER_ADMIN_SECTIONS, SuperAdminSection } from '../../core/models/super-admin.model';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TenantManagementComponent,
    UlbManagementComponent,
    TenantLifecycleComponent,
    WhiteLabelComponent,
    QuotaUsageComponent,
    ModuleCatalogueComponent,
    ComponentRegistryComponent,
    ActionDependencyRegistryComponent,
    StateSubscriptionAllocatorComponent,
    CascadeDelegationComponent,
    SsoConfigComponent,
    IdentityFederationComponent,
    MfaSessionPolicyComponent,
    RolesMatrixComponent,
    UserManagementComponent,
    RlsPoliciesComponent,
    IsolationTestsComponent,
    IsolationFindingsComponent,
    AuditVaultComponent,
    MicroservicesComponent,
    BackupDrComponent,
    GlobalCommandDashboardComponent,
    BenchmarkingMatrixComponent,
    FinancialLedgerComponent,
    GisViewerComponent,
  ],
  templateUrl: './admin-dashboard.component.html',
  styleUrl: './admin-dashboard.component.scss',
})
export class AdminDashboardComponent implements OnInit {
  private route = inject(ActivatedRoute);

  readonly sections: SuperAdminSection[] = SUPER_ADMIN_SECTIONS;
  readonly activeSection = signal<string>('executive');
  readonly activeItemId = signal<string>('EXEC-01');
  readonly selectedModuleForComponentRegistry = signal<string>('ALL');

  ngOnInit(): void {
    this.route.queryParams.subscribe((params) => {
      if (params['section']) {
        this.activeSection.set(params['section']);
      }
      if (params['item']) {
        this.activeItemId.set(params['item']);
      }
    });

    this.route.params.subscribe((params) => {
      const section = params['section'];
      const sub = params['sub'];
      if (section) {
        this.activeSection.set(section);
      }
      if (sub) {
        const subMap: Record<string, { section: string; item: string }> = {
          'dashboard': { section: 'executive', item: 'EXEC-01' },
          'benchmarking': { section: 'executive', item: 'EXEC-02' },
          'ledger': { section: 'executive', item: 'EXEC-03' },
          'gis': { section: 'executive', item: 'EXEC-04' },
          'command': { section: 'executive', item: 'EXEC-01' },
          'global-command': { section: 'executive', item: 'EXEC-01' },
          'executive': { section: 'executive', item: 'EXEC-01' },
          'tenants': { section: 'tenancy', item: 'TH-01' },
          'state-tenants': { section: 'tenancy', item: 'TH-01' },
          'cities': { section: 'tenancy', item: 'TH-02' },
          'ulbs': { section: 'tenancy', item: 'TH-02' },
          'lifecycle': { section: 'tenancy', item: 'TH-03' },
          'tenant-lifecycle': { section: 'tenancy', item: 'TH-03' },
          'white-label': { section: 'tenancy', item: 'TH-04' },
          'domains': { section: 'tenancy', item: 'TH-04' },
          'catalogue': { section: 'modules', item: 'MS-01' },
          'components': { section: 'modules', item: 'MS-02' },
          'dependencies': { section: 'modules', item: 'MS-03' },
          'subscriptions': { section: 'modules', item: 'MS-04' },
          'state-subscriptions': { section: 'modules', item: 'MS-04' },
          'delegation': { section: 'modules', item: 'MS-05' },
          'cascade-delegation': { section: 'modules', item: 'MS-05' },
          'quotas': { section: 'modules', item: 'MS-06' },
          'quota-usage': { section: 'modules', item: 'MS-06' },
          'idp-sso': { section: 'iam-sso', item: 'IAM-01' },
          'sso': { section: 'iam-sso', item: 'IAM-01' },
          'federation': { section: 'iam-sso', item: 'IAM-02' },
          'mfa-policy': { section: 'iam-sso', item: 'IAM-03' },
          'mfa': { section: 'iam-sso', item: 'IAM-03' },
          'roles-matrix': { section: 'iam-rbac', item: 'IAM-04' },
          'roles': { section: 'iam-rbac', item: 'IAM-04' },
          'role-templates': { section: 'iam-rbac', item: 'IAM-05' },
          'templates': { section: 'iam-rbac', item: 'IAM-05' },
          'effective-permissions': { section: 'iam-rbac', item: 'IAM-06' },
          'users': { section: 'iam-users', item: 'IAM-07' },
          'invitations': { section: 'iam-users', item: 'IAM-08' },
          'access-scope': { section: 'iam-users', item: 'IAM-09' },
          'rls-policies': { section: 'security', item: 'SEC-01' },
          'rls': { section: 'security', item: 'SEC-01' },
          'isolation-tests': { section: 'security', item: 'SEC-02' },
          'tests': { section: 'security', item: 'SEC-02' },
          'reports': { section: 'security', item: 'SEC-03' },
          'findings': { section: 'security', item: 'SEC-03' },
          'audit-vault': { section: 'compliance', item: 'COMP-01' },
          'audit': { section: 'compliance', item: 'COMP-01' },
          'vault': { section: 'compliance', item: 'COMP-01' },
          'compliance': { section: 'compliance', item: 'COMP-01' },
          'microservices': { section: 'fleet', item: 'FLEET-01' },
          'fleet': { section: 'fleet', item: 'FLEET-01' },
          'cluster': { section: 'fleet', item: 'FLEET-01' },
          'health': { section: 'fleet', item: 'FLEET-01' },
          'backup-dr': { section: 'fleet', item: 'FLEET-02' },
          'backups': { section: 'fleet', item: 'FLEET-02' },
          'recovery': { section: 'fleet', item: 'FLEET-02' },
          'dr': { section: 'fleet', item: 'FLEET-02' },
        };
        const mapped = subMap[sub];
        if (mapped) {
          this.activeSection.set(mapped.section);
          this.activeItemId.set(mapped.item);
        }
      }
    });
  }

  setActiveSection(sectionId: string): void {
    this.activeSection.set(sectionId);
  }

  onViewModuleComponents(moduleCode: string): void {
    this.selectedModuleForComponentRegistry.set(moduleCode);
    this.activeSection.set('modules');
    this.activeItemId.set('MS-02');
  }
}
