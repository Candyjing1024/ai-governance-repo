using AgentManagementAPI.Models;
using AgentManagementAPI.Services;
using Microsoft.AspNetCore.Mvc;

namespace AgentManagementAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ConversationsController : ControllerBase
{
    private readonly IAgentService _agentService;

    public ConversationsController(IAgentService agentService)
    {
        _agentService = agentService;
    }

    // ========== Conversation CRUD ==========

    /// <summary>
    /// Create a new conversation.
    /// </summary>
    [HttpPost]
    public async Task<IActionResult> CreateThread([FromBody] CreateThreadDto? dto = null)
    {
        var thread = await _agentService.CreateThreadAsync(dto);
        return CreatedAtAction(nameof(GetThread), new { threadId = thread.Id }, thread);
    }

    /// <summary>
    /// Get a conversation by ID.
    /// </summary>
    [HttpGet("{threadId}")]
    public async Task<IActionResult> GetThread(string threadId)
    {
        var thread = await _agentService.GetThreadAsync(threadId);
        return Ok(thread);
    }

    /// <summary>
    /// Delete a conversation by ID.
    /// </summary>
    [HttpDelete("{threadId}")]
    public async Task<IActionResult> DeleteThread(string threadId)
    {
        await _agentService.DeleteThreadAsync(threadId);
        return NoContent();
    }

    // ========== Messages ==========

    /// <summary>
    /// Add a message to a conversation.
    /// </summary>
    [HttpPost("{threadId}/messages")]
    public async Task<IActionResult> CreateMessage(string threadId, [FromBody] CreateMessageDto dto)
    {
        var message = await _agentService.CreateMessageAsync(threadId, dto);
        return Created($"/api/conversations/{threadId}/messages/{message.Id}", message);
    }

    /// <summary>
    /// List all messages in a conversation (chat history).
    /// </summary>
    [HttpGet("{threadId}/messages")]
    public async Task<IActionResult> ListMessages(string threadId)
    {
        var result = await _agentService.ListMessagesAsync(threadId);
        return Ok(result);
    }

    // ========== Runs ==========

    /// <summary>
    /// Run an agent on a conversation. Sends the latest message and returns the response.
    /// </summary>
    [HttpPost("{threadId}/runs")]
    public async Task<IActionResult> CreateRun(string threadId, [FromBody] CreateRunDto dto)
    {
        var run = await _agentService.CreateRunAsync(threadId, dto);
        return Created($"/api/conversations/{threadId}/runs/{run.Id}", run);
    }

    /// <summary>
    /// Get the status of a run.
    /// </summary>
    [HttpGet("{threadId}/runs/{runId}")]
    public async Task<IActionResult> GetRun(string threadId, string runId)
    {
        var run = await _agentService.GetRunAsync(threadId, runId);
        return Ok(run);
    }
}
