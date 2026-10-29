import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IconComponent } from '../icon/icon.component';
import { DialogService } from '../../../core/services/dialog.service';
import {
  SUPER_ADMIN_SECTIONS,
  SuperAdminMenuItem,
  SuperAdminSection,
} from '../../../core/models/super-admin.model';

@Component({
  selector: 'app-super-admin-sidebar',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './super-admin-sidebar.component.html',
  styleUrl: './super-admin-sidebar.component.scss',
})
export class SuperAdminSidebarComponent {
  private router = inject(Router);
  private dialogs = inject(DialogService);

  readonly sections: SuperAdminSection[] = SUPER_ADMIN_SECTIONS;
  readonly openSections = signal<Set<string>>(
    new Set(['intel', 'tenants', 'subscriptions', 'rbac']),
  );
  readonly activeItemId = signal<string>('ADM-A01');

  searchQuery = '';

  isSectionOpen(sectionId: string): boolean {
    return this.openSections().has(sectionId);
  }

  toggleSection(sectionId: string): void {
    const next = new Set(this.openSections());
    if (next.has(sectionId)) {
      next.delete(sectionId);
    } else {
      next.add(sectionId);
    }
    this.openSections.set(next);
  }

  get filteredSections(): SuperAdminSection[] {
    if (!this.searchQuery.trim()) {
      return this.sections;
    }
    const q = this.searchQuery.toLowerCase();
    return this.sections
      .map((sec) => ({
        ...sec,
        items: sec.items.filter(
          (item) =>
            item.title.toLowerCase().includes(q) ||
            item.code.toLowerCase().includes(q) ||
            item.description.toLowerCase().includes(q),
        ),
      }))
      .filter((sec) => sec.items.length > 0);
  }

  selectItem(item: SuperAdminMenuItem): void {
    this.activeItemId.set(item.id);
    const parentSection = this.sections.find((s) => s.items.some((i) => i.id === item.id));
    const secId = parentSection ? parentSection.id : 'intel';

    this.dialogs.showToast(`Accessing ${item.code}: ${item.title} (Level 0 Scope)`, 'info', 2000);

    this.router.navigate(['/admin'], { queryParams: { section: secId, comp: item.code } });
  }
}
