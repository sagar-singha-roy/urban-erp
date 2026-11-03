import { Component, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
import { PagedTab } from '../../../../../../shared/components/paged-tab/paged-tab';
import { WlPaginationComponent } from '../../../../../../shared/components/wl-pagination/wl-pagination.component';
import { QuotaService } from '../../../../../../core/services/quota.service';
import { PageQuery, PagedResponse, TenantOption } from '../../../../../../core/models/white-label.model';
import { SmsAllocation, QuotaOptions, RecipientOption } from '../../../../../../core/models/quota.model';
import { SmsAllocationDialogComponent } from '../../dialogs/sms-allocation-dialog/sms-allocation-dialog.component';

@Component({
  selector: 'app-quota-sms-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, WlPaginationComponent, SmsAllocationDialogComponent],
  templateUrl: './sms-tab.component.html',
  styleUrl: './sms-tab.component.scss',
})
export class SmsTabComponent extends PagedTab<SmsAllocation> {
  private service = inject(QuotaService);
  readonly options = input.required<QuotaOptions>();
  readonly tenants = input.required<TenantOption[]>();
  readonly recipients = input.required<RecipientOption[]>();

  readonly isDialogOpen = signal(false);
  readonly selected = signal<SmsAllocation | null>(null);

  protected fetch(query: PageQuery): Observable<PagedResponse<SmsAllocation>> {
    return this.service.listSms(query);
  }

  open(record: SmsAllocation | null): void {
    this.selected.set(record);
    this.isDialogOpen.set(true);
  }

  onSaved(): void {
    this.isDialogOpen.set(false);
    this.load();
  }
}
