import { Component, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CrossTenantService } from '../../../../../core/services/cross-tenant.service';
import { AccessGrant, UserOption } from '../../../../../core/models/cross-tenant.model';
import { UserPickerComponent } from './user-picker.component';

const OPEN_STATUSES = ['Pending', 'Active'];
const GRANTS_PER_USER = 100;

/** Pick a user, then one of their open access records. */
@Component({
  selector: 'app-xt-grant-picker',
  standalone: true,
  imports: [FormsModule, UserPickerComponent],
  template: `
    <div class="field wide">
      <label for="xt-grant-user">User <span class="required">*</span></label>
      <app-xt-user-picker inputId="xt-grant-user" (selected)="onUser($event)"></app-xt-user-picker>
    </div>
    <div class="field wide">
      <label for="xt-grant">Access Record <span class="required">*</span></label>
      <select
        id="xt-grant"
        [ngModel]="grantId()"
        (ngModelChange)="pick($event)"
        [ngModelOptions]="{ standalone: true }"
        [disabled]="!grants().length"
      >
        <option [ngValue]="null">{{ hint() }}</option>
        @for (g of grants(); track g.id) {
          <option [ngValue]="g.id">
            {{ g.recordNumber }}: {{ g.accessLevel }} to {{ describe()(g) }} ({{ g.status }})
          </option>
        }
      </select>
    </div>
  `,
  styleUrl: './picker.scss',
})
export class GrantPickerComponent {
  private service = inject(CrossTenantService);
  readonly describe = input.required<(grant: AccessGrant) => string>();
  readonly selected = output<AccessGrant | null>();

  readonly grants = signal<AccessGrant[]>([]);
  readonly grantId = signal<string | null>(null);
  readonly hint = signal('Select a user first');

  onUser(user: UserOption | null): void {
    this.grants.set([]);
    this.pick(null);
    if (!user) {
      this.hint.set('Select a user first');
      return;
    }
    this.service
      .listGrants({ skip: 0, limit: GRANTS_PER_USER }, { userProfileId: user.id })
      .subscribe({
        next: (res) => {
          const open = res.data.filter((g) => OPEN_STATUSES.includes(g.status));
          this.grants.set(open);
          this.hint.set(
            open.length ? 'Select an access record' : 'This user has no open cross-tenant access',
          );
        },
      });
  }

  pick(id: string | null): void {
    this.grantId.set(id);
    this.selected.emit(this.grants().find((g) => g.id === id) ?? null);
  }
}
