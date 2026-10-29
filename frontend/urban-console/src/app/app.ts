import { Component, inject, signal } from '@angular/core';
import { RouterOutlet, RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { KeycloakAuthService } from './core/services/keycloak.service';
import { PropertyService } from './core/services/property.service';
import { AppSwitcherComponent } from './shared/components/app-switcher/app-switcher.component';
import { IconComponent } from './shared/components/icon/icon.component';
import { GlobalDialogsComponent } from './shared/components/dialogs/global-dialogs.component';
import { SuperAdminSidebarComponent } from './shared/components/super-admin-sidebar/super-admin-sidebar.component';
import { TenantInfo } from './core/models/property.model';

@Component({
  imports: [
    RouterOutlet,
    RouterModule,
    CommonModule,
    FormsModule,
    AppSwitcherComponent,
    IconComponent,
    GlobalDialogsComponent,
    SuperAdminSidebarComponent,
  ],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  public authService = inject(KeycloakAuthService);
  public propertyService = inject(PropertyService);
  public router = inject(Router);

  public isMobileSidebarOpen = signal<boolean>(false);
  public isTenantDropdownOpen = signal<boolean>(false);
  public showNewTenantModal = signal<boolean>(false);
  public isSubmittingTenant = signal<boolean>(false);
  public isSuperAdminView = signal<boolean>(false);

  toggleSuperAdminView(): void {
    const next = !this.isSuperAdminView();
    this.isSuperAdminView.set(next);
    if (next) {
      this.router.navigate(['/admin']);
    } else {
      this.router.navigate(['/dashboard']);
    }
  }

  // New SaaS Tenant Onboarding Form Model
  public newTenant = {
    tenantId: '',
    name: '',
    stateCode: 'TG',
    district: '',
  };

  get isAuthPage(): boolean {
    return this.router.url.includes('/login');
  }

  toggleSidebar(): void {
    this.isMobileSidebarOpen.update((v) => !v);
  }

  closeSidebar(): void {
    this.isMobileSidebarOpen.set(false);
  }

  toggleTenantDropdown(): void {
    this.isTenantDropdownOpen.update((v) => !v);
  }

  closeTenantDropdown(): void {
    this.isTenantDropdownOpen.set(false);
  }

  selectTenant(tenant: TenantInfo): void {
    this.authService.switchTenant(tenant);
    this.isTenantDropdownOpen.set(false);
  }

  openNewTenantModal(): void {
    this.isTenantDropdownOpen.set(false);
    this.newTenant = { tenantId: '', name: '', stateCode: 'TG', district: '' };
    this.showNewTenantModal.set(true);
  }

  closeNewTenantModal(): void {
    this.showNewTenantModal.set(false);
  }

  submitNewTenant(): void {
    if (!this.newTenant.tenantId || !this.newTenant.name || !this.newTenant.district) {
      alert('Please fill all required tenant fields.');
      return;
    }

    this.isSubmittingTenant.set(true);
    this.propertyService.createTenant(this.newTenant).subscribe({
      next: (created) => {
        this.isSubmittingTenant.set(false);
        this.showNewTenantModal.set(false);
        this.authService.loadTenants();
        this.authService.switchTenant(created);
      },
      error: (err) => {
        this.isSubmittingTenant.set(false);
        alert(err.error?.detail || 'Failed to provision tenant.');
      },
    });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
