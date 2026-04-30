using Microsoft.Azure.Cosmos;
using ModelsManagementAPI.Models;
using Microsoft.Extensions.Logging;

namespace ModelsManagementAPI.Services;

public class CosmosDeploymentRequestService : IDeploymentRequestService
{
    private readonly Container _container;
    private readonly IFoundryModelService _foundryService;
    private readonly ILogger<CosmosDeploymentRequestService> _logger;

    public CosmosDeploymentRequestService(
        CosmosClient cosmosClient,
        IConfiguration configuration,
        IFoundryModelService foundryService,
        ILogger<CosmosDeploymentRequestService> logger)
    {
        var databaseName = configuration["CosmosDb:DatabaseName"]!;
        var containerName = configuration["CosmosDb:ContainerName"]!;
        _container = cosmosClient.GetContainer(databaseName, containerName);
        _foundryService = foundryService;
        _logger = logger;
    }

    public async Task<ModelDeploymentRequest> CreateRequestAsync(ModelDeploymentRequest request)
    {
        var response = await _container.CreateItemAsync(request, new PartitionKey(request.ProjectName));
        return response.Resource;
    }

    public async Task<IEnumerable<ModelDeploymentRequest>> GetAllRequestsAsync()
    {
        var query = _container.GetItemQueryIterator<ModelDeploymentRequest>(
            new QueryDefinition("SELECT * FROM c ORDER BY c.createdAt DESC"));

        var results = new List<ModelDeploymentRequest>();
        while (query.HasMoreResults)
        {
            var response = await query.ReadNextAsync();
            results.AddRange(response);
        }

        return results;
    }

    public async Task<ModelDeploymentRequest?> GetRequestByIdAsync(string id, string projectName)
    {
        try
        {
            var response = await _container.ReadItemAsync<ModelDeploymentRequest>(id, new PartitionKey(projectName));
            return response.Resource;
        }
        catch (CosmosException ex) when (ex.StatusCode == System.Net.HttpStatusCode.NotFound)
        {
            return null;
        }
    }

    public async Task<ModelDeploymentRequest?> ApproveRequestAsync(string id, string projectName, string reviewedBy)
    {
        var request = await GetRequestByIdAsync(id, projectName);
        if (request is null) return null;

        // Attempt deployment FIRST — only mark approved if it succeeds
        try
        {
            var deployment = await _foundryService.CreateDeploymentAsync(
                request.DeploymentName,
                request.ModelName,
                request.ModelVersion,
                request.SkuName,
                request.SkuCapacity);

            // Deployment succeeded — mark approved + deployed
            request.Status = "deployed";
            request.ReviewedBy = reviewedBy;
            request.ReviewedAt = DateTime.UtcNow;
            request.DeploymentId = deployment.Name;
            request.DeployedAt = DateTime.UtcNow;

            var response = await _container.ReplaceItemAsync(request, id, new PartitionKey(projectName));
            return response.Resource;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Deployment failed for request {Id}. Request stays pending.", id);
            throw;
        }
    }

    public async Task<ModelDeploymentRequest?> RejectRequestAsync(string id, string projectName, string reviewedBy, string? reason)
    {
        var request = await GetRequestByIdAsync(id, projectName);
        if (request is null) return null;

        request.Status = "rejected";
        request.ReviewedBy = reviewedBy;
        request.ReviewedAt = DateTime.UtcNow;
        request.RejectionReason = reason;

        var response = await _container.ReplaceItemAsync(request, id, new PartitionKey(projectName));
        return response.Resource;
    }
}
