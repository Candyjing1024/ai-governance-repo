using System.Text.Json.Serialization;

namespace ModelsManagementAPI.Models;

public class FoundryDeploymentListResponse
{
    [JsonPropertyName("value")]
    public List<FoundryDeployment> Value { get; set; } = [];
}

public class FoundryDeployment
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("sku")]
    public FoundryDeploymentSku? Sku { get; set; }

    [JsonPropertyName("properties")]
    public FoundryDeploymentProperties? Properties { get; set; }
}

public class FoundryDeploymentSku
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("capacity")]
    public int Capacity { get; set; }
}

public class FoundryDeploymentProperties
{
    [JsonPropertyName("model")]
    public FoundryDeploymentModel? Model { get; set; }

    [JsonPropertyName("provisioningState")]
    public string? ProvisioningState { get; set; }
}

public class FoundryDeploymentModel
{
    [JsonPropertyName("format")]
    public string? Format { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }
}
