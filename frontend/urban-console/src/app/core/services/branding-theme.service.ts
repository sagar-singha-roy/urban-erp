import { Injectable, inject, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { catchError, firstValueFrom, of } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse, PublicBranding } from '../models/white-label.model';

/** Applies the branding of the site's hostname. Without a mapped domain the default look stays. */
@Injectable({ providedIn: 'root' })
export class BrandingThemeService {
  private http = inject(HttpClient);
  private document = inject(DOCUMENT);

  readonly branding = signal<PublicBranding | null>(null);

  async init(): Promise<void> {
    const response = await firstValueFrom(
      this.http.get<ApiResponse<PublicBranding | null>>(`${environment.apiUrl}/white-label/public/branding`).pipe(catchError(() => of(null))),
    );
    if (response?.data) {
      this.branding.set(response.data);
      this.apply(response.data);
    }
  }

  private apply(branding: PublicBranding): void {
    const root = this.document.documentElement.style;
    const variables: Record<string, string | null> = {
      '--hake-navy': branding.primaryColour,
      '--hake-teal': branding.secondaryColour,
      '--hake-saffron': branding.accentColour,
      '--hake-sidebar': branding.sidebarBackgroundColour,
      '--brand-header-bg': branding.headerBackgroundColour,
      '--font-sans': branding.fontFamily ? `'${branding.fontFamily}', sans-serif` : null,
    };
    for (const [name, value] of Object.entries(variables)) {
      if (value) root.setProperty(name, value);
    }
    this.document.title = branding.displayName;
    if (branding.assets['favicon']) {
      this.document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.setAttribute('href', branding.assets['favicon']);
    }
    if (branding.customCss) {
      // textContent, never innerHTML. The server has already filtered this CSS.
      const style = this.document.createElement('style');
      style.textContent = branding.customCss;
      this.document.head.appendChild(style);
    }
  }
}
