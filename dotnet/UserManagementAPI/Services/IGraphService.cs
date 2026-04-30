using UserManagementAPI.Models;

namespace UserManagementAPI.Services;

public interface IGraphService
{
    // T13 — Create Entra security group
    Task<EntraGroup> CreateGroupAsync(string displayName, string? description);

    // T13 — Get group by ID
    Task<EntraGroup> GetGroupAsync(string groupId);

    // T13 — Lookup group by display name (idempotent create support)
    Task<EntraGroup?> FindGroupByNameAsync(string displayName);

    // T14A — Look up user by email (UPN or mail)
    Task<EntraUser> GetUserByEmailAsync(string email);

    // T14B — Add user to group
    Task AddGroupMemberAsync(string groupId, string userId);

    // T15 — Remove user from group
    Task RemoveGroupMemberAsync(string groupId, string userId);

    // T16 — List group members
    Task<List<GroupMember>> ListGroupMembersAsync(string groupId);
}
