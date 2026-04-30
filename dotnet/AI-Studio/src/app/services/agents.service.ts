import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environment';

@Injectable({ providedIn: 'root' })
export class AgentsService {
  private base = environment.agentsApi;

  constructor(private http: HttpClient) {}

  listAgents() {
    return this.http.get<any>(`${this.base}/api/agents`);
  }
  getAgent(name: string) {
    return this.http.get<any>(`${this.base}/api/agents/${name}`);
  }
  createAgent(dto: { name: string; model: string; instructions: string; description?: string }) {
    return this.http.post<any>(`${this.base}/api/agents`, dto);
  }
  updateAgent(name: string, dto: { model?: string; instructions?: string; description?: string }) {
    return this.http.patch<any>(`${this.base}/api/agents/${name}`, dto);
  }
  deleteAgent(name: string) {
    return this.http.delete(`${this.base}/api/agents/${name}`);
  }

  // Conversations
  createThread(metadata?: Record<string, string>) {
    return this.http.post<any>(`${this.base}/api/conversations`, { metadata });
  }
  getThread(id: string) {
    return this.http.get<any>(`${this.base}/api/conversations/${id}`);
  }

  // Messages
  listMessages(threadId: string) {
    return this.http.get<any>(`${this.base}/api/conversations/${threadId}/messages`);
  }
  createMessage(threadId: string, content: string) {
    return this.http.post<any>(`${this.base}/api/conversations/${threadId}/messages`, { role: 'user', content });
  }

  // Runs
  createRun(threadId: string, assistantId: string) {
    return this.http.post<any>(`${this.base}/api/conversations/${threadId}/runs`, { assistantId });
  }
  getRun(threadId: string, runId: string) {
    return this.http.get<any>(`${this.base}/api/conversations/${threadId}/runs/${runId}`);
  }

  // ========== APIM Gateway Proxy ==========
  apimCreateThread(apiPath: string, metadata?: Record<string, string>) {
    return this.http.post<any>(`${this.base}/api/apim/${apiPath}/conversations`, { metadata });
  }
  apimCreateMessage(apiPath: string, threadId: string, content: string) {
    return this.http.post<any>(`${this.base}/api/apim/${apiPath}/conversations/${threadId}/messages`, { role: 'user', content });
  }
  apimListMessages(apiPath: string, threadId: string) {
    return this.http.get<any>(`${this.base}/api/apim/${apiPath}/conversations/${threadId}/messages`);
  }
  apimCreateRun(apiPath: string, threadId: string, assistantId: string) {
    return this.http.post<any>(`${this.base}/api/apim/${apiPath}/conversations/${threadId}/runs`, { assistantId });
  }
  apimGetRun(apiPath: string, threadId: string, runId: string) {
    return this.http.get<any>(`${this.base}/api/apim/${apiPath}/conversations/${threadId}/runs/${runId}`);
  }
}
