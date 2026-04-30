using Microsoft.AspNetCore.Mvc;
using ProjectManagementAPI.Models;
using ProjectManagementAPI.Services;

namespace ProjectManagementAPI.Controllers;

/// <summary>
/// Manage Azure AI Foundry accounts (AIServices resources) via ARM REST API.
/// </summary>
[ApiController]
[Route("api/foundry/accounts")]
[Produces("application/json")]
public class FoundryAccountsController : ControllerBase
{
    private readonly IFoundryAccountService _service;

    public FoundryAccountsController(IFoundryAccountService service)
    {
        _service = service;
    }

    /// <summary>
    /// List all Foundry accounts (AIServices) in the configured resource group.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(FoundryAccountListResponse), StatusCodes.Status200OK)]
    public async Task<IActionResult> ListAccounts()
    {
        var result = await _service.ListAccountsAsync();
        return Ok(result);
    }

    /// <summary>
    /// Get the configured Foundry account.
    /// </summary>
    [HttpGet("current")]
    [ProducesResponseType(typeof(FoundryAccount), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetAccount()
    {
        var result = await _service.GetAccountAsync();
        return Ok(result);
    }

    /// <summary>
    /// Create the Foundry account (AIServices, kind=AIServices). Idempotent — returns existing if found.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(FoundryAccount), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateAccount([FromBody] CreateFoundryAccountDto dto)
    {
        var result = await _service.CreateAccountAsync(
            dto.Location, dto.Sku, dto.AllowProjectManagement, dto.PublicNetworkAccess);
        return Ok(result);
    }

    /// <summary>
    /// Patch the Foundry account (e.g. enable allowProjectManagement).
    /// </summary>
    [HttpPatch]
    [ProducesResponseType(typeof(FoundryAccount), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> PatchAccount([FromBody] PatchFoundryAccountDto dto)
    {
        var result = await _service.PatchAccountAsync(dto);
        return Ok(result);
    }

    /// <summary>
    /// Delete the Foundry account.
    /// </summary>
    [HttpDelete]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteAccount()
    {
        await _service.DeleteAccountAsync();
        return NoContent();
    }
}
