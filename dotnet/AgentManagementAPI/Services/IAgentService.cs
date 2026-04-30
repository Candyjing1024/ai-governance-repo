using AgentManagementAPI.Models;

namespace AgentManagementAPI.Services;

public interface IAgentService
{
    // ========== Agent CRUD ==========

    /// <summary>List all agents in the Foundry project.</summary>
    Task<AgentListResponse> ListAgentsAsync();

    /// <summary>Get an agent by ID.</summary>
    Task<FoundryAgent> GetAgentAsync(string agentId);

    /// <summary>Create a new agent (idempotent — returns existing if name matches).</summary>
    Task<FoundryAgent> CreateAgentAsync(CreateAgentDto dto);

    /// <summary>Update an existing agent.</summary>
    Task<FoundryAgent> UpdateAgentAsync(string agentId, UpdateAgentDto dto);

    /// <summary>Delete an agent by ID.</summary>
    Task DeleteAgentAsync(string agentId);

    // ========== Conversations (V2) ==========

    /// <summary>Create a new conversation.</summary>
    Task<AgentThread> CreateThreadAsync(CreateThreadDto? dto = null);

    /// <summary>Get a conversation by ID.</summary>
    Task<AgentThread> GetThreadAsync(string threadId);

    /// <summary>Delete a conversation by ID.</summary>
    Task DeleteThreadAsync(string threadId);

    // ========== Messages ==========

    /// <summary>Add a user message to a conversation (stored locally for history).</summary>
    Task<ThreadMessage> CreateMessageAsync(string threadId, CreateMessageDto dto);

    /// <summary>List messages in a conversation.</summary>
    Task<ThreadMessageListResponse> ListMessagesAsync(string threadId);

    // ========== Runs (V2 — synchronous /responses call) ==========

    /// <summary>Send conversation to agent via /responses and return the result as a synthetic run.</summary>
    Task<ThreadRun> CreateRunAsync(string threadId, CreateRunDto dto);

    /// <summary>Get a previously completed run by ID.</summary>
    Task<ThreadRun> GetRunAsync(string threadId, string runId);
}
