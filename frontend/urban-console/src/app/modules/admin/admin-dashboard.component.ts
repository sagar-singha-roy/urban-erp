import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { IconComponent } from '../../shared/components/icon/icon.component';
import { DialogService } from '../../core/services/dialog.service';
import { KeycloakAuthService } from '../../core/services/keycloak.service';
import {
  SUPER_ADMIN_SECTIONS,
  SuperAdminSection,
} from '../../core/models/super-admin.model';

export interface StateBenchmark {
  stateCode: string;
  stateName: string;
  ulbCount: number;
  parcels: number;
  demandAmount: number;
  collectionPct: number;
  status: string;
}

export interface GlobalKPIs {
  totalStates: number;
  totalUlbs: number;
  totalParcels: number;
  totalRevenueDemand: number;
  totalRevenueCollected: number;
  collectionEfficiency: number;
  totalActiveUsers: number;
  systemHealthPct: number;
}

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './admin-dashboard.component.html',
  styleUrl: './admin-dashboard.component.scss',
})
export class AdminDashboardComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  public dialogs = inject(DialogService);
  public authService = inject(KeycloakAuthService);

  readonly sections: SuperAdminSection[] = SUPER_ADMIN_SECTIONS;
  readonly activeSection = signal<string>('intel');
  readonly isSystemHealthy = signal<boolean>(true);

  readonly globalKPIs = signal<GlobalKPIs>({
    totalStates: 28,
    totalUlbs: 4812,
    totalParcels: 64200000,
    totalRevenueDemand: 428500000000,
    totalRevenueCollected: 335944000000,
    collectionEfficiency: 78.4,
    totalActiveUsers: 14200,
    systemHealthPct: 99.98,
  });

  readonly stateBenchmarks = signal<StateBenchmark[]>([
    {
      stateCode: 'TG',
      stateName: 'Telangana',
      ulbCount: 142,
      parcels: 3850000,
      demandAmount: 4850000000,
      collectionPct: 81.2,
      status: 'Active',
    },
    {
      stateCode: 'MH',
      stateName: 'Maharashtra',
      ulbCount: 398,
      parcels: 11200000,
      demandAmount: 16200000000,
      collectionPct: 78.5,
      status: 'Active',
    },
    {
      stateCode: 'KA',
      stateName: 'Karnataka',
      ulbCount: 281,
      parcels: 7400000,
      demandAmount: 9800000000,
      collectionPct: 75.1,
      status: 'Onboarding',
    },
    {
      stateCode: 'AP',
      stateName: 'Andhra Pradesh',
      ulbCount: 125,
      parcels: 4100000,
      demandAmount: 5120000000,
      collectionPct: 79.8,
      status: 'Active',
    },
    {
      stateCode: 'TN',
      stateName: 'Tamil Nadu',
      ulbCount: 649,
      parcels: 14800000,
      demandAmount: 18900000000,
      collectionPct: 83.4,
      status: 'Active',
    },
  ]);

  readonly officialModules = [
    { code: 'PTX', name: 'Property Tax & Revenue', domain: 'Revenue & Billing', phase: 1, components: 33 },
    { code: 'WTR', name: 'Water & Sewerage Billing', domain: 'Revenue & Billing', phase: 1, components: 32 },
    { code: 'GRV', name: 'Citizen Desk & Grievance (RTI)', domain: 'Citizen Welfare', phase: 1, components: 30 },
    { code: 'FIN', name: 'Finance & Municipal Accounts', domain: 'Finance & Admin', phase: 1, components: 30 },
    { code: 'TRL', name: 'Trade Licences Management', domain: 'Revenue & Billing', phase: 2, components: 26 },
    { code: 'UCH', name: 'User Charges (Solid/Liquid)', domain: 'Revenue & Billing', phase: 2, components: 23 },
    { code: 'SWM', name: 'Solid Waste Operations', domain: 'Infrastructure', phase: 2, components: 17 },
    { code: 'HRM', name: 'Payroll & HR Management', domain: 'Finance & Admin', phase: 2, components: 19 },
    { code: 'DMS', name: 'Document Vault & e-File', domain: 'Finance & Admin', phase: 2, components: 30 },
    { code: 'ENG', name: 'Engineering Projects (Works)', domain: 'Infrastructure', phase: 3, components: 20 },
    { code: 'BPM', name: 'Building Permission Management', domain: 'Planning', phase: 3, components: 22 },
    { code: 'SLM', name: 'Street Lights (CCMS & Poles)', domain: 'Infrastructure', phase: 3, components: 12 },
    { code: 'TPL', name: 'Town Planning & Master Plans', domain: 'Planning', phase: 3, components: 23 },
    { code: 'PRK', name: 'Parks & Horticulture', domain: 'Infrastructure', phase: 3, components: 18 },
    { code: 'MPM', name: 'Municipal Property & Lease', domain: 'Revenue & Billing', phase: 4, components: 15 },
    { code: 'LGL', name: 'Legal Cases & Court Liaison', domain: 'Planning', phase: 4, components: 17 },
    { code: 'INV', name: 'Inventory & Central Stores', domain: 'Finance & Admin', phase: 4, components: 17 },
    { code: 'FNC', name: 'Fire NOC & Hazard Control', domain: 'Planning', phase: 4, components: 17 },
    { code: 'GSC', name: 'Government Welfare Schemes', domain: 'Citizen Welfare', phase: 4, components: 14 },
  ];

  ngOnInit(): void {
    this.route.queryParams.subscribe((params) => {
      if (params['section']) {
        this.activeSection.set(params['section']);
      }
    });
    this.route.params.subscribe((params) => {
      if (params['section']) {
        this.activeSection.set(params['section']);
      }
    });
    this.refreshMetrics();
  }

  setActiveSection(sectionId: string): void {
    this.activeSection.set(sectionId);
  }

  refreshMetrics(): void {
    const headers = this.authService.getHeaders();
    this.http.get<any>('http://localhost:8000/api/v1/admin/overview', { headers }).subscribe({
      next: (kpis) => {
        if (kpis) {
          this.globalKPIs.set(kpis);
        }
      },
      error: () => {
        // Fallback demo state
      },
    });

    this.http.get<StateBenchmark[]>('http://localhost:8000/api/v1/admin/benchmarks', { headers }).subscribe({
      next: (b) => {
        if (b && b.length > 0) {
          this.stateBenchmarks.set(b);
        }
      },
      error: () => {},
    });
  }

  async openProvisionModal(type: 'state' | 'ulb'): Promise<void> {
    const confirmed = await this.dialogs.confirm({
      title: type === 'state' ? 'Provision State Tenant (Level 1)' : 'Provision City ULB Sub-Tenant (Level 2)',
      message: type === 'state'
        ? 'Allocate new state tenant jurisdiction with Master DB schema isolation and regional language packs?'
        : 'Onboard new ULB under active state jurisdiction? Active modules will cascade automatically from parent state.',
      confirmText: 'Proceed to Provision',
      cancelText: 'Cancel',
      variant: 'primary',
    });

    if (confirmed) {
      this.dialogs.showToast(
        `${type === 'state' ? 'State Tenant' : 'City ULB'} provisioning workflow initiated.`,
        'success',
        3000
      );
    }
  }

  async inviteUser(): Promise<void> {
    const confirmed = await this.dialogs.confirm({
      title: 'Invite Multi-Scope User',
      message: 'Send onboarding invitation with Keycloak SSO credentials and granular component-level RBAC role allocation?',
      confirmText: 'Send Invitation',
      cancelText: 'Cancel',
      variant: 'primary',
    });

    if (confirmed) {
      this.dialogs.showToast('Invitation dispatched to National Urban Registry gateway.', 'success', 3000);
    }
  }

  async testImpersonate(tenantId: string): Promise<void> {
    const proceed = await this.dialogs.confirm({
      title: `Temporary Impersonate Session: ${tenantId}`,
      message: `You are entering a cryptographic support impersonation session for tenant ${tenantId}. All actions will be logged to CERT-In immutable audit vault.`,
      confirmText: 'Enter Session',
      cancelText: 'Cancel',
      variant: 'destructive',
    });

    if (proceed) {
      this.authService.switchTenant(tenantId);
      this.dialogs.showToast(`Impersonating context for ${tenantId}. Audit active.`, 'warning', 4000);
    }
  }
}
