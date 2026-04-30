using AIGatewayManagementAPI.Models;

namespace AIGatewayManagementAPI.Services;

public interface IRbacService
{
    Task<RoleAssignmentListResponse> ListRoleAssignmentsAsync(string? projectName = null);
    Task<RoleAssignment> AssignRoleAsync(AssignRoleDto dto);
    Task DeleteRoleAssignmentAsync(string assignmentName, string? projectName = null);
}
