import { TenantOption } from '../../../../core/models/white-label.model';

/** The API stores UTC without an offset. Marking it as UTC lets the date pipe show local time. */
export function asUtc(value: string | null | undefined): string | null {
  if (!value) return null;
  return /([zZ]|[+-]\d\d:?\d\d)$/.test(value) ? value : `${value}Z`;
}

/** Value for a datetime-local input, in the viewer's time zone. */
export function toLocalInput(value: string | null | undefined): string {
  const utc = asUtc(value);
  if (!utc) return '';
  const date = new Date(utc);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

/** A datetime-local value sent as UTC. */
export function fromLocalInput(value: string | null | undefined): string | null {
  return value ? new Date(value).toISOString() : null;
}

export function asOptions(values: string[]): { value: string; label: string }[] {
  return values.map((value) => ({ value, label: value }));
}

export function tenantOptions(tenants: TenantOption[]): { value: string; label: string }[] {
  return tenants.map((t) => ({ value: t.tenantId, label: `${t.name} (${t.tenantLevel})` }));
}

export function tenantName(tenants: TenantOption[], id: string | null | undefined): string {
  if (!id) return '';
  return tenants.find((t) => t.tenantId === id)?.name ?? id;
}

export function grantStatusClass(status: string): string {
  if (['Active', 'Approved', 'Decided', 'Completed', 'Allow'].includes(status)) return 'good';
  if (['Pending', 'Awaiting Change', 'Open'].includes(status)) return 'warn';
  if (['Revoked', 'Expired', 'Rejected', 'Deny'].includes(status)) return 'bad';
  return '';
}
