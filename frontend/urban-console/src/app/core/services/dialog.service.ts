import { Injectable, signal } from '@angular/core';
import {
  AlertDialogConfig,
  ConfirmDialogConfig,
  PromptDialogConfig,
  ToastConfig,
} from '../models/dialog.model';

@Injectable({
  providedIn: 'root',
})
export class DialogService {
  // Alert State
  readonly alertState = signal<{
    config: AlertDialogConfig;
    resolve: () => void;
  } | null>(null);

  // Confirm State
  readonly confirmState = signal<{
    config: ConfirmDialogConfig;
    resolve: (result: boolean) => void;
  } | null>(null);

  // Prompt State
  readonly promptState = signal<{
    config: PromptDialogConfig;
    resolve: (result: string | null) => void;
  } | null>(null);

  // Toast / Snackbars State
  readonly toasts = signal<ToastConfig[]>([]);

  // 1. Alert Dialog
  alert(config: AlertDialogConfig | string): Promise<void> {
    const finalConfig: AlertDialogConfig =
      typeof config === 'string'
        ? { title: 'Notification', message: config, variant: 'info' }
        : config;

    return new Promise<void>((resolve) => {
      this.alertState.set({
        config: finalConfig,
        resolve: () => {
          this.alertState.set(null);
          resolve();
        },
      });
    });
  }

  // 2. Confirm / Are you sure Dialog
  confirm(config: ConfirmDialogConfig | string): Promise<boolean> {
    const finalConfig: ConfirmDialogConfig =
      typeof config === 'string'
        ? {
            title: 'Confirmation Required',
            message: config,
            confirmText: 'Confirm',
            cancelText: 'Cancel',
            variant: 'primary',
          }
        : config;

    return new Promise<boolean>((resolve) => {
      this.confirmState.set({
        config: finalConfig,
        resolve: (result: boolean) => {
          this.confirmState.set(null);
          resolve(result);
        },
      });
    });
  }

  // 3. Prompt Input Dialog
  prompt(config: PromptDialogConfig): Promise<string | null> {
    return new Promise<string | null>((resolve) => {
      this.promptState.set({
        config,
        resolve: (result: string | null) => {
          this.promptState.set(null);
          resolve(result);
        },
      });
    });
  }

  // 4. Toast / Snackbar
  showToast(
    message: string,
    type: 'success' | 'error' | 'warning' | 'info' = 'info',
    durationMs = 4000
  ): void {
    const id = Math.random().toString(36).substring(2, 9);
    const toast: ToastConfig = { id, message, type, durationMs };

    this.toasts.update((current) => [...current, toast]);

    if (durationMs > 0) {
      setTimeout(() => {
        this.removeToast(id);
      }, durationMs);
    }
  }

  removeToast(id: string): void {
    this.toasts.update((current) => current.filter((t) => t.id !== id));
  }
}
