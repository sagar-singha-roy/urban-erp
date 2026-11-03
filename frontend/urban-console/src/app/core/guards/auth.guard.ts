import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { KeycloakAuthService } from '../services/keycloak.service';

export const authGuard: CanActivateFn = (_route, state) => {
  const authService = inject(KeycloakAuthService);
  const router = inject(Router);
  if (authService.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

export const superAdminGuard: CanActivateFn = (route, state) => {
  const authService = inject(KeycloakAuthService);
  const router = inject(Router);
  if (!authService.isAuthenticated()) {
    return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
  }
  return authService.isSuperAdmin() ? true : router.createUrlTree(['/dashboard']);
};
