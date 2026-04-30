using Microsoft.AspNetCore.Mvc;
using AIGatewayManagementAPI.Models;
using AIGatewayManagementAPI.Services;

namespace AIGatewayManagementAPI.Controllers;

/// <summary>
/// Manages Azure API Management (APIM) as an AI Gateway for Azure AI Foundry.
/// </summary>
[ApiController]
[Route("api/gateway")]
[Produces("application/json")]
public class ApimController : ControllerBase
{
    private readonly IApimService _apimService;

    public ApimController(IApimService apimService)
    {
        _apimService = apimService;
    }

    /// <summary>
    /// Get APIM instance details (SKU, managed identity, gateway URL).
    /// </summary>
    [HttpGet("apim")]
    [ProducesResponseType(typeof(ApimServiceInfo), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetApimInstance()
    {
        var result = await _apimService.GetApimInstanceAsync();
        return Ok(result);
    }

    /// <summary>
    /// List all APIs in APIM.
    /// </summary>
    [HttpGet("apis")]
    [ProducesResponseType(typeof(ApimApiListResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> ListApis()
    {
        var result = await _apimService.ListApisAsync();
        return Ok(result);
    }

    /// <summary>
    /// Get a specific API from APIM.
    /// </summary>
    [HttpGet("apis/{apiId}")]
    [ProducesResponseType(typeof(ApimApi), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetApi(string apiId)
    {
        var result = await _apimService.GetApiAsync(apiId);
        return Ok(result);
    }

    /// <summary>
    /// Create a Foundry API in APIM with default operations (Steps 3-4 from setup).
    /// Tries azure-ai-foundry type first; falls back to HTTP API with manual operations.
    /// </summary>
    [HttpPost("apis")]
    [ProducesResponseType(typeof(ApimApi), StatusCodes.Status201Created)]
    public async Task<IActionResult> CreateFoundryApi([FromBody] CreateFoundryApiDto dto)
    {
        var result = await _apimService.CreateFoundryApiAsync(dto);
        return CreatedAtAction(nameof(GetApi), new { apiId = dto.ApiId }, result);
    }

    /// <summary>
    /// Delete an API from APIM.
    /// </summary>
    [HttpDelete("apis/{apiId}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteApi(string apiId)
    {
        await _apimService.DeleteApiAsync(apiId);
        return NoContent();
    }

    /// <summary>
    /// List all operations for an API.
    /// </summary>
    [HttpGet("apis/{apiId}/operations")]
    [ProducesResponseType(typeof(ApimOperationListResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> ListOperations(string apiId)
    {
        var result = await _apimService.ListOperationsAsync(apiId);
        return Ok(result);
    }

    /// <summary>
    /// Get the current inbound policy XML for an API.
    /// </summary>
    [HttpGet("apis/{apiId}/policy")]
    [ProducesResponseType(typeof(ApimPolicyResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetPolicy(string apiId)
    {
        var result = await _apimService.GetPolicyAsync(apiId);
        return Ok(result);
    }

    /// <summary>
    /// Apply JWT validation + Managed Identity token swap policy to an API (Step 5 from setup).
    /// Generates full XML policy from structured input.
    /// </summary>
    [HttpPut("apis/{apiId}/policy")]
    [ProducesResponseType(typeof(ApimPolicyResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> SetPolicy(string apiId, [FromBody] SetPolicyDto dto)
    {
        var result = await _apimService.SetPolicyAsync(apiId, dto);
        return Ok(result);
    }

    /// <summary>
    /// List the group IDs currently in the APIM JWT policy for an API.
    /// </summary>
    [HttpGet("apis/{apiId}/policy/groups")]
    [ProducesResponseType(typeof(List<string>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetPolicyGroups(string apiId)
    {
        var groupIds = await _apimService.GetPolicyGroupIdsAsync(apiId);
        return Ok(groupIds);
    }

    /// <summary>
    /// Add a security group to the APIM JWT policy (T17 — grant access).
    /// Read-modify-write: fetches current policy, inserts group ID, PUTs back.
    /// </summary>
    [HttpPut("apis/{apiId}/policy/groups/{groupId}")]
    [ProducesResponseType(typeof(ApimPolicyResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> AddGroupToPolicy(string apiId, string groupId)
    {
        var result = await _apimService.AddGroupToPolicyAsync(apiId, groupId);
        return Ok(result);
    }

    /// <summary>
    /// Remove a security group from the APIM JWT policy (T19 — revoke access).
    /// Read-modify-write: fetches current policy, removes group ID, PUTs back.
    /// </summary>
    [HttpDelete("apis/{apiId}/policy/groups/{groupId}")]
    [ProducesResponseType(typeof(ApimPolicyResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> RemoveGroupFromPolicy(string apiId, string groupId)
    {
        var result = await _apimService.RemoveGroupFromPolicyAsync(apiId, groupId);
        return Ok(result);
    }

    // ========== Model-level restrictions ==========

    /// <summary>
    /// List all model restrictions (group → allowed deployments) in the policy.
    /// </summary>
    [HttpGet("apis/{apiId}/policy/models")]
    [ProducesResponseType(typeof(List<ModelRestrictionDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetModelRestrictions(string apiId)
    {
        var result = await _apimService.GetModelRestrictionsAsync(apiId);
        return Ok(result);
    }

    /// <summary>
    /// Set model restrictions for a group. The group can only access the listed deployments.
    /// If the group already has restrictions, they are replaced.
    /// </summary>
    [HttpPut("apis/{apiId}/policy/models/{groupId}")]
    [ProducesResponseType(typeof(ApimPolicyResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> AddModelRestriction(string apiId, string groupId, [FromBody] ModelRestrictionDto dto)
    {
        var result = await _apimService.AddModelRestrictionAsync(apiId, groupId, dto.AllowedModels);
        return Ok(result);
    }

    /// <summary>
    /// Remove model restrictions for a group (group gets unrestricted access).
    /// </summary>
    [HttpDelete("apis/{apiId}/policy/models/{groupId}")]
    [ProducesResponseType(typeof(ApimPolicyResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> RemoveModelRestriction(string apiId, string groupId)
    {
        var result = await _apimService.RemoveModelRestrictionAsync(apiId, groupId);
        return Ok(result);
    }
}
