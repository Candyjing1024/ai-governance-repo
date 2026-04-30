import { Injectable, signal, computed } from '@angular/core';
import { Router } from '@angular/router';

export interface User {
  username: string;
  displayName: string;
  role: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly currentUser = signal<User | null>(this.loadUser());

  readonly user = this.currentUser.asReadonly();
  readonly isLoggedIn = computed(() => this.currentUser() !== null);

  constructor(private router: Router) {}

  login(username: string, password: string): boolean {
    // Simple credential check — replace with real API call in production
    if (username === 'admin' && password === 'admin') {
      const user: User = { username: 'admin', displayName: 'Admin User', role: 'admin' };
      this.currentUser.set(user);
      sessionStorage.setItem('ai_studio_user', JSON.stringify(user));
      return true;
    }
    return false;
  }

  logout(): void {
    this.currentUser.set(null);
    sessionStorage.removeItem('ai_studio_user');
    this.router.navigate(['/login']);
  }

  private loadUser(): User | null {
    const stored = sessionStorage.getItem('ai_studio_user');
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return null;
      }
    }
    return null;
  }
}
