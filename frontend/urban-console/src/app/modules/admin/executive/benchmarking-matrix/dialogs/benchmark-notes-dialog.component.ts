import { Component, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';

@Component({
  selector: 'app-benchmark-notes-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './benchmark-notes-dialog.component.html',
  styleUrl: './benchmark-notes-dialog.component.scss',
})
export class BenchmarkNotesDialogComponent {
  readonly title = input<string>('Record Comparison Directive');
  readonly subtitle = input<string>('Attach executive observations to this benchmark snapshot');
  readonly initialNotes = input<string>('');

  readonly save = output<{ title: string; notes: string; priority: string }>();
  readonly cancel = output<void>();

  readonly noteTitle = signal<string>('State & City Governance Benchmark');
  readonly notesContent = signal<string>('');
  readonly priority = signal<string>('routine');

  constructor() {
    if (this.initialNotes()) {
      this.notesContent.set(this.initialNotes());
    }
  }

  saveNotes(): void {
    if (!this.notesContent().trim()) return;
    this.save.emit({
      title: this.noteTitle(),
      notes: this.notesContent(),
      priority: this.priority(),
    });
  }
}
