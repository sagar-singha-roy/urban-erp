import { Component, input, output } from '@angular/core';

/** Touch-friendly multi-select. Each option is a full 44px row. */
@Component({
  selector: 'app-check-list',
  standalone: true,
  templateUrl: './check-list.component.html',
  styleUrl: './check-list.component.scss',
})
export class CheckListComponent {
  readonly options = input.required<{ value: string; label: string }[]>();
  readonly value = input.required<string[]>();
  readonly valueChange = output<string[]>();

  toggle(option: string, checked: boolean): void {
    const current = this.value();
    this.valueChange.emit(checked ? [...current, option] : current.filter((item) => item !== option));
  }
}
