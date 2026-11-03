import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { KeycloakAuthService } from '../services/keycloak.service';
import {
  SESSION_ENDED_DETAIL,
  SUPPORT_SESSION_ENDED,
  supportSession,
} from '../services/support-session.state';

export const authHeaderInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(KeycloakAuthService);
  const router = inject(Router);
  const token = authService.getToken();
  const tenantId = authService.getTenantId();
  const subTenantId = authService.getSubTenantId();

  let headers = req.headers;

  if (token && !headers.has('Authorization')) {
    headers = headers.set('Authorization', `Bearer ${token}`);
  }

  // A support session covers one tenant, so requests made in it carry that tenant only.
  const sessionTenant = supportSession()?.active ? supportSession()?.tenantId : null;
  if (sessionTenant) {
    headers = headers.set('X-Tenant-ID', sessionTenant).delete('X-Sub-Tenant-ID');
  } else {
    if (tenantId && !headers.has('X-Tenant-ID')) {
      headers = headers.set('X-Tenant-ID', tenantId);
    }
    if (subTenantId && !headers.has('X-Sub-Tenant-ID')) {
      headers = headers.set('X-Sub-Tenant-ID', subTenantId);
    }
  }

  // Services still set this from an empty token; the session cookie carries authentication now.
  if (/Bearer (undefined|null)?$/.test(headers.get('Authorization') ?? '')) {
    headers = headers.delete('Authorization');
  }
  headers = headers.set('X-Requested-With', 'SUVIDHA');

  const clonedReq = req.clone({ headers, withCredentials: true });
  return next(clonedReq).pipe(
    catchError((err: unknown) => {
      // A finished support session is not a failed sign-in: the agent stays signed in and the session is cleared.
      if (
        err instanceof HttpErrorResponse &&
        err.status === 401 &&
        err.error?.detail === SESSION_ENDED_DETAIL
      ) {
        window.dispatchEvent(new CustomEvent(SUPPORT_SESSION_ENDED));
        return throwError(() => err);
      }
      if (authService.isAuthenticated() && err instanceof HttpErrorResponse && err.status === 401) {
        authService.logout();
        router.navigate(['/login']);
      }
      return throwError(() => err);
    }),
  );
};
