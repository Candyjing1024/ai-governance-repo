using ModelsManagementAPI.Models;

namespace ModelsManagementAPI.Services;

public interface IDeploymentRequestService
{
    Task<ModelDeploymentRequest> CreateRequestAsync(ModelDeploymentRequest request);
    Task<IEnumerable<ModelDeploymentRequest>> GetAllRequestsAsync();
    Task<ModelDeploymentRequest?> GetRequestByIdAsync(string id, string projectName);
    Task<ModelDeploymentRequest?> ApproveRequestAsync(string id, string projectName, string reviewedBy);
    Task<ModelDeploymentRequest?> RejectRequestAsync(string id, string projectName, string reviewedBy, string? reason);
}
