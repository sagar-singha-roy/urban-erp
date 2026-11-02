import { TestBed } from '@angular/core/testing';
import { DOCUMENT } from '@angular/common';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { describe, expect, it, beforeEach, afterEach } from 'vitest';
import { environment } from '../../../environments/environment';
import { apiError } from '../models/white-label.model';
import { BrandingThemeService } from './branding-theme.service';

const URL = `${environment.apiUrl}/white-label/public/branding`;
const BRANDING = {
  displayName: 'Test City',
  tagline: null,
  primaryColour: '#112233',
  secondaryColour: '#445566',
  accentColour: null,
  headerBackgroundColour: '#778899',
  sidebarBackgroundColour: null,
  fontFamily: null,
  loginPageTitle: null,
  loginPageMessage: null,
  footerText: null,
  customCss: '.branded { color: #123456; }',
  altText: null,
  assets: {},
};

describe('BrandingThemeService', () => {
  let service: BrandingThemeService;
  let http: HttpTestingController;
  let root: CSSStyleDeclaration;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(BrandingThemeService);
    http = TestBed.inject(HttpTestingController);
    root = TestBed.inject(DOCUMENT).documentElement.style;
  });

  afterEach(() => {
    root.removeProperty('--hake-navy');
    root.removeProperty('--brand-header-bg');
    http.verify();
  });

  it('applies colours, title and custom CSS for a mapped host', async () => {
    const pending = service.init();
    http.expectOne(URL).flush({ success: true, code: 2000, data: BRANDING });
    await pending;
    expect(root.getPropertyValue('--hake-navy')).toBe('#112233');
    expect(root.getPropertyValue('--brand-header-bg')).toBe('#778899');
    expect(TestBed.inject(DOCUMENT).title).toBe('Test City');
    expect(service.branding()?.displayName).toBe('Test City');
  });

  it('keeps the default look when the host has no branding', async () => {
    const pending = service.init();
    http.expectOne(URL).flush({ success: true, code: 2000, data: null });
    await pending;
    expect(service.branding()).toBeNull();
    expect(root.getPropertyValue('--hake-navy')).toBe('');
  });

  it('does not stop the app from starting when the request fails', async () => {
    const pending = service.init();
    http.expectOne(URL).flush('down', { status: 503, statusText: 'Unavailable' });
    await expect(pending).resolves.toBeUndefined();
    expect(service.branding()).toBeNull();
  });
});

describe('apiError', () => {
  it('reads plain and validation errors', () => {
    expect(apiError({ error: { detail: 'Taken' } }, 'x')).toBe('Taken');
    expect(apiError({ error: { detail: [{ msg: 'Value error, Bad colour' }] } }, 'x')).toBe('Bad colour');
    expect(apiError({}, 'fallback')).toBe('fallback');
  });
});
