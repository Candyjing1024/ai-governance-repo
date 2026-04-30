import { Component, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ProjectsService } from '../../services/projects.service';
import { ModelsService } from '../../services/models.service';
import { AgentsService } from '../../services/agents.service';
import { GatewayService } from '../../services/gateway.service';

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit {
  projects = signal<number | null>(null);
  models = signal<number | null>(null);
  agents = signal<number | null>(null);
  apis = signal<number | null>(null);
  requests = signal<number | null>(null);
  recentRequests = signal<any[]>([]);

  constructor(
    private projectsSvc: ProjectsService,
    private modelsSvc: ModelsService,
    private agentsSvc: AgentsService,
    private gatewaySvc: GatewayService
  ) {}

  ngOnInit(): void {
    this.projectsSvc.listProjects().subscribe({
      next: r => this.projects.set(r.value?.length ?? 0),
      error: () => this.projects.set(-1)
    });
    this.modelsSvc.listDeployments().subscribe({
      next: r => this.models.set(r.value?.length ?? 0),
      error: () => this.models.set(-1)
    });
    this.agentsSvc.listAgents().subscribe({
      next: r => {
        const data = r.data ?? r.value ?? r;
        this.agents.set(Array.isArray(data) ? data.length : 0);
      },
      error: () => this.agents.set(-1)
    });
    this.gatewaySvc.listApis().subscribe({
      next: r => this.apis.set(r.value?.length ?? 0),
      error: () => this.apis.set(-1)
    });
    this.modelsSvc.listRequests().subscribe({
      next: r => {
        const list = Array.isArray(r) ? r : [];
        this.requests.set(list.filter((x: any) => x.status === 'requested_pending_approval').length);
        this.recentRequests.set(list.slice(0, 5));
      },
      error: () => this.requests.set(-1)
    });
  }

  countDisplay(val: number | null): string {
    if (val === null) return '…';
    if (val === -1) return '—';
    return val.toString();
  }
}
