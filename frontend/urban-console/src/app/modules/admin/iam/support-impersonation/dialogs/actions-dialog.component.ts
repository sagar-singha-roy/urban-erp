import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { WlPaginationComponent } from '../../../../../shared/components/wl-pagination/wl-pagination.component';
import { ImpersonationService } from '../../../../../core/services/impersonation.service';
import { AuditEntry, SessionAction } from '../../../../../core/models/impersonation.model';
import { asUtc } from '../../cross-tenant-access/cross-tenant-utils';

/** Tab 5: every request made during one session. Request bodies are never stored. */
@Component({
  selector: 'app-imp-actions-dialog',
  standalone: true,
  imports: [CommonModule, IconComponent, WlPaginationComponent],
  template: `
    <div class="dialog-overlay" (click)="closed.emit()">
      <div
        class="dialog-card"
        (click)="$event.stopPropagation()"
        role="dialog"
        aria-modal="true"
        aria-labelledby="imp-actions-title"
      >
        <div class="dialog-header">
          <div>
            <h3 id="imp-actions-title">Actions Performed: {{ entry.sessionNumber }}</h3>
            <p>
              {{ entry.supportEmail }} acting as {{ entry.targetEmail }} in {{ entry.tenantId }}.
            </p>
          </div>
          <button
            type="button"
            class="close-btn"
            (click)="closed.emit()"
            title="Close dialog"
            aria-label="Close dialog"
          >
            <app-icon name="ri-close-line" [size]="18"></app-icon>
          </button>
        </div>
        <div class="wl-scroll">
          <table class="wl-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Request</th>
                <th>Permission Asked</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              @for (a of actions(); track $index) {
                <tr>
                  <td>{{ asUtc(a.createdAt) | date: 'mediumTime' }}</td>
                  <td class="clip">{{ a.method }} {{ a.path }}</td>
                  <td>{{ a.permission ?? '-' }}</td>
                  <td>
                    <span class="wl-status" [ngClass]="a.statusCode < 400 ? 'good' : 'bad'"
                      >{{ a.statusCode < 400 ? 'Allowed' : 'Refused' }} ({{ a.statusCode }})</span
                    >
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="4" class="wl-empty">No activity was recorded for this session.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <app-wl-pagination
          [page]="page()"
          [limit]="limit()"
          [total]="total()"
          (pageChange)="page.set($event); load()"
          (limitChange)="limit.set($event); page.set(1); load()"
        ></app-wl-pagination>
      </div>
    </div>
  `,
  styleUrl: '../hub.scss',
})
export class ActionsDialogComponent implements OnInit {
  @Input({ required: true }) entry!: AuditEntry;
  @Output() closed = new EventEmitter<void>();

  private service = inject(ImpersonationService);
  readonly asUtc = asUtc;
  readonly actions = signal<SessionAction[]>([]);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly limit = signal(10);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.service
      .listActions(this.entry.sessionId, {
        skip: (this.page() - 1) * this.limit(),
        limit: this.limit(),
      })
      .subscribe({
        next: (res) => {
          this.actions.set(res.data);
          this.total.set(res.total);
        },
      });
  }
}
