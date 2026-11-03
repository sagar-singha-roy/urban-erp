import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { loadingInterceptor } from '../../../core/interceptors/loading.interceptor';
import { DialogService } from '../../../core/services/dialog.service';
import { RefreshButtonComponent } from './refresh-button.component';

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

describe('RefreshButtonComponent', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let dialogs: DialogService;

  function create() {
    const fixture = TestBed.createComponent(RefreshButtonComponent);
    fixture.componentRef.setInput('subject', 'audit vault');
    fixture.componentInstance.refresh.subscribe(() => {
      http.get('/data').subscribe({ error: () => dialogs.showToast('Page level failure', 'error') });
      dialogs.showToast('Page level success', 'success');
    });
    fixture.detectChanges();
    return fixture;
  }

  const messages = () => dialogs.toasts().map((toast) => `${toast.type}: ${toast.message}`);

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RefreshButtonComponent],
      providers: [provideHttpClient(withInterceptors([loadingInterceptor])), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
    dialogs = TestBed.inject(DialogService);
  });

  it('stays busy until requests finish and reports one success', async () => {
    const fixture = create();
    fixture.componentInstance.run();
    await wait(200);
    expect(fixture.componentInstance.isRefreshing()).toBe(true);

    backend.expectOne('/data').flush({});
    await wait(200);

    expect(fixture.componentInstance.isRefreshing()).toBe(false);
    expect(messages()).toEqual(['success: Audit vault refreshed.']);
  });

  it('reports one failure when a request fails', async () => {
    const fixture = create();
    fixture.componentInstance.run();

    backend.expectOne('/data').flush('nope', { status: 500, statusText: 'Server Error' });
    await wait(200);

    expect(fixture.componentInstance.isRefreshing()).toBe(false);
    expect(messages()).toEqual(['error: Audit vault could not be fully refreshed. Some data may be out of date.']);
  });

  it('ignores clicks while already refreshing', async () => {
    const fixture = create();
    fixture.componentInstance.run();
    fixture.componentInstance.run();

    backend.expectOne('/data').flush({});
    await wait(200);
    expect(messages().length).toBe(1);
  });

  it('allows page toasts again after finishing', async () => {
    const fixture = create();
    fixture.componentInstance.run();
    backend.expectOne('/data').flush({});
    await wait(200);

    dialogs.showToast('Saved', 'success');
    expect(messages()).toContain('success: Saved');
  });
});
