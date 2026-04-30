import { Component, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-layout',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './layout.html',
  styleUrl: './layout.scss'
})
export class Layout {
  sidebarCollapsed = signal(false);

  readonly menuItems = [
    { label: 'Projects', icon: 'bi-folder', route: '/projects' },
    { label: 'Models', icon: 'bi-box', route: '/models' },
    { label: 'AI Gateway', icon: 'bi-hdd-network', route: '/gateway' },
    { label: 'Agents', icon: 'bi-robot', route: '/agents' },
    { label: 'Settings', icon: 'bi-gear', route: '/settings' },
    { label: 'Admin', icon: 'bi-shield-lock', route: '/admin' },
  ];

  constructor(public authService: AuthService) {}

  toggleSidebar(): void {
    this.sidebarCollapsed.update(v => !v);
  }
}
