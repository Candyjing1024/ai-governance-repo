using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Azure.Identity;
using ProjectManagementAPI.Exceptions;
using ProjectManagementAPI.Models;

namespace ProjectManagementAPI.Services;

public class FoundryAccountService : IFoundryAccountService
{
    private readonly HttpClient _httpClient;
    private readonly DefaultAzureCredential _credential;
    private readonly string _subscriptionId;
    private readonly string _resourceGroup;
    private readonly string _accountName;
    private readonly string _apiVersion;
    private readonly string _armBaseUrl;
    private readonly string _armScope;
    private readonly ILogger<FoundryAccountService> _logger;
    private static readonly JsonSerializerOptions _jsonOptions = new() { PropertyNameCaseInsensitive = true };

    public FoundryAccountService(HttpClient httpClient, IConfiguration configuration, ILogger<FoundryAccountService> logger)
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

    // ========== Accounts ==========

    public async Task<FoundryAccountListResponse> ListAccountsAsync()
    {
        var url = $"{ArmBase()}?api-version={_apiVersion}";
        var response = await SendAsync(HttpMethod.Get, url);
        await EnsureSuccessAsync(response);
        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<FoundryAccountListResponse>(content, _jsonOptions) ?? new FoundryAccountListResponse();
    }

    public async Task<FoundryAccount> GetAccountAsync()
    {
        var url = AccountUrl();
        var response = await SendAsync(HttpMethod.Get, url);
        await EnsureSuccessAsync(response);
        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<FoundryAccount>(content, _jsonOptions)
            ?? throw new NotFoundException($"Account '{_accountName}' not found.");
    }

    public async Task<FoundryAccount> CreateAccountAsync(
        string location, string sku, bool allowProjectManagement, string publicNetworkAccess)
    {
        var url = AccountUrl();

        // Idempotency: check if already exists
        var checkResponse = await SendRawAsync(HttpMethod.Get, url);
        if (checkResponse.StatusCode == HttpStatusCode.OK)
        {
            var existing = JsonSerializer.Deserialize<FoundryAccount>(await checkResponse.Content.ReadAsStringAsync(), _jsonOptions);
            var state = existing?.Properties?.ProvisioningState ?? "Unknown";
            _logger.LogInformation("Account '{AccountName}' already exists (state={State})", _accountName, state);

            // Ensure allowProjectManagement is enabled if requested
            if (allowProjectManagement && existing?.Properties?.AllowProjectManagement != true)
            {
                _logger.LogInformation("Enabling allowProjectManagement on '{AccountName}'", _accountName);
                return await PatchAccountAsync(
                    new PatchFoundryAccountDto { AllowProjectManagement = true });
            }

            return existing!;
        }

        var body = new
        {
            location,
            kind = "AIServices",
            identity = new { type = "SystemAssigned" },
            sku = new { name = sku },
            properties = new
            {
                customSubDomainName = _accountName,
                publicNetworkAccess,
                allowProjectManagement
            }
        };

        _logger.LogInformation("Creating Foundry account '{AccountName}' in '{Location}'", _accountName, location);
        var response = await SendAsync(HttpMethod.Put, url, body);
        await EnsureSuccessAsync(response);

        return await PollAccountAsync(url, _accountName);
    }

    public async Task<FoundryAccount> PatchAccountAsync(PatchFoundryAccountDto patch)
    {
        var url = AccountUrl();

        var props = new Dictionary<string, object>();
        if (patch.AllowProjectManagement.HasValue) props["allowProjectManagement"] = patch.AllowProjectManagement.Value;
        if (patch.PublicNetworkAccess is not null) props["publicNetworkAccess"] = patch.PublicNetworkAccess;

        var body = new { properties = props };

        _logger.LogInformation("Patching account '{AccountName}'", _accountName);
        var response = await SendAsync(new HttpMethod("PATCH"), url, body);
        await EnsureSuccessAsync(response);

        return await PollAccountAsync(url, _accountName);
    }

    public async Task DeleteAccountAsync()
    {
        var url = AccountUrl();
        // Verify existence first — ARM DELETE is idempotent and won't 404
        var check = await SendRawAsync(HttpMethod.Get, url);
        if (check.StatusCode == System.Net.HttpStatusCode.NotFound)
            throw new NotFoundException($"Account '{_accountName}' not found.");

        _logger.LogInformation("Deleting account '{AccountName}'", _accountName);
        var response = await SendAsync(HttpMethod.Delete, url);
        await EnsureSuccessAsync(response);
    }

    // ========== Projects ==========

    public async Task<FoundryProjectListResponse> ListProjectsAsync()
    {
        var url = $"{AccountBase()}/projects?api-version={_apiVersion}";
        var response = await SendAsync(HttpMethod.Get, url);
        await EnsureSuccessAsync(response);
        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<FoundryProjectListResponse>(content, _jsonOptions) ?? new FoundryProjectListResponse();
    }

    public async Task<FoundryProject> GetProjectAsync(string projectName)
    {
        var url = ProjectUrl(projectName);
        var response = await SendAsync(HttpMethod.Get, url);
        await EnsureSuccessAsync(response);
        var content = await response.Content.ReadAsStringAsync();
        _logger.LogInformation("GetProject ARM response: {Content}", content[..Math.Min(content.Length, 500)]);
        return JsonSerializer.Deserialize<FoundryProject>(content, _jsonOptions)
            ?? throw new NotFoundException($"Project '{projectName}' not found.");
    }

    public async Task<FoundryProject> CreateProjectAsync(
        string projectName, string location, string? displayName, string? description)
    {
        var url = ProjectUrl(projectName);

        // Idempotency: check if already exists
        var checkResponse = await SendRawAsync(HttpMethod.Get, url);
        if (checkResponse.StatusCode == HttpStatusCode.OK)
        {
            var existing = JsonSerializer.Deserialize<FoundryProject>(await checkResponse.Content.ReadAsStringAsync(), _jsonOptions);
            var state = existing?.Properties?.ProvisioningState ?? "Unknown";
            _logger.LogInformation("Project '{ProjectName}' already exists (state={State})", projectName, state);
            return existing!;
        }

        var body = new
        {
            location,
            identity = new { type = "SystemAssigned" },
            properties = new
            {
                displayName = displayName ?? projectName,
                description = description ?? $"Foundry project: {projectName}"
            }
        };

        _logger.LogInformation("Creating project '{ProjectName}' under account '{AccountName}'", projectName, _accountName);
        var response = await SendAsync(HttpMethod.Put, url, body);
        await EnsureSuccessAsync(response);

        return await PollProjectAsync(url, projectName);
    }

    public async Task<FoundryProject> PatchProjectAsync(string projectName, PatchFoundryProjectDto patch)
    {
        var url = ProjectUrl(projectName);

        // Verify existence first
        var check = await SendRawAsync(HttpMethod.Get, url);
        if (check.StatusCode == System.Net.HttpStatusCode.NotFound)
            throw new NotFoundException($"Project '{projectName}' not found.");

        var props = new Dictionary<string, object>();
        if (patch.DisplayName is not null) props["displayName"] = patch.DisplayName;
        if (patch.Description is not null) props["description"] = patch.Description;

        var body = new { properties = props };

        _logger.LogInformation("Patching project '{ProjectName}' under account '{AccountName}'", projectName, _accountName);
        var response = await SendAsync(new HttpMethod("PATCH"), url, body);
        await EnsureSuccessAsync(response);

        return await PollProjectAsync(url, projectName);
    }

    public async Task DeleteProjectAsync(string projectName)
    {
        var url = ProjectUrl(projectName);
        // Verify existence first — ARM DELETE is idempotent and won't 404
        var check = await SendRawAsync(HttpMethod.Get, url);
        if (check.StatusCode == System.Net.HttpStatusCode.NotFound)
            throw new NotFoundException($"Project '{projectName}' not found.");

        _logger.LogInformation("Deleting project '{ProjectName}' from account '{AccountName}'", projectName, _accountName);
        var response = await SendAsync(HttpMethod.Delete, url);
        await EnsureSuccessAsync(response);
    }

    // ========== URL Builders ==========

    private string ArmBase() =>
        $"{_armBaseUrl}/subscriptions/{_subscriptionId}/resourceGroups/{_resourceGroup}/providers/Microsoft.CognitiveServices/accounts";

    private string AccountBase() =>
        $"{ArmBase()}/{_accountName}";

    private string AccountUrl() =>
        $"{AccountBase()}?api-version={_apiVersion}";

    private string ProjectUrl(string projectName) =>
        $"{AccountBase()}/projects/{projectName}?api-version={_apiVersion}";

    // ========== HTTP Helpers ==========

    private async Task<HttpResponseMessage> SendAsync(HttpMethod method, string url, object? body = null)
    {
        var request = new HttpRequestMessage(method, url);
        if (body is not null)
            request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");

        var token = await _credential.GetTokenAsync(
            new Azure.Core.TokenRequestContext([_armScope]));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);

        return await _httpClient.SendAsync(request);
    }

    private async Task<HttpResponseMessage> SendRawAsync(HttpMethod method, string url)
    {
        var request = new HttpRequestMessage(method, url);
        var token = await _credential.GetTokenAsync(
            new Azure.Core.TokenRequestContext([_armScope]));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
        return await _httpClient.SendAsync(request);
    }

    // ========== Polling ==========

    private async Task<FoundryAccount> PollAccountAsync(string url, string name, int maxAttempts = 60, int delaySeconds = 10)
    {
        for (var i = 0; i < maxAttempts; i++)
        {
            await Task.Delay(TimeSpan.FromSeconds(delaySeconds));

            var response = await SendRawAsync(HttpMethod.Get, url);
            if (!response.IsSuccessStatusCode) continue;

            var content = await response.Content.ReadAsStringAsync();
            var account = JsonSerializer.Deserialize<FoundryAccount>(content, _jsonOptions);
            var state = account?.Properties?.ProvisioningState;

            _logger.LogInformation("Polling account '{Name}': state={State}", name, state);

            if (state is "Succeeded" or "Failed" or "Canceled")
            {
                if (state != "Succeeded")
                    throw new ApiException(HttpStatusCode.BadGateway, $"Account '{name}' ended with state '{state}'.");
                return account!;
            }
        }

        throw new ApiException(HttpStatusCode.GatewayTimeout, $"Account '{name}' did not complete within the polling window.");
    }

    private async Task<FoundryProject> PollProjectAsync(string url, string name, int maxAttempts = 60, int delaySeconds = 10)
    {
        for (var i = 0; i < maxAttempts; i++)
        {
            await Task.Delay(TimeSpan.FromSeconds(delaySeconds));

            var response = await SendRawAsync(HttpMethod.Get, url);
            if (!response.IsSuccessStatusCode) continue;

            var content = await response.Content.ReadAsStringAsync();
            var project = JsonSerializer.Deserialize<FoundryProject>(content, _jsonOptions);
            var state = project?.Properties?.ProvisioningState;

            _logger.LogInformation("Polling project '{Name}': state={State}", name, state);

            if (state is "Succeeded" or "Failed" or "Canceled")
            {
                if (state != "Succeeded")
                    throw new ApiException(HttpStatusCode.BadGateway, $"Project '{name}' ended with state '{state}'.");
                return project!;
            }
        }

        throw new ApiException(HttpStatusCode.GatewayTimeout, $"Project '{name}' did not complete within the polling window.");
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
