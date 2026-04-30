namespace UserManagementAPI.Models;

public class EntraGroup
{
    public string Id { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public string? Description { get; set; }
    public bool SecurityEnabled { get; set; }
    public bool MailEnabled { get; set; }
    public string? MailNickname { get; set; }
}

public class EntraGroupListResponse
{
    public List<EntraGroup> Value { get; set; } = [];
}

public class EntraUser
{
    public string Id { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public string? UserPrincipalName { get; set; }
    public string? Mail { get; set; }
}

public class EntraUserListResponse
{
    public List<EntraUser> Value { get; set; } = [];
}

public class GroupMember
{
    public string Id { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public string? UserPrincipalName { get; set; }
    public string? Mail { get; set; }
}

public class GroupMemberListResponse
{
    public List<GroupMember> Value { get; set; } = [];
}
