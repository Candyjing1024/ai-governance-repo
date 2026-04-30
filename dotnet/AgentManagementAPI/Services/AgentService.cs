using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Azure.Core;
using Azure.Identity;
using AgentManagementAPI.Exceptions;
using AgentManagementAPI.Models;

namespace AgentManagementAPI.Services;

public class AgentService : IAgentService
{
    private readonly HttpClient _httpClient;
    private readonly DefaultAzureCredential _credential;
    private readonly string _projectEndpoint;
    private readonly string _agentApiVersion;
    private readonly string _agentScope;
    private readonly ILogger<AgentService> _logger;

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    public AgentService(HttpClient httpClient, IConfiguration configuration, ILogger<AgentService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;

        var tenantId = configuration["AzureFoundry:TenantId"];
        _credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
        {
            TenantId = tenantId,
            ExcludeEnvironmentCredential = true,
            ExcludeManagedIdentityCredential = true,
            ExcludeSharedTokenCacheCredential = true,
            ExcludeWorkloadIdentityCredential = true
        });

        _projectEndpoint = configuration["AgentApi:ProjectEndpoint"]!.TrimEnd('/');
        _agentApiVersion = configuration["AgentApi:ApiVersion"] ?? "2025-05-15-preview";
        _agentScope = configuration["AgentApi:Scope"] ?? "https://ai.azure.com/.default";
    }

    // ========== Agent CRUD ==========

    public async Task<AgentListResponse> ListAgentsAsync()
    {
        var url = $"{_projectEndpoint}/agents?api-version={_agentApiVersion}";

        var response = await SendAgentAsync(HttpMethod.Get, url);
        await EnsureSuccessAsync(response, "list agents");

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<AgentListResponse>(content, _jsonOptions)
            ?? new AgentListResponse();
    }

    public async Task<FoundryAgent> GetAgentAsync(string agentId)
    {
        var url = $"{_projectEndpoint}/agents/{Uri.EscapeDataString(agentId)}?api-version={_agentApiVersion}";

        var response = await SendAgentAsync(HttpMethod.Get, url);
        if (response.StatusCode == HttpStatusCode.NotFound)
            throw new NotFoundException($"Agent '{agentId}' not found.");
        await EnsureSuccessAsync(response, "get agent");

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<FoundryAgent>(content, _jsonOptions)
            ?? throw new NotFoundException($"Agent '{agentId}' not found.");
    }

    public async Task<FoundryAgent> CreateAgentAsync(CreateAgentDto dto)
    {

        // Idempotency: check if agent with same name exists
        var existing = await ListAgentsAsync();
        var match = existing.Data.FirstOrDefault(a =>
            string.Equals(a.Name, dto.Name, StringComparison.OrdinalIgnoreCase));
        if (match is not null)
        {
            _logger.LogInformation("Agent '{Name}' already exists with ID '{Id}'", dto.Name, match.Id);
            return match;
        }

        var body = new
        {
            name = dto.Name,
            description = dto.Description ?? string.Empty,
            definition = new
            {
                kind = dto.Kind,
                model = dto.Model,
                instructions = dto.Instructions ?? string.Empty
            }
        };

        var url = $"{_projectEndpoint}/agents?api-version={_agentApiVersion}";
        var response = await SendAgentAsync(HttpMethod.Post, url, body);
        await EnsureSuccessAsync(response, "create agent");

        var content = await response.Content.ReadAsStringAsync();
        var agent = JsonSerializer.Deserialize<FoundryAgent>(content, _jsonOptions)
            ?? throw new ApiException(HttpStatusCode.BadGateway, "Failed to deserialize agent response.");

        _logger.LogInformation("Created agent '{Name}' with ID '{Id}'", dto.Name, agent.Id);
        return agent;
    }

    public async Task<FoundryAgent> UpdateAgentAsync(string agentId, UpdateAgentDto dto)
    {
        var url = $"{_projectEndpoint}/agents/{Uri.EscapeDataString(agentId)}?api-version={_agentApiVersion}";

        // Get existing agent to merge definition fields
        var existing = await GetAgentAsync(agentId);

        var body = new Dictionary<string, object?>();
        if (dto.Name is not null) body["name"] = dto.Name;
        if (dto.Description is not null) body["description"] = dto.Description;

        // Build definition — merge with existing values
        body["definition"] = new
        {
            kind = existing.Definition?.Kind ?? "prompt",
            model = dto.Model ?? existing.Definition?.Model ?? string.Empty,
            instructions = dto.Instructions ?? existing.Definition?.Instructions
        };

        var response = await SendAgentAsync(HttpMethod.Post, url, body);
        if (response.StatusCode == HttpStatusCode.NotFound)
            throw new NotFoundException($"Agent '{agentId}' not found.");
        await EnsureSuccessAsync(response, "update agent");

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<FoundryAgent>(content, _jsonOptions)
            ?? throw new ApiException(HttpStatusCode.BadGateway, "Failed to deserialize agent response.");
    }

    public async Task DeleteAgentAsync(string agentId)
    {
        var url = $"{_projectEndpoint}/agents/{Uri.EscapeDataString(agentId)}?api-version={_agentApiVersion}";

        var response = await SendAgentAsync(HttpMethod.Delete, url);
        if (response.StatusCode == HttpStatusCode.NotFound)
            throw new NotFoundException($"Agent '{agentId}' not found.");
        await EnsureSuccessAsync(response, "delete agent");

        _logger.LogInformation("Deleted agent '{AgentId}'", agentId);
    }

    // ========== Conversations (V2 — /openai/v1/conversations) ==========

    /// <summary>Base URL for the OpenAI-compatible V2 endpoints.</summary>
    private string OpenAiBase => $"{_projectEndpoint}/openai/v1";

    public async Task<AgentThread> CreateThreadAsync(CreateThreadDto? dto = null)
    {
        var url = $"{OpenAiBase}/conversations";

        // V2 requires a JSON body; send empty object if no metadata
        object body = new { };
        var response = await SendAgentAsync(HttpMethod.Post, url, body);
        await EnsureSuccessAsync(response, "create conversation");

        var content = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(content);
        var root = doc.RootElement;

        return new AgentThread
        {
            Id = root.GetProperty("id").GetString() ?? string.Empty,
            Object = "conversation",
            CreatedAt = root.TryGetProperty("created_at", out var ca) ? ca.GetInt64() : null
        };
    }

    public async Task<AgentThread> GetThreadAsync(string threadId)
    {
        // V2 doesn't have a direct GET conversation endpoint — return the stored ID
        // The conversation exists if runs succeed against it
        return new AgentThread
        {
            Id = threadId,
            Object = "conversation"
        };
    }

    public async Task DeleteThreadAsync(string threadId)
    {
        // V2 conversations are automatically managed; log deletion intent
        _logger.LogInformation("Delete requested for conversation '{ConversationId}' (V2 conversations are managed by the platform)", threadId);
    }

    // ========== Messages ==========

    // In V2, messages are sent as part of the /responses call.
    // We keep a local in-memory message store so the frontend can still
    // call createMessage + listMessages as before.

    private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, List<ThreadMessage>> _messageStore = new();

    public Task<ThreadMessage> CreateMessageAsync(string threadId, CreateMessageDto dto)
    {
        var message = new ThreadMessage
        {
            Id = $"msg_{Guid.NewGuid():N}",
            Object = "message",
            ThreadId = threadId,
            Role = dto.Role,
            Content = [new MessageContent { Type = "text", Text = new MessageText { Value = dto.Content } }],
            CreatedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds()
        };

        _messageStore.AddOrUpdate(threadId,
            _ => [message],
            (_, list) => { lock (list) { list.Add(message); } return list; });

        _logger.LogInformation("Stored message '{MsgId}' on conversation '{ConvId}'", message.Id, threadId);
        return Task.FromResult(message);
    }

    public Task<ThreadMessageListResponse> ListMessagesAsync(string threadId)
    {
        var messages = _messageStore.TryGetValue(threadId, out var list)
            ? list.ToList()
            : [];
        return Task.FromResult(new ThreadMessageListResponse { Data = messages });
    }

    // ========== Runs (V2 — /openai/v1/responses) ==========

    // Store completed runs so GetRunAsync can return them
    private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, ThreadRun> _runStore = new();

    public async Task<ThreadRun> CreateRunAsync(string threadId, CreateRunDto dto)
    {
        var agentName = dto.AssistantId; // The frontend sends the agent name
        var url = $"{OpenAiBase}/responses";

        // Only send the latest user message as input — the conversation ID maintains history
        var lastUserMsg = _messageStore.TryGetValue(threadId, out var msgs)
            ? msgs.LastOrDefault(m => m.Role == "user")
            : null;

        var inputText = lastUserMsg?.Content.FirstOrDefault()?.Text?.Value ?? "";
        var input = new[] { new { role = "user", content = inputText } };

        var body = new Dictionary<string, object?>
        {
            ["agent_reference"] = new { type = "agent_reference", name = agentName },
            ["conversation"] = threadId,
            ["input"] = input
        };
        if (dto.Instructions is not null) body["instructions"] = dto.Instructions;

        var response = await SendAgentAsync(HttpMethod.Post, url, body);
        await EnsureSuccessAsync(response, "create response");

        var content = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(content);
        var root = doc.RootElement;

        // Extract the assistant's text output from the response
        var outputText = ExtractOutputText(root);
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        // Store the assistant's reply as a message
        var assistantMessage = new ThreadMessage
        {
            Id = $"msg_{Guid.NewGuid():N}",
            Object = "message",
            ThreadId = threadId,
            Role = "assistant",
            Content = [new MessageContent { Type = "text", Text = new MessageText { Value = outputText } }],
            CreatedAt = now
        };

        _messageStore.AddOrUpdate(threadId,
            _ => [assistantMessage],
            (_, list) => { lock (list) { list.Add(assistantMessage); } return list; });

        // Build a synthetic run object for the frontend
        var responseId = root.TryGetProperty("id", out var idProp) ? idProp.GetString() ?? $"run_{Guid.NewGuid():N}" : $"run_{Guid.NewGuid():N}";
        var run = new ThreadRun
        {
            Id = responseId,
            Object = "run",
            ThreadId = threadId,
            AgentName = agentName,
            Status = "completed",
            CreatedAt = now,
            CompletedAt = now
        };

        _runStore[responseId] = run;

        _logger.LogInformation("Completed response '{RunId}' on conversation '{ConvId}' with agent '{Agent}'",
            run.Id, threadId, agentName);
        return run;
    }

    /// <summary>Extract text from V2 /responses output array.</summary>
    private static string ExtractOutputText(JsonElement root)
    {
        if (root.TryGetProperty("output_text", out var ot))
            return ot.GetString() ?? "";

        if (root.TryGetProperty("output", out var output) && output.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in output.EnumerateArray())
            {
                // Look for message items with text content
                if (item.TryGetProperty("type", out var t) && t.GetString() == "message"
                    && item.TryGetProperty("content", out var contentArr))
                {
                    foreach (var c in contentArr.EnumerateArray())
                    {
                        if (c.TryGetProperty("type", out var ct) && ct.GetString() == "output_text"
                            && c.TryGetProperty("text", out var txt))
                        {
                            return txt.GetString() ?? "";
                        }
                    }
                }
            }
        }

        return "";
    }

    public Task<ThreadRun> GetRunAsync(string threadId, string runId)
    {
        if (_runStore.TryGetValue(runId, out var run) && run.ThreadId == threadId)
            return Task.FromResult(run);

        throw new NotFoundException($"Run '{runId}' not found on conversation '{threadId}'.");
    }

    // ========== HTTP Helpers ==========

    /// <summary>Send a request to the Foundry Agent data-plane.</summary>
    private async Task<HttpResponseMessage> SendAgentAsync(HttpMethod method, string url, object? body = null)
    {
        var request = new HttpRequestMessage(method, url);
        string? bodyJson = null;
        if (body is not null)
        {
            bodyJson = JsonSerializer.Serialize(body, _jsonOptions);
            request.Content = new StringContent(bodyJson, Encoding.UTF8, "application/json");
        }

        _logger.LogInformation("Foundry API: {Method} {Url}", method, url);
        if (bodyJson is not null)
            _logger.LogDebug("Foundry API body: {Body}", bodyJson[..Math.Min(bodyJson.Length, 500)]);

        var token = await _credential.GetTokenAsync(
            new TokenRequestContext([_agentScope]));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);

        return await _httpClient.SendAsync(request);
    }

    private async Task EnsureSuccessAsync(HttpResponseMessage response, string operation)
    {
        if (response.IsSuccessStatusCode) return;

        var content = await response.Content.ReadAsStringAsync();
        _logger.LogError("Agent API error during {Operation}: {Status} {Content}",
            operation, (int)response.StatusCode, content[..Math.Min(content.Length, 500)]);

        throw response.StatusCode switch
        {
            HttpStatusCode.BadRequest => new BadRequestException($"Bad request during {operation}: {content[..Math.Min(content.Length, 300)]}"),
            HttpStatusCode.NotFound => new NotFoundException($"Not found during {operation}: {content[..Math.Min(content.Length, 300)]}"),
            HttpStatusCode.Conflict => new ConflictException($"Conflict during {operation}."),
            HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden
                => new ApiException(HttpStatusCode.Unauthorized, $"Authentication failed during {operation}. Check credentials and scopes."),
            _ => new ApiException(HttpStatusCode.BadGateway, $"Foundry API error during {operation}: HTTP {(int)response.StatusCode}")
        };
    }
}
