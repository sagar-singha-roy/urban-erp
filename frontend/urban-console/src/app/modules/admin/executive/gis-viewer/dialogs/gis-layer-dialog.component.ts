import { Component, computed, inject, input, OnInit, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GisLayer, GisOptions } from '../../../../../core/models/gis.model';
import { GisService } from '../../../../../core/services/gis.service';

@Component({
  selector: 'app-gis-layer-dialog',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './gis-layer-dialog.component.html',
  styleUrl: './gis-dialog.scss',
})
export class GisLayerDialogComponent implements OnInit {
  private gis = inject(GisService);

  readonly options = input.required<GisOptions>();
  readonly layer = input<GisLayer | null>(null);
  readonly presetCategory = input<string>('City');
  readonly saved = output<GisLayer>();
  readonly closed = output<void>();

  readonly isSaving = signal(false);
  readonly error = signal('');
  readonly dataSource = signal('PostGIS');
  readonly isRemote = computed(() => ['WMS', 'WFS'].includes(this.dataSource()));

  form: GisLayer = {
    tenantId: '',
    layerName: '',
    layerCode: '',
    layerCategory: 'City',
    layerType: 'Polygon',
    dataSource: 'PostGIS',
    serviceUrl: '',
    workspaceName: '',
    layerIdentifier: '',
    crs: 'EPSG:4326',
    defaultVisibility: true,
    opacity: 1,
    layerStyle: { color: '#2563eb', weight: 2, fillOpacity: 0.2 },
    layerStatus: 'Active',
    utilityCategory: '',
    networkType: '',
    department: '',
  };
  stateCode = '';

  ngOnInit(): void {
    const existing = this.layer();
    if (existing) {
      this.form = { ...this.form, ...existing, layerStyle: { ...this.form.layerStyle, ...existing.layerStyle } };
      this.stateCode = existing.stateCode ?? '';
    } else {
      this.form.layerCategory = this.presetCategory();
    }
    this.dataSource.set(this.form.dataSource);
  }

  ulbs() {
    return this.options().ulbs.filter((u) => !this.stateCode || u.stateCode === this.stateCode);
  }

  save(): void {
    this.form.dataSource = this.dataSource();
    this.isSaving.set(true);
    this.error.set('');
    this.gis.saveLayer(this.form).subscribe({
      next: (layer) => {
        this.isSaving.set(false);
        this.saved.emit(layer);
      },
      error: (err) => {
        this.isSaving.set(false);
        const detail = err?.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'Check the required fields and try again.');
      },
    });
  }
}
