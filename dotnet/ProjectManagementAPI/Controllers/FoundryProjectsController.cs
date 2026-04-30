using Microsoft.AspNetCore.Mvc;
using ProjectManagementAPI.Models;
using ProjectManagementAPI.Services;

namespace ProjectManagementAPI.Controllers;

/// <summary>
/// Manage projects under the configured Azure AI Foundry account via ARM REST API.
/// </summary>
[ApiController]
[Route("api/foundry/projects")]
[Produces("application/json")]
public class FoundryProjectsController : ControllerBase
{
    private readonly IFoundryAccountService _service;

    public FoundryProjectsController(IFoundryAccountService service)
    {
        _service = service;
    }

    /// <summary>
    /// List all projects under the configured Foundry account.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(FoundryProjectListResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> ListProjects()
    {
        var result = await _service.ListProjectsAsync();
        return Ok(result);
    }

    /// <summary>
    /// Get a specific project by name.
    /// </summary>
    [HttpGet("{projectName}")]
    [ProducesResponseType(typeof(FoundryProject), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetProject(string projectName)
    {
        var result = await _service.GetProjectAsync(projectName.Trim());
        return Ok(result);
    }

    /// <summary>
    /// Create a project under the configured Foundry account. Idempotent — returns existing if found.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(FoundryProject), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateProject([FromBody] CreateFoundryProjectDto dto)
    {
        var result = await _service.CreateProjectAsync(
            dto.ProjectName.Trim(), dto.Location.Trim(), dto.DisplayName?.Trim(), dto.Description?.Trim());
        return Ok(result);
    }

    /// <summary>
    /// Update a project's properties (displayName, description).
    /// </summary>
    [HttpPatch("{projectName}")]
    [ProducesResponseType(typeof(FoundryProject), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> PatchProject(string projectName, [FromBody] PatchFoundryProjectDto dto)
    {
        var result = await _service.PatchProjectAsync(projectName.Trim(), dto);
        return Ok(result);
    }

    /// <summary>
    /// Delete a project from the configured Foundry account.
    /// </summary>
    [HttpDelete("{projectName}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteProject(string projectName)
    {
        await _service.DeleteProjectAsync(projectName.Trim());
        return NoContent();
    }
}
