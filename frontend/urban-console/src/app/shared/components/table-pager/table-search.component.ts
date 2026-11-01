import { Component, input } from '@angular/core';
import { PagerState } from './table-pager.component';

@Component({
  selector: 'app-table-search',
  standalone: true,
  templateUrl: './table-search.component.html',
  styleUrl: './table-search.component.scss',
})
export class TableSearchComponent {
  readonly state = input.required<PagerState>();
  readonly key = input.required<string>();
}
