import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../../services/projects.service';

@Component({
  selector: 'app-projects',
  imports: [FormsModule],
  templateUrl: './projects.html'
})
export class Projects implements OnInit {
  account = signal<any>(null);
  projects = signal<any[]>([]);

  private extractError(e: any): string {
    const err = e.error;
    if (err?.errors) return Object.entries(err.errors).map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`).join('; ');
    return err?.message ?? err?.title ?? 'An error occurred';
  }
  loading = signal(true);
  error = signal('');

  // Create form
  showCreate = false;
  newProject = { projectName: '', location: 'eastus', displayName: '', description: '' };
  creating = false;

  // Edit
  editingProject: any = null;
  editData = { displayName: '', description: '' };
  saving = false;

  // Delete
  confirmDelete = '';
  deleting = false;

  constructor(private svc: ProjectsService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.svc.getAccount().subscribe({
      next: r => this.account.set(r),
      error: () => {}
    });
    this.svc.listProjects().subscribe({
      next: r => { this.projects.set(r.value ?? []); this.loading.set(false); },
      error: e => { this.error.set(e.error?.message ?? 'Failed to load projects'); this.loading.set(false); }
    });
  }

  create(): void {
    this.creating = true;
    this.svc.createProject(this.newProject).subscribe({
      next: () => { this.showCreate = false; this.creating = false; this.newProject = { projectName: '', location: 'eastus', displayName: '', description: '' }; this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Create failed'); this.creating = false; }
    });
  }

  projectName(fullName: string): string {
    return fullName.includes('/') ? fullName.split('/').pop()! : fullName;
  }

  deleteProject(name: string): void {
    const short = this.projectName(name);
    if (this.confirmDelete !== name) { this.confirmDelete = name; return; }
    this.deleting = true;
    this.svc.deleteProject(short).subscribe({
      next: () => { this.confirmDelete = ''; this.deleting = false; this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Delete failed'); this.deleting = false; this.confirmDelete = ''; }
    });
  }

  cancelDelete(): void { this.confirmDelete = ''; }

  startEdit(p: any): void {
    this.editingProject = p;
    this.editData = {
      displayName: p.properties?.displayName ?? '',
      description: p.properties?.description ?? ''
    };
  }

  cancelEdit(): void {
    this.editingProject = null;
  }

  saveEdit(): void {
    this.saving = true;
    const name = this.projectName(this.editingProject.name);
    this.svc.patchProject(name, this.editData).subscribe({
      next: () => { this.editingProject = null; this.saving = false; this.load(); },
      error: e => { this.error.set(e.error?.message ?? 'Update failed'); this.saving = false; }
    });
  }
}
