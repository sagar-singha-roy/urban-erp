import { Directive, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { DialogService } from '../../../../core/services/dialog.service';
import { PageQuery, PagedResponse, apiError } from '../../../../core/models/white-label.model';

const SEARCH_DELAY_MS = 300;

/** Server-side search and paging shared by the five ADM-T04 tables. */
@Directive()
export abstract class PagedTab<T> implements OnInit, OnDestroy {
  protected dialogs = inject(DialogService);

  readonly items = signal<T[]>([]);
  readonly total = signal(0);
  readonly search = signal('');
  readonly page = signal(1);
  readonly limit = signal(10);
  readonly isLoading = signal(false);

  private searchTimer?: ReturnType<typeof setTimeout>;

  protected abstract fetch(query: PageQuery): Observable<PagedResponse<T>>;

  ngOnInit(): void {
    this.load();
  }

  ngOnDestroy(): void {
    clearTimeout(this.searchTimer);
  }

  load(): void {
    this.isLoading.set(true);
    this.fetch({ search: this.search().trim() || undefined, skip: (this.page() - 1) * this.limit(), limit: this.limit() }).subscribe({
      next: (res) => {
        this.items.set(res.data);
        this.total.set(res.total);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.dialogs.showToast(apiError(err, 'Could not load this list.'), 'error', 4000);
      },
    });
  }

  onSearch(value: string): void {
    this.search.set(value);
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.page.set(1);
      this.load();
    }, SEARCH_DELAY_MS);
  }

  onPage(page: number): void {
    this.page.set(page);
    this.load();
  }

  onLimit(limit: number): void {
    this.limit.set(limit);
    this.page.set(1);
    this.load();
  }

  statusClass(status: string): string {
    if (['Active', 'Verified'].includes(status)) return 'good';
    if (['Pending', 'Pending Issuance', 'Expiring Soon', 'Draft'].includes(status)) return 'warn';
    if (['Failed', 'Expired', 'Suspended', 'Invalid'].includes(status)) return 'bad';
    return '';
  }
}
