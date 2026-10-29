import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DialogService } from '../../../core/services/dialog.service';

@Component({
  selector: 'app-global-dialogs',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './global-dialogs.component.html',
  styleUrl: './global-dialogs.component.scss',
})
export class GlobalDialogsComponent {
  readonly dialogService = inject(DialogService);

  confirmKeywordInput = '';
  promptInput = '';

  onConfirmCancel(confirm: { resolve: (r: boolean) => void }): void {
    this.confirmKeywordInput = '';
    confirm.resolve(false);
  }

  onConfirmProceed(confirm: { resolve: (r: boolean) => void }): void {
    this.confirmKeywordInput = '';
    confirm.resolve(true);
  }

  onPromptCancel(prompt: { resolve: (r: string | null) => void }): void {
    this.promptInput = '';
    prompt.resolve(null);
  }

  onPromptProceed(prompt: { resolve: (r: string | null) => void }): void {
    const val = this.promptInput.trim();
    this.promptInput = '';
    prompt.resolve(val);
  }
}
