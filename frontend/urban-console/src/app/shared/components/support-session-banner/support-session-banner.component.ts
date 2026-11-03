import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ImpersonationService } from '../../../core/services/impersonation.service';
import { KeycloakAuthService } from '../../../core/services/keycloak.service';
import { DialogService } from '../../../core/services/dialog.service';
import {
  SUPPORT_SESSION_ENDED,
  canUseSupportHub,
  supportSession,
} from '../../../core/services/support-session.state';
import { asUtc } from '../../../modules/admin/iam/cross-tenant-access/cross-tenant-utils';

const CHECK_EVERY_MS = 30000;
const TICK_MS = 1000;

/** Shown on every page while a support session is live, so nobody mistakes whose account they are in. */
@Component({
  selector: 'app-support-session-banner',
  standalone: true,
  template: `
    @if (session(); as s) {
      <div class="support-banner" role="alert" aria-live="assertive">
        <span class="label">SUPPORT SESSION</span>
        <span class="who"
          >Acting as <strong>{{ s.targetName }}</strong> ({{ s.targetEmail }}) in {{ s.tenantId }},
          for {{ s.agentEmail }}</span
        >
        <span class="mode">{{ s.accessMode }}</span>
        <span class="clock">{{ remaining() }} left</span>
        <button type="button" (click)="end('Support session ended.')" [disabled]="isEnding()">
          End session
        </button>
      </div>
    }
  `,
  styleUrl: './support-session-banner.component.scss',
})
export class SupportSessionBannerComponent implements OnInit, OnDestroy {
  private service = inject(ImpersonationService);
  private auth = inject(KeycloakAuthService);
  private dialogs = inject(DialogService);

  readonly session = computed(() => (supportSession()?.active ? supportSession() : null));
  readonly isEnding = signal(false);
  private readonly now = signal(Date.now());
  private checkTimer?: ReturnType<typeof setInterval>;
  private tickTimer?: ReturnType<typeof setInterval>;
  private readonly onEnded = () => this.end('The support session has ended.');

  readonly remaining = computed(() => {
    const expires = this.session()?.expiresAt;
    if (!expires) return '';
    const seconds = Math.max(
      0,
      Math.round((new Date(asUtc(expires)!).getTime() - this.now()) / 1000),
    );
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  });

  ngOnInit(): void {
    window.addEventListener(SUPPORT_SESSION_ENDED, this.onEnded);
    this.check();
    this.checkTimer = setInterval(() => this.check(), CHECK_EVERY_MS);
    this.tickTimer = setInterval(() => {
      this.now.set(Date.now());
      if (this.session() && this.remaining() === '0:00')
        this.end('The support session reached its time limit.');
    }, TICK_MS);
  }

  ngOnDestroy(): void {
    window.removeEventListener(SUPPORT_SESSION_ENDED, this.onEnded);
    clearInterval(this.checkTimer);
    clearInterval(this.tickTimer);
  }

  check(): void {
    if (!this.auth.isAuthenticated()) {
      supportSession.set(null);
      return;
    }
    this.service.currentSession().subscribe({
      next: (res) => {
        supportSession.set(res.data.active ? res.data : null);
        // The hub is closed during a session, so only ask about it outside one.
        if (!res.data.active) {
          this.service
            .getMe()
            .subscribe({
              next: (me) => canUseSupportHub.set(me.data.canRequest || me.data.isSuperAdmin),
              error: () => canUseSupportHub.set(false),
            });
        }
      },
      error: () => supportSession.set(null),
    });
  }

  /** Clears the session cookie and reloads, so nothing from the target's view stays on screen. */
  end(message: string): void {
    if (this.isEnding()) return;
    this.isEnding.set(true);
    const reload = () => {
      supportSession.set(null);
      this.dialogs.showToast(message, 'info');
      window.location.reload();
    };
    this.service.endCurrentSession().subscribe({ next: reload, error: reload });
  }
}
