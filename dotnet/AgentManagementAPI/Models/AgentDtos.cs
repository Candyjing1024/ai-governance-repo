using System.ComponentModel.DataAnnotations;

namespace AgentManagementAPI.Models;

// ========== Agent DTOs ==========

public class CreateAgentDto
{
    /// <summary>Agent display name (must be unique within the project).</summary>
    [Required, MaxLength(256)]
    public string Name { get; set; } = string.Empty;

    /// <summary>Model deployment name to use (e.g. gpt-4o-mini).</summary>
    [Required, MaxLength(256)]
    public string Model { get; set; } = string.Empty;

    /// <summary>System instructions for the agent.</summary>
    [MaxLength(32768)]
    public string? Instructions { get; set; }

    /// <summary>Agent kind: prompt, code_interpreter, file_search.</summary>
    [MaxLength(64)]
    public string Kind { get; set; } = "prompt";

    /// <summary>Optional description.</summary>
    [MaxLength(512)]
    public string? Description { get; set; }
}

public class UpdateAgentDto
{
    /// <summary>Updated agent name.</summary>
    [MaxLength(256)]
    public string? Name { get; set; }

    /// <summary>Updated model deployment name.</summary>
    [MaxLength(256)]
    public string? Model { get; set; }

    /// <summary>Updated system instructions.</summary>
    [MaxLength(32768)]
    public string? Instructions { get; set; }

    /// <summary>Optional description.</summary>
    [MaxLength(512)]
    public string? Description { get; set; }
}

// ========== Thread DTOs ==========

public class CreateThreadDto
{
    /// <summary>Optional metadata for the thread.</summary>
    public Dictionary<string, object>? Metadata { get; set; }
}

// ========== Message DTOs ==========

public class CreateMessageDto
{
    /// <summary>Message role (user or assistant).</summary>
    [Required]
    public string Role { get; set; } = "user";

    /// <summary>Message content text.</summary>
    [Required, MaxLength(32768)]
    public string Content { get; set; } = string.Empty;
}

// ========== Run DTOs ==========

public class CreateRunDto
{
    /// <summary>Agent name (or ID) to run on this conversation.</summary>
    [Required]
    public string AssistantId { get; set; } = string.Empty;

    /// <summary>Optional instruction override for this run.</summary>
    [MaxLength(32768)]
    public string? Instructions { get; set; }
}
