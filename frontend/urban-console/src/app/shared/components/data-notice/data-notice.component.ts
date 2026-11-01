import { Component, input } from '@angular/core';

@Component({
  selector: 'app-data-notice',
  standalone: true,
  templateUrl: './data-notice.component.html',
  styleUrl: './data-notice.component.scss',
})
export class DataNoticeComponent {
  readonly message = input.required<string>();
}
