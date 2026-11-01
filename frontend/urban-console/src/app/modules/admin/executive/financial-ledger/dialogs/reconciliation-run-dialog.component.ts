import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';

export interface ReconciliationRunRequest {
  reconciliationName: string;
  financialYear: string;
  stateTenant: string;
  ulb?: string;
  reconciliationType: string;
  sourceLedger: string;
  targetLedger: string;
  periodFrom: string;
  periodTo: string;
  statementFile?: string;
  matchingCriteria: string;
  toleranceAmount?: number;
  remarks?: string;
}

@Component({
  selector: 'app-reconciliation-run-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './reconciliation-run-dialog.component.html',
  styleUrl: './reconciliation-run-dialog.component.scss'
})
export class ReconciliationRunDialogComponent {
  title = input<string>('Initiate Treasury Reconciliation');
  run = output<ReconciliationRunRequest>();
  cancel = output<void>();

  model: ReconciliationRunRequest = {
    reconciliationName: 'RBI e-Kuber BRS Cycle 2026-Q3',
    financialYear: 'FY 2026-27',
    stateTenant: 'Telangana (TG)',
    ulb: '',
    reconciliationType: 'Bank Reconciliation Statement (BRS)',
    sourceLedger: 'State Treasury Pool (Grant Ledger)',
    targetLedger: 'RBI e-Kuber Daily Clearing Scroll',
    periodFrom: '2026-10-01',
    periodTo: '2026-10-31',
    statementFile: 'RBI_eKuber_Disbursement_Scroll_Oct26.csv',
    matchingCriteria: 'UTR + Date Buffer + Exact Amount',
    toleranceAmount: 0,
    remarks: 'Monthly automated statutory clearing for state devolution accounts'
  };

  isValid(): boolean {
    return !!(
      this.model.reconciliationName &&
      this.model.financialYear &&
      this.model.stateTenant &&
      this.model.reconciliationType &&
      this.model.sourceLedger &&
      this.model.targetLedger &&
      this.model.periodFrom &&
      this.model.periodTo &&
      this.model.matchingCriteria
    );
  }

  runRecon(): void {
    if (this.isValid()) {
      this.run.emit({ ...this.model });
    }
  }
}

