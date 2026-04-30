using System.ComponentModel.DataAnnotations;

namespace AIGatewayManagementAPI.Models;

public class CreateFoundryApiDto
{
    [StringLength(200)]
    public string DisplayName { get; set; } = "Foundry API";

    [StringLength(100)]
    public string ApiId { get; set; } = "foundry-api";

    [StringLength(100)]
    public string Path { get; set; } = "foundry";
}

public class SetPolicyDto
{
    [Required(ErrorMessage = "Audience (Entra ID app client ID) is required.")]
    public string Audience { get; set; } = string.Empty;

    public List<string>? AllowedGroups { get; set; }

    public string? FoundryEndpoint { get; set; }

    public List<ModelRestrictionDto>? ModelRestrictions { get; set; }
}

public class ModelRestrictionDto
{
    [Required(ErrorMessage = "Group ID is required.")]
    public string GroupId { get; set; } = string.Empty;

    [Required(ErrorMessage = "At least one allowed model/deployment name is required.")]
    [MinLength(1, ErrorMessage = "At least one allowed model/deployment name is required.")]
    public List<string> AllowedModels { get; set; } = [];
}

public class AssignRoleDto
{
    public string? PrincipalId { get; set; }

    [Required(ErrorMessage = "Principal type is required (ServicePrincipal, Group, or User).")]
    public string PrincipalType { get; set; } = "ServicePrincipal";

    [Required(ErrorMessage = "Role name is required.")]
    public string RoleName { get; set; } = string.Empty;

    public string? ProjectName { get; set; }

    public bool UseApimIdentity { get; set; }
}
