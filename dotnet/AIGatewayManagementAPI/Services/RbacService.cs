using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Azure.Identity;
using AIGatewayManagementAPI.Exceptions;
using AIGatewayManagementAPI.Models;

namespace AIGatewayManagementAPI.Services;

public class RbacService : IRbacService
{
    private readonly HttpClient _httpClient;
    private readonly DefaultAzureCredential _credential;
    private readonly IApimService _apimService;
    private readonly string _subscriptionId;
    private readonly string _resourceGroup;
    private readonly string _accountName;
    private readonly string _tenantId;
    private readonly string _armBaseUrl;
    private readonly string _armScope;
    private readonly ILogger<RbacService> _logger;
    private static readonly JsonSerializerOptions _jsonOptions = new() { PropertyNameCaseInsensitive = true };

    private static readonly Dictionary<string, string> WellKnownRoles = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Cognitive Services OpenAI User"] = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd",
        ["Cognitive Services User"] = "a97b65f3-24c7-4388-baec-2e87135dc908",
        ["Azure AI Developer"] = "64702f94-c441-49e6-a78b-ef80e0188fee",
    };

    public RbacService(HttpClient httpClient, IConfiguration configuration, IApimService apimService, ILogger<RbacService> logger)
    {
        _httpClient = httpClient;
        _tenantId = configuration["AzureFoundry:TenantId"]!;
        _armBaseUrl = configuration["AzureUrls:ArmBaseUrl"] ?? "https://management.azure.com";
        _armScope = configuration["AzureUrls:ArmScope"] ?? "https://management.azure.com/.default";
        _credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
        {
            TenantId = _tenantId,
            ExcludeEnvironmentCredential = true,
            ExcludeManagedIdentityCredential = true,
            ExcludeSharedTokenCacheCredential = true,
            ExcludeWorkloadIdentityCredential = true
        });
        _subscriptionId = configuration["AzureFoundry:SubscriptionId"]!;
        _resourceGroup = configuration["AzureFoundry:ResourceGroup"]!;
        _accountName = configuration["AzureFoundry:AccountName"]!;
        _apimService = apimService;
        _logger = logger;
    }

    private string GetScope(string? projectName = null)
    {
        var scope = $"/subscriptions/{_subscriptionId}/resourceGroups/{_resourceGroup}" +
                    $"/providers/Microsoft.CognitiveServices/accounts/{_accountName}";
        if (!string.IsNullOrEmpty(projectName))
            scope += $"/projects/{projectName}";
        return scope;
    }

    public async Task<RoleAssignmentListResponse> ListRoleAssignmentsAsync(string? projectName = null)
    {
        var scope = GetScope(projectName);
        var url = $"{_armBaseUrl}{scope}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&$filter=atScope()";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<RoleAssignmentListResponse>(content, _jsonOptions)
            ?? new RoleAssignmentListResponse();
    }

    public async Task<RoleAssignment> AssignRoleAsync(AssignRoleDto dto)
    {
        if (!WellKnownRoles.TryGetValue(dto.RoleName, out var roleDefId))
            throw new BadRequestException(
                $"Unknown role '{dto.RoleName}'. Valid roles: {string.Join(", ", WellKnownRoles.Keys)}");

        var principalId = dto.PrincipalId;

        if (dto.UseApimIdentity)
        {
            var apim = await _apimService.GetApimInstanceAsync();
            principalId = apim.Identity?.PrincipalId
                ?? throw new BadRequestException("APIM instance does not have a managed identity.");
            _logger.LogInformation("Using APIM MI principal ID: {PrincipalId}", principalId);
        }

        if (string.IsNullOrEmpty(principalId))
            throw new BadRequestException("PrincipalId is required (or set useApimIdentity to true).");

        var scope = GetScope(dto.ProjectName);
        var assignmentId = Guid.NewGuid().ToString();
        var url = $"{_armBaseUrl}{scope}/providers/Microsoft.Authorization/roleAssignments/{assignmentId}?api-version=2022-04-01";

        var body = new
        {
            properties = new
            {
                roleDefinitionId = $"{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefId}",
                principalId,
                principalType = dto.PrincipalType
            }
        };

        var json = JsonSerializer.Serialize(body);
        var request = new HttpRequestMessage(HttpMethod.Put, url)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Assigning role '{RoleName}' to {PrincipalType} '{PrincipalId}' on scope '{Scope}'",
            dto.RoleName, dto.PrincipalType, principalId, scope);

        var response = await _httpClient.SendAsync(request);

        // 409 = already assigned
        if (response.StatusCode == HttpStatusCode.Conflict)
        {
            _logger.LogInformation("Role '{RoleName}' already assigned to '{PrincipalId}'", dto.RoleName, principalId);
            return new RoleAssignment
            {
                Name = assignmentId,
                Properties = new RoleAssignmentProperties
                {
                    PrincipalId = principalId,
                    PrincipalType = dto.PrincipalType,
                    RoleDefinitionId = roleDefId,
                    Scope = scope
                }
            };
        }

        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<RoleAssignment>(content, _jsonOptions)!;
    }

    public async Task DeleteRoleAssignmentAsync(string assignmentName, string? projectName = null)
    {
        var scope = GetScope(projectName);
        var url = $"{_armBaseUrl}{scope}/providers/Microsoft.Authorization/roleAssignments/{assignmentName}?api-version=2022-04-01";
        var request = new HttpRequestMessage(HttpMethod.Delete, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);

        if (response.StatusCode == HttpStatusCode.NoContent)
            return;

        await EnsureSuccessAsync(response);
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

        var body = await response.Content.ReadAsStringAsync();
        var statusCode = response.StatusCode;

        throw statusCode switch
        {
            HttpStatusCode.NotFound => new NotFoundException($"Resource not found. {body}"),
            HttpStatusCode.BadRequest => new BadRequestException($"Bad request. {body}"),
            HttpStatusCode.Conflict => new ConflictException($"Conflict. {body}"),
            _ => new ApiException(statusCode, $"ARM request failed ({(int)statusCode}). {body}")
        };
    }
}
