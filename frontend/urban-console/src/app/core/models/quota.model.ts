export interface QuotaOptions {
  tenantLevels: string[];
  recordStatuses: string[];
  storageTypes: string[];
  storageProviders: string[];
  measuredProviders: string[];
  storageUnits: string[];
  fileTypes: string[];
  modules: string[];
  smsProviders: string[];
  smsCategories: string[];
  smsConnected: boolean;
  apiGateways: string[];
  apiServices: string[];
  apiCategories: string[];
  quotaPeriods: string[];
  resourceTypes: string[];
  alertConditions: string[];
  operators: string[];
  severities: string[];
  notificationChannels: string[];
}

export interface RecipientOption { id: string; fullName: string; email: string; tenantId: string; }
export interface ModuleAllocation { moduleCode: string; allocationBytes: number; }

export interface StorageAllocation {
  id?: string;
  tenantId?: string;
  tenantLevel: string;
  stateTenantId: string;
  ulbTenantId: string | null;
  allocationName: string;
  storageType: string;
  storageProvider: string;
  storageBucket: string;
  allocationAmount: number | null;
  storageUnit: string;
  maxFileSizeMb: number | null;
  allowedFileTypes: string[];
  moduleAllocations: ModuleAllocation[];
  effectiveFrom: string;
  effectiveUntil: string | null;
  allocationStatus: string;
  remarks: string | null;
}

export interface LargestFile { objectName: string; sizeBytes: number; moduleCode: string; }
export interface StorageUsageRow {
  allocationId: string;
  allocationName: string;
  tenantId: string;
  tenantLevel: string;
  storageType: string;
  storageProvider: string;
  telemetryConnected: boolean;
  allocatedBytes: number;
  usedBytes: number | null;
  availableBytes: number | null;
  utilisationPercentage: number | null;
  totalFiles: number | null;
  largestFiles: LargestFile[];
  moduleUsage: Record<string, number>;
  usageStatus: string;
}

export interface StorageUsageFilters {
  tenantLevel?: string;
  stateTenantId?: string;
  ulbTenantId?: string;
  storageProvider?: string;
  storageType?: string;
  modules?: string[];
  dateFrom?: string;
  dateTo?: string;
  usageState?: string;
  minPercentage?: number | null;
  maxPercentage?: number | null;
}

export interface SmsAllocation {
  id?: string;
  tenantId?: string;
  stateTenantId: string;
  ulbTenantId: string | null;
  allocationName: string;
  smsProvider: string;
  dltEntityId: string | null;
  senderId: string | null;
  dltTemplateId: string | null;
  creditAllocation: number | null;
  creditsConsumed?: number;
  remainingCredits?: number;
  deliveredMessages?: number;
  failedMessages?: number;
  deliveryPercentage?: number | null;
  validFrom: string;
  validUntil: string;
  smsCategories: string[];
  lowCreditThreshold: number | null;
  notificationRecipients: string[];
  allocationStatus: string;
}

export interface ApiPolicy {
  id?: string;
  tenantId?: string;
  tenantLevel: string;
  stateTenantId: string;
  ulbTenantId: string | null;
  apiGateway: string;
  apiServices: string[];
  apiCategory: string | null;
  rateLimitPerMinute: number | null;
  rateLimitPerHour: number | null;
  rateLimitPerDay: number | null;
  burstLimit: number | null;
  concurrentLimit: number | null;
  quotaPeriod: string;
  effectiveFrom: string;
  effectiveUntil: string | null;
  policyStatus: string;
  totalRequests?: number;
  successfulRequests?: number;
  failedRequests?: number;
  throttledRequests?: number;
  averageResponseMs?: number | null;
  peakRequestsPerMinute?: number;
  remainingQuota?: number | null;
}

export interface ThresholdLevel { id: string; levelName: string; percentage: number; }

export interface AlertRule {
  id?: string;
  tenantId?: string;
  tenantLevel: string;
  stateTenantId: string;
  ulbTenantId: string | null;
  alertName: string;
  alertCode: string;
  resourceType: string;
  alertCondition: string;
  thresholdPercentage: number | null;
  thresholdValue: number | null;
  comparisonOperator: string;
  alertSeverity: string;
  notificationChannels: string[];
  notificationRecipients: string[];
  repeatIntervalMinutes: number | null;
  isActive: boolean;
  description: string | null;
  isFiring?: boolean;
  lastValue?: number | null;
}

export interface AlertEvent {
  id: string;
  tenantId: string;
  severity: string;
  message: string;
  deliverySummary: string | null;
  acknowledgedBy: string | null;
  acknowledgedAt: string | null;
  createdAt: string;
}

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB'];

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return 'Not connected';
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < BYTE_UNITS.length - 1) {
    value /= 1024;
    unit++;
  }
  return `${unit === 0 ? value : value.toFixed(2)} ${BYTE_UNITS[unit]}`;
}
