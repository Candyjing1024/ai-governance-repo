import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environment';

@Injectable({ providedIn: 'root' })
export class GatewayService {
  private base = environment.gatewayApi;

  constructor(private http: HttpClient) {}

  getApimInstance() {
    return this.http.get<any>(`${this.base}/api/gateway/apim`);
  }
  listApis() {
    return this.http.get<any>(`${this.base}/api/gateway/apis`);
  }
  getApi(apiId: string) {
    return this.http.get<any>(`${this.base}/api/gateway/apis/${apiId}`);
  }
  createApi(dto: { displayName: string; apiId: string; path: string; serviceUrl?: string }) {
    return this.http.post<any>(`${this.base}/api/gateway/apis`, dto);
  }
  deleteApi(apiId: string) {
    return this.http.delete(`${this.base}/api/gateway/apis/${apiId}`);
  }
  listOperations(apiId: string) {
    return this.http.get<any>(`${this.base}/api/gateway/apis/${apiId}/operations`);
  }

  // Policy
  getPolicy(apiId: string) {
    return this.http.get<any>(`${this.base}/api/gateway/apis/${apiId}/policy`);
  }
  setPolicy(apiId: string, dto: { audience: string; allowedGroups?: string[]; foundryEndpoint?: string }) {
    return this.http.put<any>(`${this.base}/api/gateway/apis/${apiId}/policy`, dto);
  }
  getPolicyGroups(apiId: string) {
    return this.http.get<any>(`${this.base}/api/gateway/apis/${apiId}/policy/groups`);
  }
  addGroupToPolicy(apiId: string, groupId: string) {
    return this.http.put<any>(`${this.base}/api/gateway/apis/${apiId}/policy/groups/${groupId}`, {});
  }
  removeGroupFromPolicy(apiId: string, groupId: string) {
    return this.http.delete<any>(`${this.base}/api/gateway/apis/${apiId}/policy/groups/${groupId}`);
  }

  // Model restrictions
  getModelRestrictions(apiId: string) {
    return this.http.get<any[]>(`${this.base}/api/gateway/apis/${apiId}/policy/models`);
  }
  addModelRestriction(apiId: string, groupId: string, allowedModels: string[]) {
    return this.http.put<any>(`${this.base}/api/gateway/apis/${apiId}/policy/models/${groupId}`, { groupId, allowedModels });
  }
  removeModelRestriction(apiId: string, groupId: string) {
    return this.http.delete<any>(`${this.base}/api/gateway/apis/${apiId}/policy/models/${groupId}`);
  }

  // RBAC
  listRoleAssignments(projectName?: string) {
    const q = projectName ? `?projectName=${encodeURIComponent(projectName)}` : '';
    return this.http.get<any>(`${this.base}/api/gateway/rbac${q}`);
  }
  assignRole(dto: { principalId?: string; principalType: string; roleName: string; projectName?: string; useApimIdentity?: boolean }) {
    return this.http.post<any>(`${this.base}/api/gateway/rbac`, dto);
  }
  deleteRoleAssignment(name: string, projectName?: string) {
    const q = projectName ? `?projectName=${encodeURIComponent(projectName)}` : '';
    return this.http.delete(`${this.base}/api/gateway/rbac/${name}${q}`);
  }
}
