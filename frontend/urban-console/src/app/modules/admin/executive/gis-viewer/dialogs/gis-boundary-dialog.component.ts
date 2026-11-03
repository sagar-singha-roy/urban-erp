import { Component, inject, input, OnInit, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GisImportResult, GisOptions } from '../../../../../core/models/gis.model';
import { GisService } from '../../../../../core/services/gis.service';

@Component({
  selector: 'app-gis-boundary-dialog',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './gis-boundary-dialog.component.html',
  styleUrl: './gis-dialog.scss',
})
export class GisBoundaryDialogComponent implements OnInit {
  private gis = inject(GisService);

  readonly options = input.required<GisOptions>();
  readonly tenantId = input('');
  readonly imported = output<GisImportResult>();
  readonly closed = output<void>();

  readonly isSaving = signal(false);
  readonly error = signal('');
  readonly levels = ['Ward', 'Zone', 'Parcel'];
  ulb = '';
  level = 'Ward';
  matchField = '';
  sourceCrs = 'EPSG:4326';
  geojson = '';

  ngOnInit(): void {
    this.ulb = this.tenantId();
  }

  async readFile(event: Event): Promise<void> {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) this.geojson = await file.text();
  }

  submit(): void {
    let featureCollection: unknown;
    try {
      featureCollection = JSON.parse(this.geojson);
    } catch {
      this.error.set('This is not valid JSON.');
      return;
    }
    this.isSaving.set(true);
    this.error.set('');
    this.gis.importBoundaries({ tenantId: this.ulb, level: this.level, matchField: this.matchField.trim(), sourceCrs: this.sourceCrs, featureCollection }).subscribe({
      next: (result) => {
        this.isSaving.set(false);
        this.imported.emit(result);
      },
      error: (err) => {
        this.isSaving.set(false);
        const detail = err?.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'The import failed.');
      },
    });
  }
}
