export type DialogVariant = 'primary' | 'destructive' | 'warning' | 'info' | 'success';

export interface ConfirmDialogConfig {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: DialogVariant;
  requireKeyword?: string; // e.g. user must type "DELETE" or "REJECT"
}

export interface AlertDialogConfig {
  title: string;
  message: string;
  variant?: DialogVariant;
  okText?: string;
}

export interface PromptDialogConfig {
  title: string;
  message?: string;
  inputLabel: string;
  placeholder?: string;
  initialValue?: string;
  confirmText?: string;
  cancelText?: string;
  required?: boolean;
}

export interface ToastConfig {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  durationMs?: number;
}
