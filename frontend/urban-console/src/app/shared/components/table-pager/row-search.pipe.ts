import { Pipe, PipeTransform } from '@angular/core';

/** Keeps rows where any value contains the search text. */
@Pipe({ name: 'rowSearch', standalone: true })
export class RowSearchPipe implements PipeTransform {
  transform<T>(rows: readonly T[] | null | undefined, term: string): T[] {
    const list = [...(rows ?? [])];
    const query = term.trim().toLowerCase();
    if (!query) return list;
    return list.filter((row) => JSON.stringify(row).toLowerCase().includes(query));
  }
}
