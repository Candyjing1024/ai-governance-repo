using Microsoft.AspNetCore.Mvc;
using UserManagementAPI.Models;
using UserManagementAPI.Services;

namespace UserManagementAPI.Controllers;

/// <summary>
/// Manages Entra ID security groups and group membership for access control.
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class GroupsController : ControllerBase
{
    private readonly IGraphService _graphService;

    public GroupsController(IGraphService graphService)
    {
        _graphService = graphService;
    }

    /// <summary>
    /// Create an Entra ID security group (T13). Idempotent — returns existing group if name matches.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(EntraGroup), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(EntraGroup), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateGroup([FromBody] CreateGroupDto dto)
    {
        // Check if group already exists (idempotent)
        var existing = await _graphService.FindGroupByNameAsync(dto.DisplayName);
        if (existing is not null)
            return Ok(existing);

        var group = await _graphService.CreateGroupAsync(dto.DisplayName, dto.Description);
        return CreatedAtAction(nameof(GetGroup), new { groupId = group.Id }, group);
    }

    /// <summary>
    /// Get an Entra ID security group by ID.
    /// </summary>
    [HttpGet("{groupId}")]
    [ProducesResponseType(typeof(EntraGroup), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetGroup(string groupId)
    {
        var group = await _graphService.GetGroupAsync(groupId);
        return Ok(group);
    }

    /// <summary>
    /// List all members of a security group (T16).
    /// </summary>
    [HttpGet("{groupId}/members")]
    [ProducesResponseType(typeof(List<GroupMember>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> ListMembers(string groupId)
    {
        var members = await _graphService.ListGroupMembersAsync(groupId);
        return Ok(members);
    }

    /// <summary>
    /// Add a user to a security group by email (T14). Resolves the user's object ID automatically.
    /// </summary>
    [HttpPost("{groupId}/members")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> AddMember(string groupId, [FromBody] AddGroupMemberDto dto)
    {
        // T14A — Resolve email to user object ID
        var user = await _graphService.GetUserByEmailAsync(dto.UserEmail);

        // T14B — Add user to group
        await _graphService.AddGroupMemberAsync(groupId, user.Id);

        return NoContent();
    }

    /// <summary>
    /// Remove a user from a security group (T15).
    /// </summary>
    [HttpDelete("{groupId}/members/{userId}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> RemoveMember(string groupId, string userId)
    {
        await _graphService.RemoveGroupMemberAsync(groupId, userId);
        return NoContent();
    }
}
