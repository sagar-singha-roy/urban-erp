import { Component, OnDestroy, OnInit, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CrossTenantService } from '../../../../../core/services/cross-tenant.service';
import { UserOption } from '../../../../../core/models/cross-tenant.model';

const SEARCH_DELAY_MS = 300;

/** Search the global user directory and pick one user. */
@Component({
  selector: 'app-xt-user-picker',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="field picker">
      <input
        type="search"
        [id]="inputId()"
        placeholder="Search name or email"
        autocomplete="off"
        [attr.aria-label]="label() + ' search'"
        [ngModel]="term()"
        (ngModelChange)="onSearch($event)"
        [ngModelOptions]="{ standalone: true }"
      />
      <select
        [attr.aria-label]="label()"
        [ngModel]="selectedId()"
        (ngModelChange)="pick($event)"
        [ngModelOptions]="{ standalone: true }"
      >
        <option [ngValue]="null">
          {{ results().length ? 'Select a user' : 'No matching users' }}
        </option>
        @for (u of results(); track u.id) {
          <option [ngValue]="u.id">{{ u.fullName }} ({{ u.email }})</option>
        }
      </select>
    </div>
  `,
  styleUrl: './picker.scss',
})
export class UserPickerComponent implements OnInit, OnDestroy {
  private service = inject(CrossTenantService);
  readonly inputId = input('xt-user');
  readonly label = input('User');
  readonly selected = output<UserOption | null>();

  readonly term = signal('');
  readonly results = signal<UserOption[]>([]);
  readonly selectedId = signal<string | null>(null);
  private timer?: ReturnType<typeof setTimeout>;

  ngOnInit(): void {
    this.search('');
  }

  ngOnDestroy(): void {
    clearTimeout(this.timer);
  }

  onSearch(value: string): void {
    this.term.set(value);
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.search(value.trim()), SEARCH_DELAY_MS);
  }

  private search(value: string): void {
    this.service.findUsers(value).subscribe({ next: (res) => this.results.set(res.data) });
  }

  pick(id: string | null): void {
    this.selectedId.set(id);
    this.selected.emit(this.results().find((u) => u.id === id) ?? null);
  }
}
