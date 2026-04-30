using System.Text.Json.Serialization;
using Newtonsoft.Json;

namespace ModelsManagementAPI.Models;

public class ModelDeploymentRequest
{
    [JsonPropertyName("id")]
    [JsonProperty("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString();

    [JsonPropertyName("modelName")]
    [JsonProperty("modelName")]
    public string ModelName { get; set; } = string.Empty;

    [JsonPropertyName("deploymentName")]
    [JsonProperty("deploymentName")]
    public string DeploymentName { get; set; } = string.Empty;

    [JsonPropertyName("projectName")]
    [JsonProperty("projectName")]
    public string ProjectName { get; set; } = string.Empty;

    [JsonPropertyName("region")]
    [JsonProperty("region")]
    public string Region { get; set; } = string.Empty;

    [JsonPropertyName("businessJustification")]
    [JsonProperty("businessJustification")]
    public string BusinessJustification { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    [JsonProperty("status")]
    public string Status { get; set; } = "requested_pending_approval";

    [JsonPropertyName("createdAt")]
    [JsonProperty("createdAt")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [JsonPropertyName("createdBy")]
    [JsonProperty("createdBy")]
    public string CreatedBy { get; set; } = string.Empty;

    [JsonPropertyName("reviewedBy")]
    [JsonProperty("reviewedBy")]
    public string? ReviewedBy { get; set; }

    [JsonPropertyName("reviewedAt")]
    [JsonProperty("reviewedAt")]
    public DateTime? ReviewedAt { get; set; }

    [JsonPropertyName("rejectionReason")]
    [JsonProperty("rejectionReason")]
    public string? RejectionReason { get; set; }

    [JsonPropertyName("deployedAt")]
    [JsonProperty("deployedAt")]
    public DateTime? DeployedAt { get; set; }

    [JsonPropertyName("skuName")]
    [JsonProperty("skuName")]
    public string SkuName { get; set; } = "GlobalStandard";

    [JsonPropertyName("skuCapacity")]
    [JsonProperty("skuCapacity")]
    public int SkuCapacity { get; set; } = 10;

    [JsonPropertyName("modelVersion")]
    [JsonProperty("modelVersion")]
    public string ModelVersion { get; set; } = string.Empty;

    [JsonPropertyName("requestGroup")]
    [JsonProperty("requestGroup")]
    public string RequestGroup { get; set; } = string.Empty;

    [JsonPropertyName("requestUser")]
    [JsonProperty("requestUser")]
    public string RequestUser { get; set; } = string.Empty;

    [JsonPropertyName("deploymentId")]
    [JsonProperty("deploymentId")]
    public string? DeploymentId { get; set; }

    [JsonPropertyName("groupId")]
    [JsonProperty("groupId")]
    public string? GroupId { get; set; }

    [JsonPropertyName("policyUpdated")]
    [JsonProperty("policyUpdated")]
    public bool PolicyUpdated { get; set; } = false;
}
