import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';
import { Layout } from './layout/layout';
import { Login } from './pages/login/login';

export const routes: Routes = [
  { path: 'login', component: Login },
  {
    path: '',
    component: Layout,
    canActivate: [authGuard],
    children: [
      { path: '', loadComponent: () => import('./pages/dashboard/dashboard').then(m => m.Dashboard) },
      { path: 'projects', loadComponent: () => import('./pages/projects/projects').then(m => m.Projects) },
      { path: 'models', loadComponent: () => import('./pages/models/models').then(m => m.Models) },
      { path: 'gateway', loadComponent: () => import('./pages/gateway/gateway').then(m => m.Gateway) },
      { path: 'agents', loadComponent: () => import('./pages/agents/agents').then(m => m.Agents) },
      { path: 'settings', loadComponent: () => import('./pages/settings/settings').then(m => m.Settings) },
      { path: 'admin', loadComponent: () => import('./pages/admin/admin').then(m => m.Admin) },
    ]
  },
  { path: '**', redirectTo: '' }
];
