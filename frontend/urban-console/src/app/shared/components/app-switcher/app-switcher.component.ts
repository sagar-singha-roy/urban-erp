import { Component, inject, signal, HostListener, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { KeycloakAuthService, ModuleMetadata } from '../../../core/services/keycloak.service';
import { IconComponent } from '../icon/icon.component';

@Component({
  selector: 'app-switcher',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './app-switcher.component.html',
  styleUrl: './app-switcher.component.scss'
})
export class AppSwitcherComponent {
  public authService = inject(KeycloakAuthService);
  private eRef = inject(ElementRef);

  isOpen = signal<boolean>(false);
  searchTerm = '';
  selectedDomain = 'ALL';

  toggleDropdown(): void {
    this.isOpen.set(!this.isOpen());
    if (this.isOpen()) {
      this.searchTerm = '';
      this.selectedDomain = 'ALL';
    }
  }

  closeDropdown(): void {
    this.isOpen.set(false);
  }

  @HostListener('document:click', ['$event'])
  clickOut(event: MouseEvent) {
    if (this.isOpen() && !this.eRef.nativeElement.contains(event.target)) {
      this.closeDropdown();
    }
  }

  get filteredModules(): ModuleMetadata[] {
    const list = this.authService.userModules();
    return list.filter(m => {
      const matchSearch = !this.searchTerm ||
        m.name.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        m.code.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        m.description.toLowerCase().includes(this.searchTerm.toLowerCase());

      const matchDomain = this.selectedDomain === 'ALL' || m.domain.toLowerCase().includes(this.selectedDomain.toLowerCase());

      return matchSearch && matchDomain;
    });
  }

  selectModule(module: ModuleMetadata): void {
    const success = this.authService.switchModule(module);
    if (success) {
      this.closeDropdown();
    }
  }
}
