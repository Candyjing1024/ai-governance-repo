using AgentManagementAPI.Models;
using AgentManagementAPI.Services;
using Microsoft.AspNetCore.Mvc;

namespace AgentManagementAPI.Controllers;

/// <summary>
/// Agent playground operations routed through APIM gateway.
/// Mirrors ConversationsController but sends requests via APIM instead of Foundry directly.
/// </summary>
[ApiController]
[Route("api/apim/{apiPath}")]
public class ApimProxyController : ControllerBase
{
    private readonly ApimProxyService _proxy;

    public ApimProxyController(ApimProxyService proxy)
    {
        _proxy = proxy;
    }

    /// <summary>Create a conversation via APIM.</summary>
    [HttpPost("conversations")]
    public async Task<IActionResult> CreateThread(string apiPath, [FromBody] CreateThreadDto? dto = null)
    {
        object body = dto?.Metadata is not null ? new { metadata = dto.Metadata } : new { };
        using var result = await _proxy.CreateThreadAsync(apiPath, body);
        return StatusCode(201, result.RootElement.Clone());
    }

    /// <summary>Create a message via APIM.</summary>
    [HttpPost("conversations/{threadId}/messages")]
    public IActionResult CreateMessage(string apiPath, string threadId, [FromBody] CreateMessageDto dto)
    {
        using var result = _proxy.CreateMessageSync(threadId, dto.Role, dto.Content);
        return Ok(result.RootElement.Clone());
    }

    /// <summary>List messages via APIM.</summary>
    [HttpGet("conversations/{threadId}/messages")]
    public IActionResult ListMessages(string apiPath, string threadId)
    {
        using var result = _proxy.ListMessagesSync(threadId);
        return Ok(result.RootElement.Clone());
    }

    /// <summary>Create a run (V2: POST /responses) via APIM.</summary>
    [HttpPost("conversations/{threadId}/runs")]
    public async Task<IActionResult> CreateRun(string apiPath, string threadId, [FromBody] CreateRunDto dto)
    {
        var agentName = dto.AssistantId;
        using var result = await _proxy.CreateRunAsync(apiPath, threadId, agentName);
        var root = result.RootElement;
        var id = root.TryGetProperty("id", out var idProp) ? idProp.GetString() : $"run_{Guid.NewGuid():N}";
        return Ok(new { id, status = "completed", thread_id = threadId });
    }

    /// <summary>Get run status via APIM.</summary>
    [HttpGet("conversations/{threadId}/runs/{runId}")]
    public IActionResult GetRun(string apiPath, string threadId, string runId)
    {
        using var result = _proxy.GetRunSync(threadId, runId);
        return Ok(result.RootElement.Clone());
    }
}
