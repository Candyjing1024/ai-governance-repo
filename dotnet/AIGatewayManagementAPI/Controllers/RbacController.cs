using Microsoft.AspNetCore.Mvc;
using AIGatewayManagementAPI.Models;
using AIGatewayManagementAPI.Services;

namespace AIGatewayManagementAPI.Controllers;

/// <summary>
/// Manages RBAC role assignments on Azure AI Foundry for APIM managed identity and AD groups.
/// </summary>
[ApiController]
[Route("api/gateway/rbac")]
[Produces("application/json")]
public class RbacController : ControllerBase
{
    private readonly IRbacService _rbacService;

    public RbacController(IRbacService rbacService)
    {
        _rbacService = rbacService;
    }

    /// <summary>
    /// List role assignments on the Foundry scope (account or project level).
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(RoleAssignmentListResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> ListRoleAssignments([FromQuery] string? projectName = null)
    {
        var result = await _rbacService.ListRoleAssignmentsAsync(projectName);
        return Ok(result);
    }

    /// <summary>
    /// Assign a role to a principal on the Foundry scope.
    /// Set useApimIdentity=true to auto-fetch the APIM managed identity principal ID.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(RoleAssignment), StatusCodes.Status200OK)]
    public async Task<IActionResult> AssignRole([FromBody] AssignRoleDto dto)
    {
        var result = await _rbacService.AssignRoleAsync(dto);
        return Ok(result);
    }

    /// <summary>
    /// Remove a role assignment by its name (GUID).
    /// </summary>
    [HttpDelete("{assignmentName}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> DeleteRoleAssignment(string assignmentName, [FromQuery] string? projectName = null)
    {
        await _rbacService.DeleteRoleAssignmentAsync(assignmentName, projectName);
        return NoContent();
    }
}
