import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GatewayService } from '../../services/gateway.service';
import { UsersService } from '../../services/users.service';
import { ModelsService } from '../../services/models.service';
import { forkJoin, of, catchError } from 'rxjs';

@Component({
  selector: 'app-gateway',
  imports: [FormsModule],
  templateUrl: './gateway.html'
})
export class Gateway implements OnInit {
  tab = signal<'apis' | 'rbac'>('apis');
  apim = signal<any>(null);

  private extractError(e: any): string {
    const err = e.error;
    if (err?.errors) return Object.entries(err.errors).map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`).join('; ');
    return err?.message ?? err?.title ?? 'An error occurred';
  }
  apis = signal<any[]>([]);
  roles = signal<any[]>([]);
  principalNames = signal<Record<string, string>>({});
  loading = signal(true);
  loadingDetail = signal(false);
  error = signal('');

  // API detail
  selectedApi = signal<any>(null);
  operations = signal<any[]>([]);
  policy = signal('');
  policyGroups = signal<string[]>([]);
  groupNames = signal<Record<string, string>>({});

  // Create API form
  showCreate = false;
  newApi = { apiId: '', displayName: '', serviceUrl: '', path: '' };
  creating = false;

  // Policy edit
  editingPolicy = false;
  policyEdit = { audience: '', foundryEndpoint: '', allowedGroups: '' };
  savingPolicy = false;

  // Delete
  confirmDelete = '';
  deleting = false;

  // Model restrictions
  modelRestrictions = signal<any[]>([]);
  showAddRestriction = false;
  newRestriction: { groupId: string; allowedModels: string[] } = { groupId: '', allowedModels: [] };
  addingRestriction = false;
  foundryModels = signal<any[]>([]);
  modelsDropdownOpen = false;
  confirmRemoveRestriction = '';
  removingRestriction = false;

  // RBAC form
  showAssign = false;
  newRole: any = { principalId: '', principalType: 'User', roleName: '', projectName: '', useApimIdentity: false };
  assigning = false;

  constructor(private svc: GatewayService, private usersSvc: UsersService, private modelsSvc: ModelsService) {}

  ngOnInit(): void {
    this.load();
    this.modelsSvc.listDeployments().subscribe({
      next: r => this.foundryModels.set(r.value ?? r ?? []),
      error: () => {}
    });
  }

  load(): void {
    this.loading.set(true);
    this.svc.getApimInstance().subscribe({
      next: r => this.apim.set(r),
      error: () => {}
    });
    this.svc.listApis().subscribe({
      next: r => { this.apis.set(r.value ?? r ?? []); this.loading.set(false); },
      error: e => { this.error.set(e.error?.message ?? 'Failed to load APIs'); this.loading.set(false); }
    });
    this.svc.listRoleAssignments().subscribe({
      next: r => { this.roles.set(r.value ?? r ?? []); this.resolvePrincipalNames(); },
      error: () => {}
    });
  }

  createApi(): void {
    this.creating = true;
    this.svc.createApi(this.newApi).subscribe({
      next: () => { this.showCreate = false; this.creating = false; this.newApi = { apiId: '', displayName: '', serviceUrl: '', path: '' }; this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Create failed'); this.creating = false; }
    });
  }

  deleteApi(id: string): void {
    if (this.confirmDelete !== id) { this.confirmDelete = id; return; }
    this.deleting = true;
    this.svc.deleteApi(id).subscribe({
      next: () => { this.confirmDelete = ''; this.deleting = false; this.selectedApi.set(null); this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Delete failed'); this.deleting = false; this.confirmDelete = ''; }
    });
  }

  cancelDelete(): void { this.confirmDelete = ''; }

  selectApi(api: any): void {
    const id = api.name ?? api.id;
    this.selectedApi.set(api);
    this.loadingDetail.set(true);
    this.operations.set([]);
    this.policy.set('');
    this.policyGroups.set([]);

    forkJoin({
      ops: this.svc.listOperations(id).pipe(catchError(() => of({ value: [] }))),
      pol: this.svc.getPolicy(id).pipe(catchError(() => of(''))),
      grp: this.svc.getPolicyGroups(id).pipe(catchError(() => of([]))),
      models: this.svc.getModelRestrictions(id).pipe(catchError(() => of([])))
    }).subscribe({
      next: ({ ops, pol, grp, models }) => {
        this.operations.set(ops.value ?? ops ?? []);
        this.policy.set(typeof pol === 'string' ? pol : pol.properties?.value ?? JSON.stringify(pol, null, 2));
        const groups: string[] = Array.isArray(grp) ? grp : grp.value ?? [];
        this.policyGroups.set(groups);
        this.resolveGroupNames(groups);
        this.modelRestrictions.set(Array.isArray(models) ? models : []);
        // Resolve group names for model restrictions too
        const restrictionGroupIds = this.modelRestrictions().map((r: any) => r.groupId).filter(Boolean);
        this.resolveGroupNames(restrictionGroupIds);
        this.loadingDetail.set(false);
      },
      error: () => this.loadingDetail.set(false)
    });
  }

  getRoleName(roleDefId: string): string {
    if (!roleDefId) return '—';
    // roleDefinitionId is like /subscriptions/.../roleDefinitions/<guid>
    // Map known GUIDs to friendly names
    const knownRoles: Record<string, string> = {
      'a97b65f3-24c7-4388-baec-2e87135dc908': 'Cognitive Services User',
      '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd': 'Cognitive Services OpenAI User',
      '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68': 'Contributor',
      'acdd72a7-3385-48ef-bd42-f606fba81ae7': 'Reader',
      'b24988ac-6180-42a0-ab88-20f7382dd24c': 'Contributor',
      '8e3af657-a8ff-443c-a75c-2fe8c4bcb635': 'Owner',
    };
    const guid = roleDefId.split('/').pop() ?? '';
    return knownRoles[guid] ?? guid.substring(0, 8) + '…';
  }

  getOperationFullUrl(op: any): string {
    const gatewayUrl = this.apim()?.properties?.gatewayUrl ?? this.apim()?.gatewayUrl ?? '';
    const apiPath = this.selectedApi()?.properties?.path ?? '';
    const urlTemplate = op.properties?.urlTemplate ?? '';
    return `${gatewayUrl}/${apiPath}${urlTemplate}`.replace(/\/+/g, '/').replace(':/', '://');
  }

  resolvePrincipalNames(): void {
    const ids = [...new Set(this.roles().map(r => r.properties?.principalId).filter(Boolean))];
    const names: Record<string, string> = {};
    // We can't look up by ID directly via our users API (it uses email), so we'll use the APIM info for the MI
    const apimPrincipal = this.apim()?.identity?.principalId;
    if (apimPrincipal) {
      names[apimPrincipal] = `${this.apim()?.name} (APIM MI)`;
    }
    this.principalNames.set(names);
  }

  assignRole(): void {
    this.assigning = true;
    this.svc.assignRole(this.newRole).subscribe({
      next: () => { this.showAssign = false; this.assigning = false; this.newRole = { principalId: '', principalType: 'User', roleName: '', projectName: '', useApimIdentity: false }; this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Assign failed'); this.assigning = false; }
    });
  }

  resolveGroupNames(groupIds: string[]): void {
    const names: Record<string, string> = { ...this.groupNames() };
    for (const id of groupIds) {
      if (!names[id]) {
        this.usersSvc.getGroup(id).pipe(catchError(() => of(null))).subscribe(g => {
          if (g?.displayName) {
            this.groupNames.set({ ...this.groupNames(), [id]: g.displayName });
          }
        });
      }
    }
  }

  startEditPolicy(): void {
    // Pre-populate form with existing values
    const groups = this.policyGroups().join(', ');
    // Extract audience from policy XML if available
    const policyXml = this.policy();
    let audience = '';
    let endpoint = '';
    const audMatch = policyXml.match(/<audience>(.*?)<\/audience>/);
    if (audMatch) {
      audience = audMatch[1].replace('api://', '');
    }
    const backendMatch = policyXml.match(/set-backend-service\s+base-url="([^"]+)"/);
    if (backendMatch) {
      endpoint = backendMatch[1];
    }
    this.policyEdit = { audience, foundryEndpoint: endpoint, allowedGroups: groups };
    this.editingPolicy = true;
  }

  cancelEditPolicy(): void {
    this.editingPolicy = false;
  }

  savePolicy(): void {
    const apiId = this.selectedApi()?.name ?? this.selectedApi()?.id;
    if (!apiId) return;
    this.savingPolicy = true;
    const dto: any = { audience: this.policyEdit.audience };
    if (this.policyEdit.foundryEndpoint) dto.foundryEndpoint = this.policyEdit.foundryEndpoint;
    if (this.policyEdit.allowedGroups) dto.allowedGroups = this.policyEdit.allowedGroups.split(',').map((s: string) => s.trim()).filter(Boolean);
    this.svc.setPolicy(apiId, dto).subscribe({
      next: () => { this.editingPolicy = false; this.savingPolicy = false; this.selectApi(this.selectedApi()); },
      error: e => { this.error.set(e.error?.message ?? 'Policy update failed'); this.savingPolicy = false; }
    });
  }

  // ========== Model Restrictions ==========

  toggleModelSelection(modelName: string): void {
    const idx = this.newRestriction.allowedModels.indexOf(modelName);
    if (idx >= 0) {
      this.newRestriction.allowedModels.splice(idx, 1);
    } else {
      this.newRestriction.allowedModels.push(modelName);
    }
  }

  addModelRestriction(): void {
    const apiId = this.selectedApi()?.name ?? this.selectedApi()?.id;
    if (!apiId || !this.newRestriction.groupId || !this.newRestriction.allowedModels.length) return;
    this.addingRestriction = true;
    this.modelsDropdownOpen = false;
    const models = this.newRestriction.allowedModels;
    this.svc.addModelRestriction(apiId, this.newRestriction.groupId, models).subscribe({
      next: () => {
        this.showAddRestriction = false;
        this.addingRestriction = false;
        this.newRestriction = { groupId: '', allowedModels: [] };
        this.selectApi(this.selectedApi());
      },
      error: e => { this.error.set(this.extractError(e)); this.addingRestriction = false; }
    });
  }

  removeModelRestriction(groupId: string): void {
    if (this.confirmRemoveRestriction !== groupId) { this.confirmRemoveRestriction = groupId; return; }
    const apiId = this.selectedApi()?.name ?? this.selectedApi()?.id;
    if (!apiId) return;
    this.removingRestriction = true;
    this.svc.removeModelRestriction(apiId, groupId).subscribe({
      next: () => { this.confirmRemoveRestriction = ''; this.removingRestriction = false; this.selectApi(this.selectedApi()); },
      error: e => { this.error.set(this.extractError(e)); this.removingRestriction = false; this.confirmRemoveRestriction = ''; }
    });
  }

  cancelRemoveRestriction(): void { this.confirmRemoveRestriction = ''; }

  deleteRole(id: string): void {
    if (!confirm('Remove this role assignment?')) return;
    this.svc.deleteRoleAssignment(id).subscribe({
      next: () => this.load(),
      error: e => this.error.set(e.error?.message ?? 'Delete failed')
    });
  }
}
