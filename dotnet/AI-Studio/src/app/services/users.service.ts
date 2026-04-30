import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environment';

@Injectable({ providedIn: 'root' })
export class UsersService {
  private base = environment.usersApi;

  constructor(private http: HttpClient) {}

  getUser(email: string) {
    return this.http.get<any>(`${this.base}/api/users/${encodeURIComponent(email)}`);
  }

  // Groups
  createGroup(dto: { displayName: string; description?: string }) {
    return this.http.post<any>(`${this.base}/api/groups`, dto);
  }
  getGroup(groupId: string) {
    return this.http.get<any>(`${this.base}/api/groups/${groupId}`);
  }
  listMembers(groupId: string) {
    return this.http.get<any>(`${this.base}/api/groups/${groupId}/members`);
  }
  addMember(groupId: string, userEmail: string) {
    return this.http.post(`${this.base}/api/groups/${groupId}/members`, { userEmail }, { observe: 'response' });
  }
  removeMember(groupId: string, userId: string) {
    return this.http.delete(`${this.base}/api/groups/${groupId}/members/${userId}`);
  }
}
