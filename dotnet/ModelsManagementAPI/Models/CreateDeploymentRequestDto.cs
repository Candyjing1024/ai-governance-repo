using System.ComponentModel.DataAnnotations;

namespace ModelsManagementAPI.Models;

public class CreateDeploymentRequestDto
{
    [Required(ErrorMessage = "Model name is required.")]
    [StringLength(200)]
    public string ModelName { get; set; } = string.Empty;

    [Required(ErrorMessage = "Deployment name is required.")]
    [StringLength(200)]
    public string DeploymentName { get; set; } = string.Empty;

    [Required(ErrorMessage = "Project name is required.")]
    [StringLength(200)]
    public string ProjectName { get; set; } = string.Empty;

    [Required(ErrorMessage = "Region is required.")]
    [StringLength(100)]
    public string Region { get; set; } = string.Empty;

    [Required(ErrorMessage = "Business justification is required.")]
    [StringLength(2000)]
    public string BusinessJustification { get; set; } = string.Empty;

    [StringLength(50)]
    public string SkuName { get; set; } = "GlobalStandard";

    [Range(1, 1000)]
    public int SkuCapacity { get; set; } = 10;

    [StringLength(50)]
    public string ModelVersion { get; set; } = string.Empty;

    [Required(ErrorMessage = "Request group name is required.")]
    [StringLength(200)]
    public string RequestGroup { get; set; } = string.Empty;

    [Required(ErrorMessage = "Request user email is required.")]
    [StringLength(200)]
    [EmailAddress(ErrorMessage = "Request user must be a valid email address.")]
    public string RequestUser { get; set; } = string.Empty;
}
