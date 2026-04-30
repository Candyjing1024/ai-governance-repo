using System.Text.Json.Serialization;

namespace AIGatewayManagementAPI.Models;

// --- APIM Service ---

public class ApimServiceInfo
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("location")]
    public string? Location { get; set; }

    [JsonPropertyName("sku")]
    public ApimSku? Sku { get; set; }

    [JsonPropertyName("identity")]
    public ApimIdentity? Identity { get; set; }

    [JsonPropertyName("properties")]
    public ApimServiceProperties? Properties { get; set; }
}

public class ApimSku
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("capacity")]
    public int Capacity { get; set; }
}

public class ApimIdentity
{
    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("principalId")]
    public string? PrincipalId { get; set; }

    [JsonPropertyName("tenantId")]
    public string? TenantId { get; set; }
}

public class ApimServiceProperties
{
    [JsonPropertyName("gatewayUrl")]
    public string? GatewayUrl { get; set; }

    [JsonPropertyName("provisioningState")]
    public string? ProvisioningState { get; set; }

    [JsonPropertyName("publisherEmail")]
    public string? PublisherEmail { get; set; }

    [JsonPropertyName("publisherName")]
    public string? PublisherName { get; set; }
}

// --- APIs ---

public class ApimApiListResponse
{
    [JsonPropertyName("value")]
    public List<ApimApi> Value { get; set; } = [];
}

public class ApimApi
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("properties")]
    public ApimApiProperties? Properties { get; set; }
}

public class ApimApiProperties
{
    [JsonPropertyName("displayName")]
    public string? DisplayName { get; set; }

    [JsonPropertyName("path")]
    public string? Path { get; set; }

    [JsonPropertyName("protocols")]
    public List<string>? Protocols { get; set; }

    [JsonPropertyName("serviceUrl")]
    public string? ServiceUrl { get; set; }

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("subscriptionRequired")]
    public bool? SubscriptionRequired { get; set; }
}

// --- Operations ---

public class ApimOperationListResponse
{
    [JsonPropertyName("value")]
    public List<ApimOperation> Value { get; set; } = [];
}

public class ApimOperation
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("properties")]
    public ApimOperationProperties? Properties { get; set; }
}

public class ApimOperationProperties
{
    [JsonPropertyName("displayName")]
    public string? DisplayName { get; set; }

    [JsonPropertyName("method")]
    public string? Method { get; set; }

    [JsonPropertyName("urlTemplate")]
    public string? UrlTemplate { get; set; }
}

// --- Policy ---

public class ApimPolicyResponse
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("properties")]
    public ApimPolicyProperties? Properties { get; set; }
}

public class ApimPolicyProperties
{
    [JsonPropertyName("format")]
    public string? Format { get; set; }

    [JsonPropertyName("value")]
    public string? Value { get; set; }
}

// --- Role Assignments ---

public class RoleAssignmentListResponse
{
    [JsonPropertyName("value")]
    public List<RoleAssignment> Value { get; set; } = [];
}

public class RoleAssignment
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("properties")]
    public RoleAssignmentProperties? Properties { get; set; }
}

public class RoleAssignmentProperties
{
    [JsonPropertyName("roleDefinitionId")]
    public string? RoleDefinitionId { get; set; }

    [JsonPropertyName("principalId")]
    public string? PrincipalId { get; set; }

    [JsonPropertyName("principalType")]
    public string? PrincipalType { get; set; }

    [JsonPropertyName("scope")]
    public string? Scope { get; set; }
}
