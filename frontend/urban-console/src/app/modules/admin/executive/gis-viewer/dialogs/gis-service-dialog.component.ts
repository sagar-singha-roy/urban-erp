import { Component, inject, input, OnInit, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GisApprovedService, GisOptions } from '../../../../../core/models/gis.model';
import { GisService } from '../../../../../core/services/gis.service';

@Component({
  selector: 'app-gis-service-dialog',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './gis-service-dialog.component.html',
  styleUrl: './gis-dialog.scss',
})
export class GisServiceDialogComponent implements OnInit {
  private gis = inject(GisService);

  readonly options = input.required<GisOptions>();
  readonly service = input<GisApprovedService | null>(null);
  readonly tenantId = input('');
  readonly saved = output<void>();
  readonly closed = output<void>();

  readonly isSaving = signal(false);
  readonly error = signal('');
  form: GisApprovedService = { tenantId: '', serviceName: '', baseUrl: '', isActive: true };

  ngOnInit(): void {
    this.form = { ...this.form, tenantId: this.tenantId(), ...this.service() };
  }

  submit(): void {
    this.isSaving.set(true);
    this.error.set('');
    this.gis.saveService(this.form).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.saved.emit();
      },
      error: (err) => {
        this.isSaving.set(false);
        const detail = err?.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'This service could not be saved.');
      },
    });
  }
}
