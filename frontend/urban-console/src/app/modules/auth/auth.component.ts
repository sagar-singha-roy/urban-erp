import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { KeycloakAuthService } from '../../core/services/keycloak.service';
import { IconComponent } from '../../shared/components/icon/icon.component';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './auth.component.html',
  styleUrl: './auth.component.scss',
})
export class AuthComponent {
  private authService = inject(KeycloakAuthService);
  private router = inject(Router);

  isSignUp = signal<boolean>(false);
  isLoading = signal<boolean>(false);
  errorMessage = signal<string>('');
  successMessage = signal<string>('');

  // Production Sign In Form Model
  signInData = {
    username_or_email: '',
    password: '',
  };

  // User Registration Form Model
  signUpData = {
    full_name: '',
    email: '',
    username: '',
    password: '',
    role: 'citizen',
    assigned_zone: '',
    assigned_ward: '',
  };

  toggleMode(signUp: boolean): void {
    this.isSignUp.set(signUp);
    this.errorMessage.set('');
    this.successMessage.set('');
  }

  private extractErrorMessage(err: any, fallback: string): string {
    if (!err) return fallback;
    const detail = err.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: any) => {
          if (typeof d === 'string') return d;
          if (d?.msg) {
            const loc = Array.isArray(d.loc)
              ? d.loc.filter((l: string) => l !== 'body').join('.')
              : '';
            return loc ? `${loc}: ${d.msg}` : d.msg;
          }
          return JSON.stringify(d);
        })
        .join(', ');
    }
    if (typeof detail === 'object' && detail !== null) {
      return detail.msg || detail.message || JSON.stringify(detail);
    }
    if (typeof err.error === 'string') return err.error;
    if (err.message && typeof err.message === 'string') return err.message;
    return fallback;
  }

  onSignIn(): void {
    const identifier = this.signInData.username_or_email?.trim();
    const password = this.signInData.password?.trim();

    if (!identifier || !password) {
      this.errorMessage.set('Please provide both official email/username and password.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.authService.signIn({ username_or_email: identifier, password }).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(
          this.extractErrorMessage(err, 'Authentication failed. Please verify credentials.'),
        );
      },
    });
  }

  onSignUp(): void {
    if (
      !this.signUpData.full_name?.trim() ||
      !this.signUpData.email?.trim() ||
      !this.signUpData.username?.trim() ||
      !this.signUpData.password?.trim()
    ) {
      this.errorMessage.set('Please complete all required fields.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.authService.signUp(this.signUpData).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.successMessage.set('Account provisioned successfully. Redirecting to workspace...');
        setTimeout(() => {
          this.router.navigate(['/dashboard']);
        }, 800);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(
          this.extractErrorMessage(err, 'Registration failed. Please review inputs.'),
        );
      },
    });
  }
}
