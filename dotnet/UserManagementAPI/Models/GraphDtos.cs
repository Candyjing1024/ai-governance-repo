using System.ComponentModel.DataAnnotations;

namespace UserManagementAPI.Models;

public class CreateGroupDto
{
    [Required(ErrorMessage = "Group display name is required.")]
    [StringLength(256)]
    public string DisplayName { get; set; } = string.Empty;

    [StringLength(500)]
    public string? Description { get; set; }
}

public class AddGroupMemberDto
{
    [Required(ErrorMessage = "User email is required.")]
    [EmailAddress(ErrorMessage = "A valid email address is required.")]
    public string UserEmail { get; set; } = string.Empty;
}
