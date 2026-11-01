import { Component, inject, input, output, signal } from '@angular/core';
import { DialogService } from '../../../core/services/dialog.service';
import { LoadingService } from '../../../core/services/loading.service';
import { IconComponent } from '../icon/icon.component';

const SETTLE_CHECK_MS = 150;
const MAX_WAIT_MS = 30000;

/**
 * The one refresh control for every page: same look, spinner for the real duration of the
 * reload, and a single success or failure message. Pages only say what to reload.
 */
@Component({
  selector: 'app-refresh-button',
  standalone: true,
  imports: [IconComponent],
  templateUrl: './refresh-button.component.html',
  styleUrl: './refresh-button.component.scss',
})
export class RefreshButtonComponent {
  private loader = inject(LoadingService);
  private dialogs = inject(DialogService);

  /** What is being reloaded, as it should read in a sentence, e.g. "audit vault". */
  readonly subject = input.required<string>();
  readonly iconOnly = input<boolean>(false);
  readonly refresh = output<void>();

  readonly isRefreshing = signal<boolean>(false);

  run(): void {
    if (this.isRefreshing()) return;
    this.isRefreshing.set(true);
    const failuresBefore = this.loader.failedRequests();
    const startedAt = Date.now();
    this.dialogs.setToastsMuted(true);
    this.refresh.emit();
    this.waitForRequests(failuresBefore, startedAt);
  }

  private waitForRequests(failuresBefore: number, startedAt: number): void {
    setTimeout(() => {
      const timedOut = Date.now() - startedAt > MAX_WAIT_MS;
      if (this.loader.isLoading() && !timedOut) {
        this.waitForRequests(failuresBefore, startedAt);
        return;
      }
      this.isRefreshing.set(false);
      this.dialogs.setToastsMuted(false);
      const subject = this.subject();
      if (timedOut || this.loader.failedRequests() > failuresBefore) {
        const title = subject.charAt(0).toUpperCase() + subject.slice(1);
        this.dialogs.showToast(`${title} could not be fully refreshed. Some data may be out of date.`, 'error', 4000);
      } else {
        const title = subject.charAt(0).toUpperCase() + subject.slice(1);
        this.dialogs.showToast(`${title} refreshed.`, 'success', 2500);
      }
    }, SETTLE_CHECK_MS);
  }
}
