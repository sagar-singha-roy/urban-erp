/** ADM-R04 Support Impersonation Hub. Field names match the API's camelCase JSON. */

export interface ImpersonationOptions {
  requestTypes: string[];
  durations: number[];
  accessModes: string[];
  tenantLevels: string[];
  requestStatuses: string[];
  sessionStatuses: string[];
  roles: { code: string; name: string }[];
  writeActionTypes: string[];
  sensitiveFieldParts: string[];
  maxApprovalHours: number;
}

export interface HubProfile {
  userId: string;
  email: string;
  fullName: string;
  roleCode: string;
  isSuperAdmin: boolean;
  canRequest: boolean;
}
export interface TargetOption {
  id: string;
  fullName: string;
  email: string;
  role: string;
  tenantIds: string[];
}
export interface ApproverOption {
  id: string;
  fullName: string;
  email: string;
}

export interface ImpersonationPolicy {
  id?: string;
  policyCode?: string;
  policyName: string;
  allowedSupportRoles: string[];
  allowedTenantLevels: string[];
  maxSessionMinutes: number;
  approvalRequired: boolean;
  dualApproval: boolean;
  readOnlyDefault: boolean;
  maskSensitiveData: boolean;
  downloadDisabled: boolean;
  writeActionsAllowed: string[];
  sessionRecording: boolean;
  isActive: boolean;
  updatedBy?: string | null;
  updatedAt?: string | null;
}

export interface RequestPayload {
  targetUserId: string;
  targetTenantId: string;
  requestType: string;
  businessJustification: string;
  ticketReference: string;
  requestedMinutes: number;
  accessMode: string;
}

export interface ApprovalRecord {
  stage: number;
  approverEmail: string;
  decision: string;
  comments: string | null;
  decidedAt: string | null;
}

export interface ImpersonationRequest extends RequestPayload {
  id: string;
  requestNumber: string;
  policyCode: string;
  supportUserId: string;
  supportEmail: string;
  supportName: string;
  targetEmail: string;
  targetName: string;
  targetTenantLevel: string;
  status: string;
  dualApprovalRequired: boolean;
  secondApproverEmail: string | null;
  approvalValidUntil: string | null;
  requestedAt: string | null;
  decidedAt: string | null;
  approvals: ApprovalRecord[];
}

export interface DecisionPayload {
  decision: string;
  comments: string | null;
  approvalValidUntil: string | null;
  dualApprovalRequired: boolean;
  secondApproverId: string | null;
}

export interface SupportSession {
  id: string;
  sessionNumber: string;
  requestId: string;
  requestNumber: string;
  supportEmail: string;
  targetEmail: string;
  targetName: string;
  tenantId: string;
  accessMode: string;
  status: string;
  startedAt: string;
  expiresAt: string;
  endedAt: string | null;
  terminationReason: string | null;
  terminatedBy: string | null;
}

export interface CurrentSession {
  active: boolean;
  sessionNumber?: string | null;
  targetName?: string | null;
  targetEmail?: string | null;
  tenantId?: string | null;
  accessMode?: string | null;
  expiresAt?: string | null;
  agentEmail?: string | null;
}

export interface AuditEntry {
  sessionId: string;
  sessionNumber: string;
  requestNumber: string;
  supportEmail: string;
  targetEmail: string;
  tenantId: string;
  status: string;
  loginTime: string;
  logoutTime: string | null;
  actionsPerformed: number;
  ipAddress: string | null;
  device: string | null;
  approvalReference: string;
  terminationReason: string | null;
  auditEventId: string | null;
}

export interface SessionAction {
  method: string;
  path: string;
  permission: string | null;
  statusCode: number;
  createdAt: string;
}
