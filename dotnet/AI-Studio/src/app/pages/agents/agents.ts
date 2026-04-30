import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AgentsService } from '../../services/agents.service';
import { GatewayService } from '../../services/gateway.service';

@Component({
  selector: 'app-agents',
  imports: [FormsModule],
  templateUrl: './agents.html'
})
export class Agents implements OnInit {
  tab = signal<'agents' | 'playground'>('agents');
  agents = signal<any[]>([]);

  private extractError(e: any): string {
    const err = e.error;
    if (err?.errors) return Object.entries(err.errors).map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`).join('; ');
    return err?.message ?? err?.title ?? 'An error occurred';
  }
  loading = signal(true);
  error = signal('');

  // Create form
  showCreate = false;
  newAgent = { name: '', model: 'gpt-4o-mini', instructions: '', description: '' };
  creating = false;

  // Edit
  editingAgent: any = null;
  editAgentData = { model: '', instructions: '' };
  savingAgent = false;

  // Delete
  confirmDelete = '';
  deleting = false;

  // Playground
  selectedAgent = signal<any>(null);
  threadId = signal('');
  messages = signal<any[]>([]);
  userMessage = '';
  sending = false;
  runStatus = signal('');
  useApim = false;
  apimApis = signal<any[]>([]);
  selectedApimApi = '';

  constructor(private svc: AgentsService, private gatewaySvc: GatewayService) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading.set(true);
    this.svc.listAgents().subscribe({
      next: r => { this.agents.set(r.value ?? r.data ?? []); this.loading.set(false); },
      error: e => { this.error.set(e.error?.message ?? 'Failed to load agents'); this.loading.set(false); }
    });
  }

  createAgent(): void {
    this.creating = true;
    this.svc.createAgent(this.newAgent).subscribe({
      next: () => { this.showCreate = false; this.creating = false; this.newAgent = { name: '', model: 'gpt-4o-mini', instructions: '', description: '' }; this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Create failed'); this.creating = false; }
    });
  }

  deleteAgent(name: string): void {
    if (this.confirmDelete !== name) { this.confirmDelete = name; return; }
    this.deleting = true;
    this.svc.deleteAgent(name).subscribe({
      next: () => { this.confirmDelete = ''; this.deleting = false; this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Delete failed'); this.deleting = false; this.confirmDelete = ''; }
    });
  }

  cancelDelete(): void { this.confirmDelete = ''; }

  startEditAgent(a: any): void {
    this.editingAgent = a;
    this.editAgentData = {
      model: a.model ?? a.versions?.latest?.definition?.model ?? '',
      instructions: a.instructions ?? a.versions?.latest?.definition?.instructions ?? ''
    };
  }

  cancelEditAgent(): void { this.editingAgent = null; }

  saveEditAgent(): void {
    this.savingAgent = true;
    const name = this.editingAgent.name ?? this.editingAgent.id;
    this.svc.updateAgent(name, this.editAgentData).subscribe({
      next: () => { this.editingAgent = null; this.savingAgent = false; this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Update failed'); this.savingAgent = false; }
    });
  }

  openPlayground(agent: any): void {
    this.selectedAgent.set(agent);
    this.threadId.set('');
    this.messages.set([]);
    this.runStatus.set('');
    this.tab.set('playground');
    this.createNewThread();
  }

  createNewThread(): void {
    const create$ = this.useApim && this.selectedApimApi
      ? this.svc.apimCreateThread(this.selectedApimApi)
      : this.svc.createThread();
    create$.subscribe({
      next: (t: any) => this.threadId.set(t.id),
      error: e => this.error.set(this.extractError(e))
    });
  }

  toggleApim(): void {
    this.useApim = !this.useApim;
    // Reset thread for new mode
    this.threadId.set('');
    this.messages.set([]);
    this.runStatus.set('');
    if (this.useApim && this.apimApis().length === 0) {
      this.gatewaySvc.listApis().subscribe({
        next: (r: any) => {
          const list = r.value ?? r ?? [];
          this.apimApis.set(list);
          if (list.length > 0) {
            this.selectedApimApi = list[0].properties?.path ?? list[0].name;
            this.createNewThread();
          }
        },
        error: e => this.error.set(this.extractError(e))
      });
    } else if (this.useApim && this.selectedApimApi) {
      this.createNewThread();
    } else if (!this.useApim && this.selectedAgent()) {
      this.createNewThread();
    }
  }

  onApimApiChange(): void {
    this.threadId.set('');
    this.messages.set([]);
    this.runStatus.set('');
    if (this.selectedApimApi) {
      this.createNewThread();
    }
  }

  sendMessage(): void {
    if (!this.userMessage.trim() || !this.threadId()) return;
    this.sending = true;
    const msg = this.userMessage;
    this.userMessage = '';
    this.messages.update(m => [...m, { role: 'user', content: msg }]);

    const ap = this.selectedApimApi;
    const createMsg$ = this.useApim && ap
      ? this.svc.apimCreateMessage(ap, this.threadId(), msg)
      : this.svc.createMessage(this.threadId(), msg);

    createMsg$.subscribe({
      next: () => {
        const agent = this.selectedAgent();
        const agentId = agent?.name ?? agent?.id;
        const createRun$ = this.useApim && ap
          ? this.svc.apimCreateRun(ap, this.threadId(), agentId)
          : this.svc.createRun(this.threadId(), agentId);

        createRun$.subscribe({
          next: (run: any) => {
            this.runStatus.set(run.status);
            this.pollRun(run.id);
          },
          error: e => { this.error.set(this.extractError(e)); this.sending = false; }
        });
      },
      error: e => { this.error.set(this.extractError(e)); this.sending = false; }
    });
  }

  private pollRun(runId: string): void {
    const ap = this.selectedApimApi;
    const getRun$ = this.useApim && ap
      ? this.svc.apimGetRun(ap, this.threadId(), runId)
      : this.svc.getRun(this.threadId(), runId);

    getRun$.subscribe({
      next: (run: any) => {
        this.runStatus.set(run.status);
        if (run.status === 'completed') {
          this.loadMessages();
        } else if (run.status === 'failed' || run.status === 'cancelled') {
          this.sending = false;
        } else {
          setTimeout(() => this.pollRun(runId), 1500);
        }
      },
      error: () => this.sending = false
    });
  }

  private loadMessages(): void {
    const ap = this.selectedApimApi;
    const listMsgs$ = this.useApim && ap
      ? this.svc.apimListMessages(ap, this.threadId())
      : this.svc.listMessages(this.threadId());

    listMsgs$.subscribe({
      next: (r: any) => {
        const msgs = r.data ?? r.value ?? [];
        this.messages.set(msgs.map((m: any) => ({
          role: m.role,
          content: m.content?.[0]?.text?.value ?? m.content?.[0]?.text ?? m.content ?? ''
        })));
        this.sending = false;
      },
      error: () => this.sending = false
    });
  }
}
