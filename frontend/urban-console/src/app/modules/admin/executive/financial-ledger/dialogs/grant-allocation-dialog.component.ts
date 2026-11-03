import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { GrantAllocationCreate } from '../../../../../core/models/executive.model';

@Component({
  selector: 'app-grant-allocation-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './grant-allocation-dialog.component.html',
  styleUrl: './grant-allocation-dialog.component.scss'
})
export class GrantAllocationDialogComponent {
  title = input<string>('Record Central / State Grant Allocation');
  save = output<GrantAllocationCreate>();
  cancel = output<void>();

  model: GrantAllocationCreate = {
    grantScheme: '15th Finance Commission (Urban)',
    fundingAuthority: 'Ministry of Finance (MoF)',
    financialYear: 'FY 2026-27',
    sanctionOrderNo: '',
    sanctionOrderDate: new Date().toISOString().substring(0, 10),
    stateTenant: 'Telangana (TG)',
    targetUlb: 'Greater Hyderabad (GHMC)',
    sanctionedAmount: 500000000,
    releasedAmount: 350000000,
    allocationAmount: 350000000,
    releaseDate: new Date().toISOString().substring(0, 10),
    deadline: '2027-03-31',
    grantPurpose: '',
    sanctionDoc: 'Sanction_Order_GO_2026.pdf',
    allocationRemarks: 'Disbursed as per state inter-governmental fiscal devolution formula',
    approvalAuthority: 'Principal Secretary (UDD / Municipal Administration)'
  };

  isValid(): boolean {
    return !!(
      this.model.grantScheme &&
      this.model.fundingAuthority &&
      this.model.financialYear &&
      this.model.sanctionOrderNo &&
      this.model.sanctionOrderDate &&
      this.model.stateTenant &&
      this.model.sanctionedAmount > 0 &&
      this.model.releasedAmount > 0 &&
      this.model.allocationAmount > 0 &&
      this.model.grantPurpose &&
      this.model.approvalAuthority
    );
  }

  saveAllocation(): void {
    if (this.isValid()) {
      this.save.emit({ ...this.model });
    }
  }
}

