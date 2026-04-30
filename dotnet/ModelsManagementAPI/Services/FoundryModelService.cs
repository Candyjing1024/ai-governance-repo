using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Azure.Identity;
using ModelsManagementAPI.Exceptions;
using ModelsManagementAPI.Models;

namespace ModelsManagementAPI.Services;

public class FoundryModelService : IFoundryModelService
{
    private readonly HttpClient _httpClient;
    private readonly DefaultAzureCredential _credential;
    private readonly string _subscriptionId;
    private readonly string _resourceGroup;
    private readonly string _accountName;
    private readonly string _apiVersion;
    private readonly string _armBaseUrl;
    private readonly string _armScope;
    private readonly ILogger<FoundryModelService> _logger;
    private static readonly JsonSerializerOptions _jsonOptions = new() { PropertyNameCaseInsensitive = true };

    public FoundryModelService(HttpClient httpClient, IConfiguration configuration, ILogger<FoundryModelService> logger)
    {
        _httpClient = httpClient;
        var tenantId = configuration["AzureFoundry:TenantId"];
        _armBaseUrl = configuration["AzureUrls:ArmBaseUrl"] ?? "https://management.azure.com";
        _armScope = configuration["AzureUrls:ArmScope"] ?? "https://management.azure.com/.default";
        _credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
        {
            TenantId = tenantId,
            ExcludeEnvironmentCredential = true,
            ExcludeManagedIdentityCredential = true,
            ExcludeSharedTokenCacheCredential = true,
            ExcludeWorkloadIdentityCredential = true
        });
        _subscriptionId = configuration["AzureFoundry:SubscriptionId"]!;
        _resourceGroup = configuration["AzureFoundry:ResourceGroup"]!;
        _accountName = configuration["AzureFoundry:AccountName"]!;
        _apiVersion = configuration["AzureFoundry:ApiVersion"] ?? "2025-12-01";
        _logger = logger;
    }

    public async Task<FoundryDeploymentListResponse> ListDeploymentsAsync()
    {
        var url = BuildUrl();
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<FoundryDeploymentListResponse>(content, _jsonOptions)
            ?? new FoundryDeploymentListResponse();
    }

    public async Task<FoundryDeployment> GetDeploymentAsync(string deploymentName)
    {
        var url = BuildUrl(deploymentName);
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<FoundryDeployment>(content, _jsonOptions)
            ?? throw new NotFoundException($"Deployment '{deploymentName}' not found.");
    }

    public async Task<FoundryDeployment> CreateDeploymentAsync(
        string deploymentName, string modelName, string modelVersion, string skuName, int skuCapacity)
    {
        var url = BuildUrl(deploymentName);

        // Idempotency: check if deployment already exists
        var checkRequest = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(checkRequest);
        var checkResponse = await _httpClient.SendAsync(checkRequest);

        if (checkResponse.StatusCode == HttpStatusCode.OK)
        {
            var existing = JsonSerializer.Deserialize<FoundryDeployment>(await checkResponse.Content.ReadAsStringAsync(), _jsonOptions);
            var state = existing?.Properties?.ProvisioningState ?? "Unknown";
            _logger.LogInformation("Deployment '{DeploymentName}' already exists (state={State})", deploymentName, state);
            return existing!;
        }

        var model = string.IsNullOrWhiteSpace(modelVersion)
            ? new { format = "OpenAI", name = modelName }
            : (object)new { format = "OpenAI", name = modelName, version = modelVersion };

        var body = new
        {
            sku = new { name = skuName, capacity = skuCapacity },
            properties = new
            {
                model
            }
        };

        var json = JsonSerializer.Serialize(body);
        var request = new HttpRequestMessage(HttpMethod.Put, url)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Creating deployment '{DeploymentName}' on account '{AccountName}'", deploymentName, _accountName);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        // Poll until provisioning completes
        return await PollDeploymentAsync(url, deploymentName);
    }

    public async Task DeleteDeploymentAsync(string deploymentName)
    {
        // Check if deployment exists first (ARM DELETE returns 204 even for non-existent resources)
        await GetDeploymentAsync(deploymentName);

        var url = BuildUrl(deploymentName);
        var request = new HttpRequestMessage(HttpMethod.Delete, url);
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Deleting deployment '{DeploymentName}' from account '{AccountName}'", deploymentName, _accountName);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);
    }

    public async Task<FoundryDeployment> PatchDeploymentAsync(string deploymentName, PatchFoundryDeploymentDto patch)
    {
        // Get existing deployment to merge values
        var existing = await GetDeploymentAsync(deploymentName);

        var skuName = patch.SkuName ?? existing.Sku?.Name ?? "GlobalStandard";
        var skuCapacity = patch.SkuCapacity ?? existing.Sku?.Capacity ?? 10;

        var url = BuildUrl(deploymentName);
        var body = new
        {
            sku = new { name = skuName, capacity = skuCapacity },
            properties = new
            {
                model = new
                {
                    format = existing.Properties?.Model?.Format ?? "OpenAI",
                    name = existing.Properties?.Model?.Name,
                    version = existing.Properties?.Model?.Version
                }
            }
        };

        var json = JsonSerializer.Serialize(body);
        var request = new HttpRequestMessage(HttpMethod.Put, url)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Updating deployment '{DeploymentName}' on account '{AccountName}'", deploymentName, _accountName);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        return await PollDeploymentAsync(url, deploymentName);
    }

    private async Task<FoundryDeployment> PollDeploymentAsync(string url, string deploymentName, int maxAttempts = 60, int delaySeconds = 10)
    {
        for (var i = 0; i < maxAttempts; i++)
        {
            await Task.Delay(TimeSpan.FromSeconds(delaySeconds));

            var pollRequest = new HttpRequestMessage(HttpMethod.Get, url);
            await SetAuthHeaderAsync(pollRequest);
            var pollResponse = await _httpClient.SendAsync(pollRequest);

            if (!pollResponse.IsSuccessStatusCode) continue;

            var content = await pollResponse.Content.ReadAsStringAsync();
            var deployment = JsonSerializer.Deserialize<FoundryDeployment>(content, _jsonOptions);
            var state = deployment?.Properties?.ProvisioningState;

            _logger.LogInformation("Polling deployment '{DeploymentName}': state={State}", deploymentName, state);

            if (state is "Succeeded" or "Failed" or "Canceled")
            {
                if (state != "Succeeded")
                    throw new ApiException(HttpStatusCode.BadGateway, $"Deployment '{deploymentName}' ended with state '{state}'.");

                return deployment!;
            }
        }

        throw new ApiException(HttpStatusCode.GatewayTimeout, $"Deployment '{deploymentName}' did not complete within the polling window.");
    }

    private string BuildUrl(string? deploymentName = null)
    {
        var baseUrl = $"{_armBaseUrl}/subscriptions/{_subscriptionId}" +
                      $"/resourceGroups/{_resourceGroup}" +
                      $"/providers/Microsoft.CognitiveServices/accounts/{_accountName}/deployments";

        if (!string.IsNullOrEmpty(deploymentName))
            baseUrl += $"/{deploymentName}";

        return $"{baseUrl}?api-version={_apiVersion}";
    }

    private async Task SetAuthHeaderAsync(HttpRequestMessage request)
    {
        var token = await _credential.GetTokenAsync(
            new Azure.Core.TokenRequestContext([_armScope]));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
    }

    private static async Task EnsureSuccessAsync(HttpResponseMessage response)
    {
        if (response.IsSuccessStatusCode) return;

        var errorContent = await response.Content.ReadAsStringAsync();

        throw response.StatusCode switch
        {
            HttpStatusCode.NotFound => new NotFoundException($"Resource not found. {errorContent}"),
            HttpStatusCode.Unauthorized => new UnauthorizedException($"Unauthorized. {errorContent}"),
            HttpStatusCode.Forbidden => new ForbiddenException($"Forbidden. {errorContent}"),
            HttpStatusCode.Conflict => new ConflictException($"Conflict. {errorContent}"),
            HttpStatusCode.BadRequest => new BadRequestException($"Bad request. {errorContent}"),
            _ => new ApiException(response.StatusCode, $"ARM API error ({response.StatusCode}): {errorContent}")
        };
    }
}
