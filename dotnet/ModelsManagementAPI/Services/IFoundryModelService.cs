using ModelsManagementAPI.Models;

namespace ModelsManagementAPI.Services;

public interface IFoundryModelService
{
    Task<FoundryDeploymentListResponse> ListDeploymentsAsync();
    Task<FoundryDeployment> GetDeploymentAsync(string deploymentName);
    Task<FoundryDeployment> CreateDeploymentAsync(string deploymentName, string modelName, string modelVersion, string skuName, int skuCapacity);
    Task<FoundryDeployment> PatchDeploymentAsync(string deploymentName, PatchFoundryDeploymentDto patch);
    Task DeleteDeploymentAsync(string deploymentName);
}
