export interface ApiResponse<T> { success: boolean; code: number; data: T; }
export interface PagedResponse<T> { success: boolean; code: number; data: T[]; total: number; }

export interface WhiteLabelOptions {
  tenantLevels: string[];
  recordStatuses: string[];
  fontFamilies: string[];
  logoTypes: string[];
  domainTypes: string[];
  dnsProviders: string[];
  dnsRecordTypes: string[];
  verificationMethods: string[];
  domainStatuses: string[];
  certificateProviders: string[];
  certificateTypes: string[];
  targetApplications: string[];
  targetServices: string[];
  routingStrategies: string[];
}

export interface TenantOption { tenantId: string; name: string; tenantLevel: string; stateTenantId: string; }

export interface BrandingProfile {
  id?: string;
  tenantId?: string;
  tenantLevel: string;
  stateTenantId: string;
  ulbTenantId: string | null;
  profileName: string;
  displayName: string;
  tagline: string | null;
  primaryColour: string;
  secondaryColour: string;
  accentColour: string | null;
  headerBackgroundColour: string | null;
  sidebarBackgroundColour: string | null;
  fontFamily: string | null;
  loginPageTitle: string | null;
  loginPageMessage: string | null;
  footerText: string | null;
  customCss: string | null;
  brandingStatus: string;
}

export interface AssetFile { id: string; fileKind: string; contentType: string; sizeBytes: number; }
export interface AssetSet {
  id: string;
  tenantId: string;
  logoType: string;
  altText: string;
  effectiveFrom: string | null;
  assetStatus: string;
  files: AssetFile[];
}

export interface TenantDomain {
  id: string;
  tenantId: string;
  domainName: string;
  domainType: string;
  subdomain: string | null;
  rootDomain: string | null;
  dnsProvider: string | null;
  dnsRecordType: string;
  dnsHost: string;
  dnsTarget: string;
  verificationMethod: string;
  verificationStatus: string;
  verificationToken: string;
  verificationInstructions: string;
  claimExpiresAt: string | null;
  lastCheckedAt: string | null;
  lastCheckMessage: string | null;
  isPrimary: boolean;
  domainStatus: string;
}

/** The API never returns key material. hasPrivateKey only says that one is stored. */
export interface TenantCertificate {
  id: string;
  tenantId: string;
  domainId: string;
  domainName: string;
  provider: string;
  certificateType: string;
  hasPrivateKey: boolean;
  autoRenewal: boolean;
  renewalNotificationDays: number;
  expiryDate: string | null;
  certificateStatus: string;
  statusMessage: string | null;
  lastValidationAt: string | null;
}

export interface DomainMapping {
  id?: string;
  tenantId: string;
  domainId: string;
  domainName?: string;
  mappingName: string;
  targetApplication: string;
  targetService: string;
  targetRoute: string | null;
  routingStrategy: string;
  sslRequired: boolean;
  forceHttps: boolean;
  isPrimary: boolean;
  mappingStatus: string;
  effectiveFrom: string | null;
}

export interface RoutingStatus { appliedVersion: string | null; pendingVersion: string | null; lastError: string | null; }

export interface PublicBranding {
  displayName: string;
  tagline: string | null;
  primaryColour: string;
  secondaryColour: string;
  accentColour: string | null;
  headerBackgroundColour: string | null;
  sidebarBackgroundColour: string | null;
  fontFamily: string | null;
  loginPageTitle: string | null;
  loginPageMessage: string | null;
  footerText: string | null;
  customCss: string | null;
  altText: string | null;
  assets: Record<string, string>;
}

export interface PageQuery { search?: string; skip: number; limit: number; tenantId?: string; }

/** Readable message from a FastAPI error, including validation errors. */
export function apiError(err: { error?: { detail?: unknown } }, fallback: string): string {
  const detail = err?.error?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, '');
  return fallback;
}
