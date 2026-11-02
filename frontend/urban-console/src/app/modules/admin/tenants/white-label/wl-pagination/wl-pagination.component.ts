import { Component, computed, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';

@Component({
  selector: 'app-wl-pagination',
  standalone: true,
  imports: [FormsModule, IconComponent],
  templateUrl: './wl-pagination.component.html',
  styleUrl: './wl-pagination.component.scss',
})
export class WlPaginationComponent {
  readonly page = input.required<number>();
  readonly limit = input.required<number>();
  readonly total = input.required<number>();
  readonly pageChange = output<number>();
  readonly limitChange = output<number>();

  readonly limits = [5, 10, 20, 50];
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit())));
  readonly first = computed(() => (this.total() === 0 ? 0 : (this.page() - 1) * this.limit() + 1));
  readonly last = computed(() => Math.min(this.page() * this.limit(), this.total()));
}
