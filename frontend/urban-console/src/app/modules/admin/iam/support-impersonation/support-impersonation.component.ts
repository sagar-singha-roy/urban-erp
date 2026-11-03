import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { ImpersonationService } from '../../../../core/services/impersonation.service';
import { DialogService } from '../../../../core/services/dialog.service';
import { apiError } from '../../../../core/models/white-label.model';
import { HubProfile, ImpersonationOptions } from '../../../../core/models/impersonation.model';
import { RequestsTabComponent } from './tabs/requests-tab.component';
import { ApprovalsTabComponent } from './tabs/approvals-tab.component';
import { SessionsTabComponent } from './tabs/sessions-tab.component';
import { PolicyTabComponent } from './tabs/policy-tab.component';
import { AuditTabComponent } from './tabs/audit-tab.component';

type TabId = 'requests' | 'approvals' | 'sessions' | 'policy' | 'audit';

const TABS: { id: TabId; label: string; icon: string; superAdminOnly: boolean }[] = [
  {
    id: 'requests',
    label: 'Impersonation Requests',
    icon: 'ri-user-shared-line',
    superAdminOnly: false,
  },
  {
    id: 'approvals',
    label: 'Approval Management',
    icon: 'ri-checkbox-circle-line',
    superAdminOnly: true,
  },
  { id: 'sessions', label: 'Active Sessions', icon: 'ri-timer-line', superAdminOnly: false },
  {
    id: 'policy',
    label: 'Impersonation Policy',
    icon: 'ri-shield-keyhole-line',
    superAdminOnly: true,
  },
  { id: 'audit', label: 'Audit Logs', icon: 'ri-file-shield-2-line', superAdminOnly: true },
];

/** ADM-R04 Support Impersonation Hub. Support staff see their own requests and sessions; super admins see everything. */
@Component({
  selector: 'app-support-impersonation',
  standalone: true,
  imports: [
    IconComponent,
    RequestsTabComponent,
    ApprovalsTabComponent,
    SessionsTabComponent,
    PolicyTabComponent,
    AuditTabComponent,
  ],
  template: `
    <div class="hub-wrapper">
      <header class="suvidha-page-header">
        <div class="header-titles">
          <h1
            class="page-title"
            data-tooltip="Level 0 Identity &amp; Access Management — ADM-R04"
            title="Level 0 Identity &amp; Access Management — ADM-R04"
          >
            Support Impersonation Hub
          </h1>
          <p class="page-subtitle">
            Short, approved sessions for troubleshooting a user's account, without their
            credentials. Every session is audited.
          </p>
        </div>
      </header>
      @if (me(); as profile) {
        <div class="tabs-bar" role="tablist">
          @for (tab of tabs(); track tab.id) {
            <button
              type="button"
              class="tab-btn"
              role="tab"
              [class.active]="activeTab() === tab.id"
              [attr.aria-selected]="activeTab() === tab.id"
              (click)="activeTab.set(tab.id)"
            >
              <app-icon [name]="tab.icon" [size]="16"></app-icon><span>{{ tab.label }}</span>
            </button>
          }
        </div>
        @if (options(); as opts) {
          <section class="tab-panel" role="tabpanel">
            @switch (activeTab()) {
              @case ('requests') {
                <app-imp-requests-tab [options]="opts" [me]="profile"></app-imp-requests-tab>
              }
              @case ('approvals') {
                <app-imp-approvals-tab [options]="opts" [me]="profile"></app-imp-approvals-tab>
              }
              @case ('sessions') {
                <app-imp-sessions-tab [options]="opts" [me]="profile"></app-imp-sessions-tab>
              }
              @case ('policy') {
                <app-imp-policy-tab [options]="opts"></app-imp-policy-tab>
              }
              @case ('audit') {
                <app-imp-audit-tab></app-imp-audit-tab>
              }
            }
          </section>
        }
      } @else if (denied()) {
        <div class="denied">{{ denied() }}</div>
      }
    </div>
  `,
  styleUrl: './support-impersonation.component.scss',
})
export class SupportImpersonationComponent implements OnInit {
  private service = inject(ImpersonationService);
  private dialogs = inject(DialogService);

  readonly options = signal<ImpersonationOptions | null>(null);
  readonly me = signal<HubProfile | null>(null);
  readonly denied = signal('');
  readonly activeTab = signal<TabId>('requests');
  readonly tabs = computed(() => TABS.filter((t) => !t.superAdminOnly || this.me()?.isSuperAdmin));

  ngOnInit(): void {
    forkJoin({ options: this.service.getOptions(), me: this.service.getMe() }).subscribe({
      next: ({ options, me }) => {
        this.options.set(options.data);
        this.me.set(me.data);
      },
      error: (err) => {
        const message = apiError(err, 'Could not load this page.');
        this.denied.set(message);
        this.dialogs.showToast(message, 'error', 4000);
      },
    });
  }
}
