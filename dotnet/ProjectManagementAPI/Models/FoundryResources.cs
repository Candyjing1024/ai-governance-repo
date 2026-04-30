using System.Text.Json.Serialization;

namespace ProjectManagementAPI.Models;

// --- Account (AIServices Resource) DTOs ---

public class FoundryAccountListResponse
{
    [JsonPropertyName("value")]
    public List<FoundryAccount> Value { get; set; } = [];
}

public class FoundryAccount
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("location")]
    public string? Location { get; set; }

    [JsonPropertyName("kind")]
    public string? Kind { get; set; }

    [JsonPropertyName("sku")]
    public FoundryAccountSku? Sku { get; set; }

    [JsonPropertyName("identity")]
    public FoundryIdentity? Identity { get; set; }

    [JsonPropertyName("properties")]
    public FoundryAccountProperties? Properties { get; set; }
}

public class FoundryAccountSku
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }
}

public class FoundryIdentity
{
    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("principalId")]
    public string? PrincipalId { get; set; }

    [JsonPropertyName("tenantId")]
    public string? TenantId { get; set; }
}

public class FoundryAccountProperties
{
    [JsonPropertyName("provisioningState")]
    public string? ProvisioningState { get; set; }

    [JsonPropertyName("endpoint")]
    public string? Endpoint { get; set; }

    [JsonPropertyName("customSubDomainName")]
    public string? CustomSubDomainName { get; set; }

    [JsonPropertyName("publicNetworkAccess")]
    public string? PublicNetworkAccess { get; set; }

    [JsonPropertyName("allowProjectManagement")]
    public bool? AllowProjectManagement { get; set; }
}

// --- Project DTOs ---

public class FoundryProjectListResponse
{
    [JsonPropertyName("value")]
    public List<FoundryProject> Value { get; set; } = [];
}

public class FoundryProject
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("location")]
    public string? Location { get; set; }

    [JsonPropertyName("identity")]
    public FoundryIdentity? Identity { get; set; }

    [JsonPropertyName("properties")]
    public FoundryProjectProperties? Properties { get; set; }
}

public class FoundryProjectProperties
{
    [JsonPropertyName("provisioningState")]
    public string? ProvisioningState { get; set; }

    [JsonPropertyName("displayName")]
    public string? DisplayName { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("endpoints")]
    public Dictionary<string, string>? Endpoints { get; set; }
}
