using Microsoft.AspNetCore.Mvc;
using UserManagementAPI.Models;
using UserManagementAPI.Services;

namespace UserManagementAPI.Controllers;

/// <summary>
/// Looks up Entra ID users by email for group membership operations.
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class UsersController : ControllerBase
{
    private readonly IGraphService _graphService;

    public UsersController(IGraphService graphService)
    {
        _graphService = graphService;
    }

    /// <summary>
    /// Health check endpoint.
    /// </summary>
    [HttpGet("health")]
    public IActionResult Health()
    {
        return Ok(new { status = "healthy", service = "UserManagementAPI" });
    }

    /// <summary>
    /// Look up an Entra ID user by email/UPN (T14A). Supports both direct UPN and guest users.
    /// </summary>
    [HttpGet("{email}")]
    [ProducesResponseType(typeof(EntraUser), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetByEmail(string email)
    {
        var user = await _graphService.GetUserByEmailAsync(email);
        return Ok(user);
    }
}
