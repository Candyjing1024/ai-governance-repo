using AgentManagementAPI.Models;
using AgentManagementAPI.Services;
using Microsoft.AspNetCore.Mvc;

namespace AgentManagementAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AgentsController : ControllerBase
{
    private readonly IAgentService _agentService;

    public AgentsController(IAgentService agentService)
    {
        _agentService = agentService;
    }

    /// <summary>
    /// Health check endpoint.
    /// </summary>
    [HttpGet("health")]
    public IActionResult Health()
    {
        return Ok(new { status = "healthy", service = "AgentManagementAPI" });
    }

    /// <summary>
    /// List all agents in the Foundry project.
    /// </summary>
    [HttpGet]
    public async Task<IActionResult> ListAgents()
    {
        var result = await _agentService.ListAgentsAsync();
        return Ok(result);
    }

    /// <summary>
    /// Get an agent by ID.
    /// </summary>
    [HttpGet("{agentId}")]
    public async Task<IActionResult> GetAgent(string agentId)
    {
        var agent = await _agentService.GetAgentAsync(agentId);
        return Ok(agent);
    }

    /// <summary>
    /// Create a new agent (idempotent — returns existing if name matches).
    /// </summary>
    [HttpPost]
    public async Task<IActionResult> CreateAgent([FromBody] CreateAgentDto dto)
    {
        var agent = await _agentService.CreateAgentAsync(dto);
        return CreatedAtAction(nameof(GetAgent), new { agentId = agent.Id }, agent);
    }

    /// <summary>
    /// Update an existing agent.
    /// </summary>
    [HttpPatch("{agentId}")]
    public async Task<IActionResult> UpdateAgent(string agentId, [FromBody] UpdateAgentDto dto)
    {
        var agent = await _agentService.UpdateAgentAsync(agentId, dto);
        return Ok(agent);
    }

    /// <summary>
    /// Delete an agent by ID.
    /// </summary>
    [HttpDelete("{agentId}")]
    public async Task<IActionResult> DeleteAgent(string agentId)
    {
        await _agentService.DeleteAgentAsync(agentId);
        return NoContent();
    }
}
