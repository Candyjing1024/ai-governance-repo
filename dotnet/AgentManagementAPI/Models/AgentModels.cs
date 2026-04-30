using System.Text.Json.Serialization;

namespace AgentManagementAPI.Models;

// ========== Agent Models ==========

public class FoundryAgent
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public FoundryAgentVersions? Versions { get; set; }
    public FoundryAgentEndpoint? AgentEndpoint { get; set; }

    // Convenience accessors that pull from versions.latest
    [JsonIgnore] public string? Model => Versions?.Latest?.Definition?.Model;
    [JsonIgnore] public string? Instructions => Versions?.Latest?.Definition?.Instructions;
    [JsonIgnore] public AgentDefinition? Definition => Versions?.Latest?.Definition;
    [JsonIgnore] public string? Description => Versions?.Latest?.Description;
    [JsonIgnore] public Dictionary<string, object>? Metadata => Versions?.Latest?.Metadata;
    [JsonIgnore] public long? CreatedAt => Versions?.Latest?.CreatedAt;
    [JsonIgnore] public string? Status => Versions?.Latest?.Status;
}

public class FoundryAgentVersions
{
    public FoundryAgentVersion? Latest { get; set; }
}

public class FoundryAgentVersion
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string? Version { get; set; }
    public string? Description { get; set; }
    public long? CreatedAt { get; set; }
    public AgentDefinition? Definition { get; set; }
    public string? Status { get; set; }
    public Dictionary<string, object>? Metadata { get; set; }
}

public class AgentDefinition
{
    public string Kind { get; set; } = "prompt";
    public string Model { get; set; } = string.Empty;
    public string? Instructions { get; set; }
}

public class FoundryAgentEndpoint
{
    public FoundryVersionSelector? VersionSelector { get; set; }
    public List<string>? Protocols { get; set; }
}

public class FoundryVersionSelector
{
    public List<FoundryVersionSelectionRule>? VersionSelectionRules { get; set; }
}

public class FoundryVersionSelectionRule
{
    public string? Type { get; set; }
    public string? AgentVersion { get; set; }
    public int? TrafficPercentage { get; set; }
}

public class AgentListResponse
{
    public List<FoundryAgent> Data { get; set; } = [];
}

// ========== Conversation Models (V2 API) ==========

/// <summary>Represents a V2 conversation (replaces classic thread).</summary>
public class AgentThread
{
    public string Id { get; set; } = string.Empty;
    public string Object { get; set; } = "conversation";
    public long? CreatedAt { get; set; }
    public Dictionary<string, object>? Metadata { get; set; }
}

// ========== Message Models ==========

/// <summary>A message in a conversation, normalised from V2 response output.</summary>
public class ThreadMessage
{
    public string Id { get; set; } = string.Empty;
    public string Object { get; set; } = "message";
    public string ThreadId { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    public List<MessageContent> Content { get; set; } = [];
    public long? CreatedAt { get; set; }
}

public class MessageContent
{
    public string Type { get; set; } = "text";
    public MessageText? Text { get; set; }
}

public class MessageText
{
    public string Value { get; set; } = string.Empty;
}

public class ThreadMessageListResponse
{
    public List<ThreadMessage> Data { get; set; } = [];
}

// ========== Run Models ==========

/// <summary>
/// Synthetic run object returned to the frontend.
/// In V2 the /responses call is synchronous so status is always "completed" or "failed".
/// </summary>
public class ThreadRun
{
    public string Id { get; set; } = string.Empty;
    public string Object { get; set; } = "run";
    public string ThreadId { get; set; } = string.Empty;
    public string AgentName { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public string? Model { get; set; }
    public string? Instructions { get; set; }
    public long? CreatedAt { get; set; }
    public long? CompletedAt { get; set; }
}
