export interface SuperAdminMenuItem {
  id: string;
  code: string;
  title: string;
  route: string;
  badge?: string;
  description: string;
}

export interface SuperAdminSection {
  id: string;
  title: string;
  icon: string;
  items: SuperAdminMenuItem[];
}

export const SUPER_ADMIN_SECTIONS: SuperAdminSection[] = [
  {
    id: 'intel',
    title: 'EXECUTIVE INTELLIGENCE',
    icon: 'chart',
    items: [
      { id: 'ADM-A01', code: 'ADM-A01', title: 'Global Command Dashboard', route: '/admin/dashboard', badge: 'Live', description: 'Pan-state real-time KPI rollup' },
      { id: 'ADM-A02', code: 'ADM-A02', title: 'State & City Benchmarking', route: '/admin/benchmarking', description: 'Comparative DCB & Swachh recovery' },
      { id: 'ADM-A03', code: 'ADM-A03', title: 'Consolidated Finance Ledger', route: '/admin/finance', description: '15th FC & central scheme tracking' },
      { id: 'ADM-A04', code: 'ADM-A04', title: 'Spatial GIS Multi-City Map', route: '/admin/gis-map', badge: 'GIS', description: 'Pan-state PostGIS layer view' },
    ]
  },
  {
    id: 'tenants',
    title: 'TENANCY & HIERARCHY',
    icon: 'parcels',
    items: [
      { id: 'ADM-T01', code: 'ADM-T01', title: 'State Tenants (Level 1)', route: '/admin/tenants/states', description: 'State onboarding & configuration' },
      { id: 'ADM-T02', code: 'ADM-T02', title: 'Sub-Tenants & ULBs (Level 2)', route: '/admin/tenants/cities', badge: 'ULB', description: 'Municipal corporations & wards' },
      { id: 'ADM-T03', code: 'ADM-T03', title: 'Tenant Lifecycle & Lock', route: '/admin/tenants/lifecycle', description: 'Maintenance mode & suspension' },
      { id: 'ADM-T04', code: 'ADM-T04', title: 'White-Labelling & Domains', route: '/admin/tenants/domains', description: 'CNAME & state emblem branding' },
    ]
  },
  {
    id: 'subscriptions',
    title: 'MODULES & SUBSCRIPTIONS',
    icon: 'collection',
    items: [
      { id: 'ADM-S01', code: 'ADM-S01', title: '19-Module Master Catalogue', route: '/admin/modules/catalogue', badge: '415', description: 'All modules & component targets' },
      { id: 'ADM-S02', code: 'ADM-S02', title: 'State Module Subscriptions', route: '/admin/modules/state-subs', description: 'Assign modules to state tenants' },
      { id: 'ADM-S03', code: 'ADM-S03', title: 'Sub-Tenant Cascade Guard', route: '/admin/modules/delegation', description: 'Enforce parent subscription caps' },
      { id: 'ADM-S04', code: 'ADM-S04', title: 'Quota & Usage Metering', route: '/admin/modules/quotas', description: 'Storage, SMS & API call limits' },
    ]
  },
  {
    id: 'rbac',
    title: 'GLOBAL IDENTITY & RBAC',
    icon: 'dms',
    items: [
      { id: 'ADM-R01', code: 'ADM-R01', title: 'Global User Directory', route: '/admin/identity/users', description: 'Multi-tier user provisioning' },
      { id: 'ADM-R02', code: 'ADM-R02', title: 'Scope & Membership Review', route: '/admin/identity/scopes', badge: 'Audit', description: 'Cross-tenant roving access check' },
      { id: 'ADM-R03', code: 'ADM-R03', title: '415 Component RBAC Engine', route: '/admin/identity/permissions', description: 'Action permission matrix builder' },
      { id: 'ADM-R04', code: 'ADM-R04', title: 'Support Impersonation Hub', route: '/admin/identity/impersonation', badge: 'Secured', description: 'Signed temporary officer login' },
      { id: 'ADM-R05', code: 'ADM-R05', title: 'SSO & Keycloak Realms', route: '/admin/identity/sso', description: 'MeriPehchan & MFA policies' },
    ]
  },
  {
    id: 'integrations',
    title: 'INTEGRATIONS & COMPLIANCE',
    icon: 'efficiency',
    items: [
      { id: 'ADM-C01', code: 'ADM-C01', title: 'Central Gateway Policies', route: '/admin/security/gateway', description: 'API rate limits, WAF & IP allowlists' },
      { id: 'ADM-C02', code: 'ADM-C02', title: 'Payment Switch & Escrow', route: '/admin/integrations/payments', badge: 'BBPS', description: 'SBI ePay, BillDesk, treasury routing' },
      { id: 'ADM-C03', code: 'ADM-C03', title: 'State Adapters Hub', route: '/admin/integrations/adapters', description: 'IGRS, eCourts CNR, CGF feeds' },
      { id: 'ADM-C04', code: 'ADM-C04', title: 'CERT-In Immutable Audit', route: '/admin/security/audit-vault', badge: 'Signed', description: 'Cryptographically hashed audit log' },
      { id: 'ADM-C05', code: 'ADM-C05', title: 'Data Sovereignty & RLS Check', route: '/admin/security/rls', description: 'PostgreSQL tenant isolation audit' },
    ]
  },
  {
    id: 'operations',
    title: 'PLATFORM OPERATIONS & FLEET',
    icon: 'slm',
    items: [
      { id: 'ADM-O01', code: 'ADM-O01', title: 'Microservice Cluster Health', route: '/admin/system/health', badge: '19/19', description: 'Pod topology, memory, DB latency' },
      { id: 'ADM-O02', code: 'ADM-O02', title: 'Multi-Tenant Schema Migrator', route: '/admin/system/migrations', description: 'Zero-downtime rolling DDL execution' },
      { id: 'ADM-O03', code: 'ADM-O03', title: 'Scoped Cache Partition Purge', route: '/admin/system/cache', description: 'Selective Redis partition flusher' },
      { id: 'ADM-O04', code: 'ADM-O04', title: 'Backup & Disaster Recovery', route: '/admin/system/backups', description: 'Cross-region snapshot & PITR tests' },
      { id: 'ADM-O05', code: 'ADM-O05', title: 'Global Broadcast Banner', route: '/admin/system/announcements', description: 'Cross-portal maintenance alerts' },
      { id: 'ADM-O06', code: 'ADM-O06', title: 'Release Ring & Flags', route: '/admin/system/releases', description: 'Canary & progressive feature flags' },
    ]
  }
];
