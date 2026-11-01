import { Component, computed, input, signal } from '@angular/core';

export const PAGE_SIZES = [5, 10, 20, 50];

/** Page and rows-per-page for each table on a page, addressed by a key. */
export class PagerState {
  private readonly state = signal<Record<string, { page: number; limit: number }>>({});
  private readonly terms = signal<Record<string, string>>({});

  search(key: string): string {
    return this.terms()[key] ?? '';
  }

  setSearch(key: string, term: string): void {
    this.terms.update((all) => ({ ...all, [key]: term }));
    this.setPage(key, 1);
  }

  private current(key: string) {
    return this.state()[key] ?? { page: 1, limit: PAGE_SIZES[1] };
  }

  limit(key: string): number {
    return this.current(key).limit;
  }

  page(key: string, total: number): number {
    const { page, limit } = this.current(key);
    return Math.min(page, Math.max(1, Math.ceil(total / limit)));
  }

  start(key: string, total: number): number {
    return (this.page(key, total) - 1) * this.limit(key);
  }

  end(key: string, total: number): number {
    return this.start(key, total) + this.limit(key);
  }

  setPage(key: string, page: number): void {
    this.state.update((all) => ({ ...all, [key]: { ...this.current(key), page } }));
  }

  setLimit(key: string, limit: number): void {
    this.state.update((all) => ({ ...all, [key]: { page: 1, limit } }));
  }
}

@Component({
  selector: 'app-table-pager',
  standalone: true,
  templateUrl: './table-pager.component.html',
  styleUrl: './table-pager.component.scss',
})
export class TablePagerComponent {
  readonly state = input.required<PagerState>();
  readonly key = input.required<string>();
  readonly total = input.required<number>();

  readonly sizes = PAGE_SIZES;
  readonly page = computed(() => this.state().page(this.key(), this.total()));
  readonly limit = computed(() => this.state().limit(this.key()));
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit())));
  readonly first = computed(() => (this.total() === 0 ? 0 : (this.page() - 1) * this.limit() + 1));
  readonly last = computed(() => Math.min(this.page() * this.limit(), this.total()));

  go(page: number): void {
    this.state().setPage(this.key(), page);
  }

  changeLimit(value: string): void {
    this.state().setLimit(this.key(), Number(value));
  }
}
