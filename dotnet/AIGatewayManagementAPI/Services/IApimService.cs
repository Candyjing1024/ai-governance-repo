using AIGatewayManagementAPI.Models;

namespace AIGatewayManagementAPI.Services;

public interface IApimService
{
    Task<ApimServiceInfo> GetApimInstanceAsync();
    Task<ApimApiListResponse> ListApisAsync();
    Task<ApimApi> GetApiAsync(string apiId);
    Task<ApimApi> CreateFoundryApiAsync(CreateFoundryApiDto dto);
    Task DeleteApiAsync(string apiId);
    Task<ApimOperationListResponse> ListOperationsAsync(string apiId);
    Task<ApimPolicyResponse> GetPolicyAsync(string apiId);
    Task<ApimPolicyResponse> SetPolicyAsync(string apiId, SetPolicyDto dto);
    Task<string> GetFoundryEndpointAsync();

    // T17 — Add group to APIM JWT policy
    Task<ApimPolicyResponse> AddGroupToPolicyAsync(string apiId, string groupId);

    // T19 — Remove group from APIM JWT policy
    Task<ApimPolicyResponse> RemoveGroupFromPolicyAsync(string apiId, string groupId);

    // Extract current group IDs from policy XML
    Task<List<string>> GetPolicyGroupIdsAsync(string apiId);

    // Model-level access restrictions per group
    Task<ApimPolicyResponse> AddModelRestrictionAsync(string apiId, string groupId, List<string> allowedModels);
    Task<ApimPolicyResponse> RemoveModelRestrictionAsync(string apiId, string groupId);
    Task<List<ModelRestrictionDto>> GetModelRestrictionsAsync(string apiId);
}
