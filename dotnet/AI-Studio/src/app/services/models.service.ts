import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environment';

@Injectable({ providedIn: 'root' })
export class ModelsService {
  private base = environment.modelsApi;

  constructor(private http: HttpClient) {}

  // Foundry Deployments
  listDeployments() {
    return this.http.get<any>(`${this.base}/api/foundry/models`);
  }
  getDeployment(name: string) {
    return this.http.get<any>(`${this.base}/api/foundry/models/${name}`);
  }
  createDeployment(dto: { modelName: string; deploymentName: string; modelVersion?: string; skuName?: string; skuCapacity?: number }) {
    return this.http.post<any>(`${this.base}/api/foundry/models`, dto);
  }
  patchDeployment(name: string, dto: { skuName?: string; skuCapacity?: number }) {
    return this.http.patch<any>(`${this.base}/api/foundry/models/${name}`, dto);
  }
  deleteDeployment(name: string) {
    return this.http.delete(`${this.base}/api/foundry/models/${name}`);
  }

  // Deployment Requests
  listRequests() {
    return this.http.get<any[]>(`${this.base}/api/DeploymentRequests`);
  }
  getRequest(id: string, projectName: string) {
    return this.http.get<any>(`${this.base}/api/DeploymentRequests/${id}?projectName=${encodeURIComponent(projectName)}`);
  }
  createRequest(dto: any) {
    return this.http.post<any>(`${this.base}/api/DeploymentRequests`, dto);
  }
  approveRequest(id: string, projectName: string, reviewedBy: string) {
    return this.http.put<any>(`${this.base}/api/DeploymentRequests/${id}/approve?projectName=${encodeURIComponent(projectName)}`, { reviewedBy });
  }
  rejectRequest(id: string, projectName: string, reviewedBy: string, rejectionReason?: string) {
    return this.http.put<any>(`${this.base}/api/DeploymentRequests/${id}/reject?projectName=${encodeURIComponent(projectName)}`, { reviewedBy, rejectionReason });
  }
}
