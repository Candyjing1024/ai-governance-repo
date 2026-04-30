import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { UsersService } from '../../services/users.service';

@Component({
  selector: 'app-admin',
  imports: [FormsModule],
  templateUrl: './admin.html'
})
export class Admin {
  error = signal('');

  // User lookup
  lookupEmail = '';
  user = signal<any>(null);
  lookingUp = false;

  // Group management
  tab = signal<'lookup' | 'groups'>('lookup');
  groupId = '';
  group = signal<any>(null);
  members = signal<any[]>([]);
  loadingGroup = false;

  // Create group
  showCreateGroup = false;
  newGroup = { displayName: '', description: '', mailNickname: '' };
  creatingGroup = false;

  // Add member
  newMemberEmail = '';
  addingMember = false;

  constructor(private svc: UsersService) {}

  lookupUser(): void {
    if (!this.lookupEmail.trim()) return;
    this.lookingUp = true;
    this.user.set(null);
    this.svc.getUser(this.lookupEmail).subscribe({
      next: r => { this.user.set(r); this.lookingUp = false; },
      error: e => { this.error.set(e.error?.message ?? 'User not found'); this.lookingUp = false; }
    });
  }

  loadGroup(): void {
    if (!this.groupId.trim()) return;
    this.loadingGroup = true;
    this.group.set(null);
    this.members.set([]);
    this.svc.getGroup(this.groupId).subscribe({
      next: r => { this.group.set(r); this.loadingGroup = false; },
      error: e => { this.error.set(e.error?.message ?? 'Group not found'); this.loadingGroup = false; }
    });
    this.svc.listMembers(this.groupId).subscribe({
      next: r => this.members.set(r.value ?? r ?? []),
      error: () => {}
    });
  }

  createGroup(): void {
    this.creatingGroup = true;
    this.svc.createGroup(this.newGroup).subscribe({
      next: r => {
        this.group.set(r);
        this.groupId = r.id;
        this.showCreateGroup = false;
        this.creatingGroup = false;
        this.loadGroup();
      },
      error: e => { this.error.set(e.error?.message ?? 'Create failed'); this.creatingGroup = false; }
    });
  }

  addMember(): void {
    if (!this.newMemberEmail.trim() || !this.groupId) return;
    this.addingMember = true;
    // First look up the user to get their ID
    this.svc.getUser(this.newMemberEmail).subscribe({
      next: (u: any) => {
        this.svc.addMember(this.groupId, u.id).subscribe({
          next: () => { this.newMemberEmail = ''; this.addingMember = false; this.loadGroup(); },
          error: e => { this.error.set(e.error?.message ?? 'Add failed'); this.addingMember = false; }
        });
      },
      error: e => { this.error.set(e.error?.message ?? 'User not found'); this.addingMember = false; }
    });
  }

  removeMember(userId: string): void {
    if (!confirm('Remove this member?')) return;
    this.svc.removeMember(this.groupId, userId).subscribe({
      next: () => this.loadGroup(),
      error: e => this.error.set(e.error?.message ?? 'Remove failed')
    });
  }
}
