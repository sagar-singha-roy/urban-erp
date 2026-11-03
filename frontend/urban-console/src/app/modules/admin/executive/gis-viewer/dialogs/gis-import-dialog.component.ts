import { Component, inject, input, OnInit, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GisImportResult, GisLayer, GisOptions } from '../../../../../core/models/gis.model';
import { GisService } from '../../../../../core/services/gis.service';

@Component({
  selector: 'app-gis-import-dialog',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './gis-import-dialog.component.html',
  styleUrl: './gis-dialog.scss',
})
export class GisImportDialogComponent implements OnInit {
  private gis = inject(GisService);

  readonly options = input.required<GisOptions>();
  readonly layer = input.required<GisLayer>();
  readonly imported = output<GisImportResult>();
  readonly closed = output<void>();

  readonly isSaving = signal(false);
  readonly error = signal('');
  sourceCrs = 'EPSG:4326';
  geojson = '';

  ngOnInit(): void {
    this.sourceCrs = this.layer().crs;
  }

  async readFile(event: Event): Promise<void> {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) {
      this.geojson = await file.text();
    }
  }

  submit(): void {
    let collection: unknown;
    try {
      collection = JSON.parse(this.geojson);
    } catch {
      this.error.set('This is not valid JSON.');
      return;
    }
    this.isSaving.set(true);
    this.error.set('');
    this.gis.importFeatures(this.layer().id!, this.sourceCrs, collection).subscribe({
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
