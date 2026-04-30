import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environment';

@Injectable({ providedIn: 'root' })
export class ProjectsService {
  private base = environment.projectsApi;

  constructor(private http: HttpClient) {}

  // Accounts
  listAccounts() {
    return this.http.get<any>(`${this.base}/api/foundry/accounts`);
  }
  getAccount() {
    return this.http.get<any>(`${this.base}/api/foundry/accounts/current`);
  }

  // Projects
  listProjects() {
    return this.http.get<any>(`${this.base}/api/foundry/projects`);
  }
  getProject(name: string) {
    return this.http.get<any>(`${this.base}/api/foundry/projects/${name}`);
  }
  createProject(dto: { projectName: string; location: string; displayName?: string; description?: string }) {
    return this.http.post<any>(`${this.base}/api/foundry/projects`, dto);
  }
  patchProject(name: string, dto: { displayName?: string; description?: string }) {
    return this.http.patch<any>(`${this.base}/api/foundry/projects/${name}`, dto);
  }
  deleteProject(name: string) {
    return this.http.delete(`${this.base}/api/foundry/projects/${name}`);
  }
}
