using System.ComponentModel.DataAnnotations;

namespace ModelsManagementAPI.Models;

public class ApproveDeploymentRequestDto
{
    [Required]
    public string ReviewedBy { get; set; } = string.Empty;
}

public class RejectDeploymentRequestDto
{
    [Required]
    public string ReviewedBy { get; set; } = string.Empty;

    [StringLength(2000)]
    public string? RejectionReason { get; set; }
}
