import { Component, OnInit, inject, signal, viewChild } from '@angular/core';
import { forkJoin } from 'rxjs';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { RefreshButtonComponent } from '../../../../shared/components/refresh-button/refresh-button.component';
import { QuotaService } from '../../../../core/services/quota.service';
import { WhiteLabelService } from '../../../../core/services/white-label.service';
import { DialogService } from '../../../../core/services/dialog.service';
import { TenantOption, apiError } from '../../../../core/models/white-label.model';
import { QuotaOptions, RecipientOption } from '../../../../core/models/quota.model';
import { StorageAllocationTabComponent } from './tabs/storage-allocation-tab/storage-allocation-tab.component';
import { StorageUsageTabComponent } from './tabs/storage-usage-tab/storage-usage-tab.component';
import { SmsTabComponent } from './tabs/sms-tab/sms-tab.component';
import { ApiTabComponent } from './tabs/api-tab/api-tab.component';
import { AlertsTabComponent } from './tabs/alerts-tab/alerts-tab.component';

type TabId = 'allocation' | 'usage' | 'sms' | 'api' | 'alerts';

@Component({
  selector: 'app-quota-usage',
  standalone: true,
  imports: [IconComponent, RefreshButtonComponent, StorageAllocationTabComponent, StorageUsageTabComponent, SmsTabComponent, ApiTabComponent, AlertsTabComponent],
  templateUrl: './quota-usage.component.html',
  styleUrl: './quota-usage.component.scss',
})
export class QuotaUsageComponent implements OnInit {
  private service = inject(QuotaService);
  private whiteLabel = inject(WhiteLabelService);
  private dialogs = inject(DialogService);

  readonly tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'allocation', label: 'Storage Allocation', icon: 'ri-hard-drive-2-line' },
    { id: 'usage', label: 'Storage Usage', icon: 'ri-pie-chart-line' },
    { id: 'sms', label: 'SMS / DLT Credits', icon: 'ri-message-2-line' },
    { id: 'api', label: 'API Usage', icon: 'ri-speed-line' },
    { id: 'alerts', label: 'Usage Alerts', icon: 'ri-alarm-warning-line' },
  ];
  readonly activeTab = signal<TabId>('allocation');
  readonly options = signal<QuotaOptions | null>(null);
  readonly tenants = signal<TenantOption[]>([]);
  readonly recipients = signal<RecipientOption[]>([]);

  private allocation = viewChild(StorageAllocationTabComponent);
  private usage = viewChild(StorageUsageTabComponent);
  private sms = viewChild(SmsTabComponent);
  private api = viewChild(ApiTabComponent);
  private alerts = viewChild(AlertsTabComponent);

  ngOnInit(): void {
    this.loadReferenceData();
  }

  loadReferenceData(): void {
    forkJoin({ options: this.service.getOptions(), tenants: this.whiteLabel.getTenants(), recipients: this.service.getRecipients() }).subscribe({
      next: ({ options, tenants, recipients }) => {
        this.options.set(options.data);
        this.tenants.set(tenants.data);
        this.recipients.set(recipients.data);
      },
      error: (err) => this.dialogs.showToast(apiError(err, 'Could not load this page.'), 'error', 4000),
    });
  }

  refresh(): void {
    this.loadReferenceData();
    (this.allocation() ?? this.usage() ?? this.sms() ?? this.api() ?? this.alerts())?.load();
    this.alerts()?.loadEvents();
  }
}
