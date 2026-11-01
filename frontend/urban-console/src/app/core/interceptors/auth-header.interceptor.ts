import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { KeycloakAuthService } from '../services/keycloak.service';

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

  if (tenantId && !headers.has('X-Tenant-ID')) {
    headers = headers.set('X-Tenant-ID', tenantId);
  }

  if (subTenantId && !headers.has('X-Sub-Tenant-ID')) {
    headers = headers.set('X-Sub-Tenant-ID', subTenantId);
  }

  const clonedReq = req.clone({ headers });
  return next(clonedReq).pipe(
    catchError((err: unknown) => {
      if (token && err instanceof HttpErrorResponse && err.status === 401) {
        authService.logout();
        router.navigate(['/login']);
      }
      return throwError(() => err);
    }),
  );
};

