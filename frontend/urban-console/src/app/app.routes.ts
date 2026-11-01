import { Routes } from '@angular/router';
import { DashboardComponent } from './modules/dashboard/dashboard.component';
import { AuthComponent } from './modules/auth/auth.component';
import { AdminDashboardComponent } from './modules/admin/admin-dashboard.component';
import { authGuard, superAdminGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'admin', pathMatch: 'full' },
  { path: 'login', component: AuthComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'admin', component: AdminDashboardComponent, canActivate: [superAdminGuard] },
  { path: 'admin/:section', component: AdminDashboardComponent, canActivate: [superAdminGuard] },
  { path: 'admin/:section/:sub', component: AdminDashboardComponent, canActivate: [superAdminGuard] },
  { path: '**', redirectTo: 'admin' }
];
