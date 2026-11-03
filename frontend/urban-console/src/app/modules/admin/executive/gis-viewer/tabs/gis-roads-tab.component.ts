import { Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GisLayer, GisOptions, GisRoadFilter } from '../../../../../core/models/gis.model';
import { GisMultiSelectComponent } from '../gis-multi-select.component';

@Component({
  selector: 'app-gis-roads-tab',
  standalone: true,
  imports: [FormsModule, GisMultiSelectComponent],
  templateUrl: './gis-roads-tab.component.html',
  styleUrl: '../gis-viewer.component.scss',
})
export class GisRoadsTabComponent {
  readonly options = input.required<GisOptions>();
  readonly layers = input.required<GisLayer[]>();
  // The parent owns this object, so filters survive switching tabs.
  readonly filter = input.required<GisRoadFilter>();
  readonly show = output<void>();
  readonly addLayer = output<void>();
  readonly tenantChange = output<string>();

  ulbs(): GisOptions['ulbs'] {
    return this.options().ulbs.filter((u) => !this.filter().state || u.stateCode === this.filter().state);
  }

  /** Layers of this ULB and category, from the chosen data source. */
  layersFor(category: string): GisLayer[] {
    const f = this.filter();
    return this.layers().filter((l) => l.tenantId === f.tenantId && l.layerCategory === category && (!f.dataSource || l.dataSource === f.dataSource));
  }
}
