/** ADM-R02 Cross-Tenant Access Management. Field names match the API's camelCase JSON. */

export interface CrossTenantOptions {
  userTypes: string[];
  accessLevels: string[];
  accessStatuses: string[];
  scopeLevels: string[];
  scopeModes: string[];
  actions: string[];
  dataScopes: string[];
  accessDecisions: string[];
  reviewStatuses: string[];
  reviewDecisions: string[];
  modules: { code: string; name: string }[];
}

export interface UserOption {
  id: string;
  fullName: string;
  email: string;
  userType: string | null;
  homeTenantId: string | null;
}
export interface ComponentOption {
  code: string;
  name: string;
  moduleCode: string;
}
export interface AreaOption {
  id: string;
  name: string;
  tenantId: string;
  zoneId: string | null;
}
export interface Department {
  id: string;
  tenantId: string;
  code: string;
  name: string;
  isActive: boolean;
}

export interface GrantPayload {
  userProfileId: string;
  userType: string;
  homeTenantId: string;
  targetTenantIds: string[];
  accessLevel: string;
  effectiveFrom: string;
  effectiveUntil: string | null;
  businessJustification: string;
  approvalAuthorityId: string;
  approvalReference: string | null;
}

export interface AccessGrant extends GrantPayload {
  id: string;
  recordNumber: string;
  userEmail: string;
  userName: string;
  status: string;
  approvalAuthorityEmail: string;
  requestedBy: string;
  approvedBy: string | null;
  approvedAt: string | null;
  decisionNote: string | null;
  revokedBy: string | null;
  revokedAt: string | null;
  revokeReason: string | null;
  hasScope: boolean;
  createdAt: string | null;
}

export interface GrantFilters {
  status?: string;
  accessLevel?: string;
  userType?: string;
  userProfileId?: string;
}

export interface ScopePayload {
  grantId: string;
  accessScope: string;
  stateTenantId: string;
  ulbTenantIds: string[];
  departmentIds: string[];
  zoneIds: string[];
  wardIds: string[];
  scopeMode: string;
  includeChildTenants: boolean;
  restrictedComponents: string[];
  effectiveDate: string;
  expiryDate: string | null;
}

export interface AccessScope extends ScopePayload {
  id: string;
  recordNumber: string;
  userEmail: string;
  userName: string;
  updatedBy: string | null;
  updatedAt: string | null;
}

export interface RulePayload {
  grantId: string;
  targetTenantId: string;
  moduleCodes: string[];
  componentCodes: string[];
  actionPermissions: string[];
  dataAccessScope: string;
  accessDecision: string;
  restrictionReason: string | null;
}

export interface PermissionRule extends RulePayload {
  id: string;
  recordNumber: string;
  userEmail: string;
  reviewStatus: string;
  reviewedBy: string | null;
  reviewedAt: string | null;
  createdBy: string | null;
}

export interface CampaignPayload {
  campaignName: string;
  periodStart: string;
  periodEnd: string;
  tenantScope: string[];
  userTypes: string[];
  accessStatuses: string[];
  reviewOwnerId: string;
  reviewDeadline: string;
}

export interface ReviewCampaign extends CampaignPayload {
  id: string;
  reviewOwnerEmail: string;
  status: string;
  createdBy: string | null;
  createdAt: string | null;
  completedAt: string | null;
  totalItems: number;
  decidedItems: number;
}

export interface ReviewItem {
  id: string;
  grantId: string;
  recordNumber: string;
  userEmail: string;
  userName: string;
  userType: string;
  homeTenantId: string;
  targetTenantIds: string[];
  accessLevel: string;
  grantStatus: string;
  status: string;
  reviewDecision: string | null;
  reviewerComments: string | null;
  decidedBy: string | null;
  decidedAt: string | null;
}

export interface HistoryEntry {
  id: string;
  grantId: string | null;
  userEmail: string;
  homeTenantId: string | null;
  targetTenantIds: string[];
  previousAccessLevel: string | null;
  newAccessLevel: string | null;
  previousScope: string | null;
  newScope: string | null;
  action: string;
  changedBy: string;
  ipAddress: string | null;
  reason: string | null;
  approvalReference: string | null;
  createdAt: string;
}

export interface HistoryFilters {
  action?: string;
  dateFrom?: string;
  dateTo?: string;
}

/** Readable label for an API action code such as PERMISSION_RULE_SAVED. */
export function actionLabel(action: string): string {
  return action
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase());
}
