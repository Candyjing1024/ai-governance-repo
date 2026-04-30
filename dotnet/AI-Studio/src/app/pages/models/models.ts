import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { ModelsService } from '../../services/models.service';

@Component({
  selector: 'app-models',
  imports: [FormsModule, DatePipe],
  templateUrl: './models.html'
})
export class Models implements OnInit {
  tab = signal<'deployments' | 'requests'>('deployments');

  private extractError(e: any): string {
    const err = e.error;
    if (err?.errors) {
      return Object.entries(err.errors).map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`).join('; ');
    }
    return err?.message ?? err?.title ?? 'An error occurred';
  }
  deployments = signal<any[]>([]);
  requests = signal<any[]>([]);
  loading = signal(true);
  error = signal('');

  // Create deployment form
  showCreate = false;
  newDeploy = { modelName: '', deploymentName: '', modelVersion: '', skuName: 'GlobalStandard', skuCapacity: 10 };
  creating = false;

  // Edit deployment
  editingDeploy: any = null;
  editDeployData = { skuName: '', skuCapacity: 10 };
  savingDeploy = false;

  // Delete
  confirmDelete = '';
  deleting = false;

  // Request form
  showRequest = false;
  newRequest: any = { modelName: '', deploymentName: '', projectName: '', region: 'eastus', businessJustification: '', skuName: 'GlobalStandard', skuCapacity: 10, modelVersion: '', requestGroup: '', requestUser: '' };
  submitting = false;

  constructor(private svc: ModelsService) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading.set(true);
    this.svc.listDeployments().subscribe({
      next: r => { this.deployments.set(r.value ?? []); this.loading.set(false); },
      error: e => { this.error.set(this.extractError(e)); this.loading.set(false); }
    });
    this.svc.listRequests().subscribe({
      next: r => this.requests.set(Array.isArray(r) ? r : []),
      error: () => {}
    });
  }

  createDeployment(): void {
    this.creating = true;
    this.svc.createDeployment(this.newDeploy).subscribe({
      next: () => { this.showCreate = false; this.creating = false; this.load(); },
      error: e => { this.error.set(this.extractError(e)); this.creating = false; }
    });
  }

  deleteDeployment(name: string): void {
    if (this.confirmDelete !== name) { this.confirmDelete = name; return; }
    this.deleting = true;
    this.svc.deleteDeployment(name).subscribe({
      next: () => { this.confirmDelete = ''; this.deleting = false; this.load(); },
      error: e => { this.error.set(this.extractError(e)); this.deleting = false; this.confirmDelete = ''; }
    });
  }

  cancelDelete(): void { this.confirmDelete = ''; }

  startEditDeploy(d: any): void {
    this.editingDeploy = d;
    this.editDeployData = { skuName: d.sku?.name ?? 'GlobalStandard', skuCapacity: d.sku?.capacity ?? 10 };
  }

  cancelEditDeploy(): void { this.editingDeploy = null; }

  saveEditDeploy(): void {
    this.savingDeploy = true;
    this.svc.patchDeployment(this.editingDeploy.name, this.editDeployData).subscribe({
      next: () => { this.editingDeploy = null; this.savingDeploy = false; this.load(); },
      error: e => { this.error.set(this.extractError(e)); this.savingDeploy = false; }
    });
  }

  submitRequest(): void {
    this.submitting = true;
    this.svc.createRequest(this.newRequest).subscribe({
      next: () => { this.showRequest = false; this.submitting = false; this.load(); },
      error: e => { this.error.set(this.extractError(e)); this.submitting = false; }
    });
  }

  // Review modal
  reviewingRequest: any = null;
  reviewAction: 'approve' | 'reject' = 'approve';
  reviewData = { reviewer: '', reason: '' };
  reviewing = false;

  openReview(req: any): void {
    this.reviewingRequest = req;
    this.reviewAction = 'approve';
    this.reviewData = { reviewer: '', reason: '' };
  }

  approve(req: any): void {
    this.reviewingRequest = req;
    this.reviewAction = 'approve';
    this.reviewData = { reviewer: '', reason: '' };
  }

  reject(req: any): void {
    this.reviewingRequest = req;
    this.reviewAction = 'reject';
    this.reviewData = { reviewer: '', reason: '' };
  }

  cancelReview(): void { this.reviewingRequest = null; }

  submitReview(): void {
    this.reviewing = true;
    const req = this.reviewingRequest;
    const obs = this.reviewAction === 'approve'
      ? this.svc.approveRequest(req.id, req.projectName, this.reviewData.reviewer)
      : this.svc.rejectRequest(req.id, req.projectName, this.reviewData.reviewer, this.reviewData.reason);
    obs.subscribe({
      next: () => { this.reviewingRequest = null; this.reviewing = false; this.load(); },
      error: e => { this.error.set(this.extractError(e)); this.reviewing = false; }
    });
  }
}
