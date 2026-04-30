using ProjectManagementAPI.Models;

namespace ProjectManagementAPI.Services;

public interface IFoundryAccountService
{
    // Accounts
    Task<FoundryAccountListResponse> ListAccountsAsync();
    Task<FoundryAccount> GetAccountAsync();
    Task<FoundryAccount> CreateAccountAsync(string location, string sku, bool allowProjectManagement, string publicNetworkAccess);
    Task<FoundryAccount> PatchAccountAsync(PatchFoundryAccountDto patch);
    Task DeleteAccountAsync();

    // Projects
    Task<FoundryProjectListResponse> ListProjectsAsync();
    Task<FoundryProject> GetProjectAsync(string projectName);
    Task<FoundryProject> CreateProjectAsync(string projectName, string location, string? displayName, string? description);
    Task<FoundryProject> PatchProjectAsync(string projectName, PatchFoundryProjectDto patch);
    Task DeleteProjectAsync(string projectName);
}
