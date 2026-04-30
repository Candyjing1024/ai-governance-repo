using System.ComponentModel.DataAnnotations;

namespace ModelsManagementAPI.Models;

public class CreateFoundryDeploymentDto
{
    [Required]
    public string ModelName { get; set; } = string.Empty;

    [Required]
    public string DeploymentName { get; set; } = string.Empty;

    public string ModelVersion { get; set; } = string.Empty;

    public string SkuName { get; set; } = "GlobalStandard";

    [Range(1, 1000)]
    public int SkuCapacity { get; set; } = 10;
}

public class PatchFoundryDeploymentDto
{
    public string? SkuName { get; set; }

    [Range(1, 1000)]
    public int? SkuCapacity { get; set; }
}
