import { Component, ElementRef, HostListener, computed, inject, input, model, signal } from '@angular/core';

/** Searchable checkbox dropdown. Items may be plain strings or objects read through valueKey and labelKey. */
@Component({
  selector: 'app-gis-multi-select',
  standalone: true,
  templateUrl: './gis-multi-select.component.html',
  styleUrl: './gis-multi-select.component.scss',
})
export class GisMultiSelectComponent {
  private host = inject(ElementRef<HTMLElement>);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  readonly items = input.required<readonly any[]>();
  readonly valueKey = input<string>('');
  readonly labelKey = input<string>('');
  readonly placeholder = input<string>('Select');
  readonly value = model<string[]>([]);

  readonly open = signal(false);
  readonly term = signal('');

  readonly options = computed(() =>
    this.items().map((item) => ({
      value: String(this.valueKey() ? item[this.valueKey()] : item),
      label: String(this.labelKey() ? item[this.labelKey()] : item),
    })),
  );
  readonly visible = computed(() => {
    const query = this.term().trim().toLowerCase();
    return this.options().filter((o) => !query || o.label.toLowerCase().includes(query));
  });
  readonly summary = computed(() => {
    const selected = this.value();
    if (!selected.length) return this.placeholder();
    const first = this.options().find((o) => o.value === selected[0])?.label ?? selected[0];
    return selected.length === 1 ? first : `${first} +${selected.length - 1}`;
  });

  isSelected(value: string): boolean {
    return this.value().includes(value);
  }

  toggle(value: string): void {
    this.value.update((current) => (current.includes(value) ? current.filter((v) => v !== value) : [...current, value]));
  }

  clear(): void {
    this.value.set([]);
  }

  @HostListener('document:click', ['$event'])
  closeOnOutsideClick(event: Event): void {
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    this.open.set(false);
  }
}
