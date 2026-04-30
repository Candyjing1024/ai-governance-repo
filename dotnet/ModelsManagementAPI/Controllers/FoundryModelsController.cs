using Microsoft.AspNetCore.Mvc;
using ModelsManagementAPI.Models;
using ModelsManagementAPI.Services;

namespace ModelsManagementAPI.Controllers;

/// <summary>
/// Foundry-Direct endpoints. All data fetched from / written to Azure AI Foundry via ARM REST API. No local DB interaction.
/// </summary>
[ApiController]
[Route("api/foundry/models")]
[Produces("application/json")]
public class FoundryModelsController : ControllerBase
{
    private readonly IFoundryModelService _foundryService;

    public FoundryModelsController(IFoundryModelService foundryService)
    {
        _foundryService = foundryService;
    }

    /// <summary>
    /// List all model deployments from Azure AI Foundry.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(FoundryDeploymentListResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> ListDeployments()
    {
        var result = await _foundryService.ListDeploymentsAsync();
        return Ok(result);
    }

    /// <summary>
    /// Get a specific model deployment from Azure AI Foundry.
    /// </summary>
    [HttpGet("{deploymentName}")]
    [ProducesResponseType(typeof(FoundryDeployment), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetDeployment(string deploymentName)
    {
        var result = await _foundryService.GetDeploymentAsync(deploymentName);
        return Ok(result);
    }

    /// <summary>
    /// Create a model deployment directly on Azure AI Foundry.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(FoundryDeployment), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateDeployment([FromBody] CreateFoundryDeploymentDto dto)
    {
        var result = await _foundryService.CreateDeploymentAsync(
            dto.DeploymentName, dto.ModelName, dto.ModelVersion, dto.SkuName, dto.SkuCapacity);
        return Ok(result);
    }

    /// <summary>
    /// Delete a model deployment from Azure AI Foundry.
    /// </summary>
    [HttpDelete("{deploymentName}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteDeployment(string deploymentName)
    {
        await _foundryService.DeleteDeploymentAsync(deploymentName);
        return NoContent();
    }

    /// <summary>
    /// Update an existing model deployment on Azure AI Foundry (SKU name/capacity).
    /// </summary>
    [HttpPatch("{deploymentName}")]
    [ProducesResponseType(typeof(FoundryDeployment), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> PatchDeployment(string deploymentName, [FromBody] PatchFoundryDeploymentDto dto)
    {
        var result = await _foundryService.PatchDeploymentAsync(deploymentName, dto);
        return Ok(result);
    }
}
