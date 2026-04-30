using System.ComponentModel.DataAnnotations;

namespace ProjectManagementAPI.Models;

public class CreateFoundryAccountDto
{
    [Required]
    [StringLength(100)]
    public string Location { get; set; } = string.Empty;

    public string Sku { get; set; } = "S0";

    public bool AllowProjectManagement { get; set; } = true;

    public string PublicNetworkAccess { get; set; } = "Enabled";
}

public class PatchFoundryAccountDto
{
    public bool? AllowProjectManagement { get; set; }

    public string? PublicNetworkAccess { get; set; }
}

public class CreateFoundryProjectDto
{
    [Required]
    [StringLength(200)]
    public string ProjectName { get; set; } = string.Empty;

    [Required]
    [StringLength(100)]
    public string Location { get; set; } = string.Empty;

    [StringLength(500)]
    public string? DisplayName { get; set; }

    [StringLength(2000)]
    public string? Description { get; set; }
}

public class PatchFoundryProjectDto
{
    [StringLength(500)]
    public string? DisplayName { get; set; }

    [StringLength(2000)]
    public string? Description { get; set; }
}
