import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { CheckListComponent } from '../../../../../../shared/components/check-list/check-list.component';
import { CrossTenantService } from '../../../../../../core/services/cross-tenant.service';
import { DialogService } from '../../../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../../../core/models/white-label.model';
import {
  AccessGrant,
  AccessScope,
  AreaOption,
  ComponentOption,
  CrossTenantOptions,
  Department,
  ScopePayload,
} from '../../../../../../core/models/cross-tenant.model';
import { GrantPickerComponent } from '../../shared/grant-picker.component';
import { asOptions, fromLocalInput, tenantName, toLocalInput } from '../../cross-tenant-utils';

type Choice = { value: string; label: string };

/** Tab 2: narrow an access record to a state, ULBs, departments, zones or wards. A scope never adds tenants. */
@Component({
  selector: 'app-xt-scope-dialog',
  standalone: true,
  imports: [FormsModule, IconComponent, CheckListComponent, GrantPickerComponent],
  templateUrl: './scope-dialog.component.html',
  styleUrl: '../grant-dialog/grant-dialog.component.scss',
})
export class ScopeDialogComponent implements OnInit {
  @Input() record: AccessScope | null = null;
  @Input({ required: true }) options!: CrossTenantOptions;
  @Input({ required: true }) tenants!: TenantOption[];
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(CrossTenantService);
  private dialogs = inject(DialogService);
  readonly isSaving = signal(false);
  readonly asOptions = asOptions;

  readonly grant = signal<AccessGrant | null>(null);
  readonly departments = signal<Department[]>([]);
  readonly zones = signal<AreaOption[]>([]);
  readonly wards = signal<AreaOption[]>([]);
  readonly components = signal<ComponentOption[]>([]);

  effectiveDate = '';
  expiryDate = '';
  restrictedModules: string[] = [];
  restrictedComponentCodes: string[] = [];
  browseModule = '';
  newDepartment = { tenantId: '', code: '', name: '' };
  form: ScopePayload = {
    grantId: '',
    accessScope: 'State',
    stateTenantId: '',
    ulbTenantIds: [],
    departmentIds: [],
    zoneIds: [],
    wardIds: [],
    scopeMode: 'Explicit',
    includeChildTenants: true,
    restrictedComponents: [],
    effectiveDate: '',
    expiryDate: null,
  };

  readonly describeGrant = (g: AccessGrant): string =>
    g.targetTenantIds.map((t) => tenantName(this.tenants, t)).join(', ');

  ngOnInit(): void {
    const r = this.record;
    this.effectiveDate = toLocalInput(r?.effectiveDate) || toLocalInput(new Date().toISOString());
    this.expiryDate = toLocalInput(r?.expiryDate);
    if (!r) return;
    const moduleCodes = new Set(this.options.modules.map((m) => m.code));
    this.form = {
      ...r,
      ulbTenantIds: [...r.ulbTenantIds],
      departmentIds: [...r.departmentIds],
      zoneIds: [...r.zoneIds],
      wardIds: [...r.wardIds],
    };
    this.restrictedModules = r.restrictedComponents.filter((c) => moduleCodes.has(c));
    this.restrictedComponentCodes = r.restrictedComponents.filter((c) => !moduleCodes.has(c));
    this.service.getGrant(r.grantId).subscribe({
      next: (res) => {
        this.grant.set(res.data);
        this.loadAreas();
      },
    });
  }

  onGrant(grant: AccessGrant | null): void {
    this.grant.set(grant);
    this.form.grantId = grant?.id ?? '';
    this.form.ulbTenantIds = [];
    const states = this.stateChoices;
    this.form.stateTenantId = states.length === 1 ? states[0].tenantId : '';
    this.onAreasChanged();
  }

  private get targets(): string[] {
    return this.grant()?.targetTenantIds ?? [];
  }

  get stateChoices(): TenantOption[] {
    const targets = this.targets;
    const ulbStates = new Set(
      this.tenants
        .filter((t) => t.tenantLevel === 'ULB' && targets.includes(t.tenantId))
        .map((t) => t.stateTenantId),
    );
    return this.tenants.filter(
      (t) =>
        t.tenantLevel === 'State' && (targets.includes(t.tenantId) || ulbStates.has(t.tenantId)),
    );
  }

  get wholeState(): boolean {
    return !!this.form.stateTenantId && this.targets.includes(this.form.stateTenantId);
  }

  get ulbChoices(): Choice[] {
    const inState = this.tenants.filter(
      (t) => t.tenantLevel === 'ULB' && t.stateTenantId === this.form.stateTenantId,
    );
    const reachable = this.wholeState
      ? inState
      : inState.filter((t) => this.targets.includes(t.tenantId));
    return reachable.map((t) => ({ value: t.tenantId, label: t.name }));
  }

  private get areaTenants(): string[] {
    return this.form.ulbTenantIds.length
      ? this.form.ulbTenantIds
      : this.ulbChoices.map((c) => c.value);
  }

  get departmentTenants(): Choice[] {
    return [this.form.stateTenantId, ...this.areaTenants]
      .filter(Boolean)
      .map((id) => ({ value: id, label: tenantName(this.tenants, id) }));
  }

  get departmentChoices(): Choice[] {
    return this.departments().map((d) => ({
      value: d.id,
      label: `${d.name} (${tenantName(this.tenants, d.tenantId)})`,
    }));
  }

  get zoneChoices(): Choice[] {
    return this.zones().map((z) => ({
      value: z.id,
      label: `${z.name}, ${tenantName(this.tenants, z.tenantId)}`,
    }));
  }

  get wardChoices(): Choice[] {
    return this.wards().map((w) => ({
      value: w.id,
      label: `${w.name}, ${tenantName(this.tenants, w.tenantId)}`,
    }));
  }

  get moduleChoices(): Choice[] {
    return this.options.modules.map((m) => ({ value: m.code, label: `${m.code} ${m.name}` }));
  }

  get componentChoices(): Choice[] {
    return this.components().map((c) => ({ value: c.code, label: `${c.code} ${c.name}` }));
  }

  onState(stateId: string): void {
    this.form.stateTenantId = stateId;
    this.form.ulbTenantIds = [];
    if (!this.wholeState) this.form.includeChildTenants = true;
    this.onAreasChanged();
  }

  onUlbs(ids: string[]): void {
    this.form.ulbTenantIds = ids;
    this.onAreasChanged();
  }

  onZones(ids: string[]): void {
    this.form.zoneIds = ids;
    this.loadWards();
  }

  /** Areas outside the new selection are dropped, because the server would refuse them. */
  private onAreasChanged(): void {
    this.form.departmentIds = [];
    this.form.zoneIds = [];
    this.form.wardIds = [];
    this.loadAreas();
  }

  private loadAreas(): void {
    const tenants = this.areaTenants;
    if (!this.form.stateTenantId) {
      this.departments.set([]);
      this.zones.set([]);
      this.wards.set([]);
      return;
    }
    this.service
      .getDepartments([this.form.stateTenantId, ...tenants])
      .subscribe({ next: (res) => this.departments.set(res.data) });
    this.service.getZones(tenants).subscribe({ next: (res) => this.zones.set(res.data) });
    this.loadWards();
  }

  private loadWards(): void {
    this.service
      .getWards(this.areaTenants, this.form.zoneIds)
      .subscribe({ next: (res) => this.wards.set(res.data) });
  }

  onBrowseModule(code: string): void {
    this.browseModule = code;
    if (!code) {
      this.components.set([]);
      return;
    }
    this.service.getComponents([code]).subscribe({ next: (res) => this.components.set(res.data) });
  }

  /** The list shows one module's components, so keep choices made under other modules. */
  onComponents(codes: string[]): void {
    const shown = new Set(this.components().map((c) => c.code));
    this.restrictedComponentCodes = [
      ...this.restrictedComponentCodes.filter((c) => !shown.has(c)),
      ...codes,
    ];
  }

  addDepartment(): void {
    const d = this.newDepartment;
    if (!d.tenantId || !d.code.trim() || !d.name.trim()) {
      this.dialogs.showToast('Choose the tenant and enter a code and name.', 'warning');
      return;
    }
    this.service
      .createDepartment({ tenantId: d.tenantId, code: d.code.trim(), name: d.name.trim() })
      .subscribe({
        next: (res) => {
          this.departments.update((list) => [...list, res.data]);
          this.form.departmentIds = [...this.form.departmentIds, res.data.id];
          this.newDepartment = { tenantId: d.tenantId, code: '', name: '' };
        },
        error: (err) =>
          this.dialogs.showToast(apiError(err, 'Could not add this department.'), 'error', 5000),
      });
  }

  submit(): void {
    const f = this.form;
    if (!f.grantId || !f.accessScope || !f.stateTenantId || !f.scopeMode || !this.effectiveDate) {
      this.dialogs.showToast('Please complete the required fields.', 'warning');
      return;
    }
    const payload: ScopePayload = {
      grantId: f.grantId,
      accessScope: f.accessScope,
      stateTenantId: f.stateTenantId,
      ulbTenantIds: f.ulbTenantIds,
      departmentIds: f.departmentIds,
      zoneIds: f.zoneIds,
      wardIds: f.wardIds,
      scopeMode: f.scopeMode,
      includeChildTenants: this.wholeState ? f.includeChildTenants : true,
      restrictedComponents: [...this.restrictedModules, ...this.restrictedComponentCodes],
      effectiveDate: fromLocalInput(this.effectiveDate)!,
      expiryDate: fromLocalInput(this.expiryDate),
    };
    this.isSaving.set(true);
    this.service.saveScope(payload).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.dialogs.showToast('Scope saved.', 'success');
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.dialogs.showToast(apiError(err, 'Could not save this scope.'), 'error', 5000);
      },
    });
  }
}
