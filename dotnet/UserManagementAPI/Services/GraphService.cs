using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Azure.Identity;
using UserManagementAPI.Exceptions;
using UserManagementAPI.Models;

namespace UserManagementAPI.Services;

public class GraphService : IGraphService
{
    private readonly HttpClient _httpClient;
    private readonly DefaultAzureCredential _credential;
    private readonly ILogger<GraphService> _logger;
    private readonly string _graphBaseUrl;
    private readonly string _graphScope;
    private static readonly JsonSerializerOptions _jsonOptions = new() { PropertyNameCaseInsensitive = true };

    public GraphService(HttpClient httpClient, IConfiguration configuration, ILogger<GraphService> logger)
    {
        _httpClient = httpClient;
        var tenantId = configuration["AzureAd:TenantId"]!;
        _graphBaseUrl = configuration["MicrosoftGraph:BaseUrl"] ?? "https://graph.microsoft.com/v1.0";
        _graphScope = configuration["MicrosoftGraph:Scope"] ?? "https://graph.microsoft.com/.default";
        _credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
        {
            TenantId = tenantId,
            ExcludeEnvironmentCredential = true,
            ExcludeManagedIdentityCredential = true,
            ExcludeSharedTokenCacheCredential = true,
            ExcludeWorkloadIdentityCredential = true
        });
        _logger = logger;
    }

    public async Task<EntraGroup> CreateGroupAsync(string displayName, string? description)
    {
        // Idempotent: check if group already exists
        var existing = await FindGroupByNameAsync(displayName);
        if (existing is not null)
        {
            _logger.LogInformation("Group '{DisplayName}' already exists with ID {GroupId}", displayName, existing.Id);
            return existing;
        }

        var url = $"{_graphBaseUrl}/groups";
        var body = new
        {
            displayName,
            mailEnabled = false,
            mailNickname = displayName,
            securityEnabled = true,
            description = description ?? $"Security group: {displayName}"
        };

        var json = JsonSerializer.Serialize(body);
        var request = new HttpRequestMessage(HttpMethod.Post, url)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Creating Entra security group '{DisplayName}'", displayName);
        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<EntraGroup>(content, _jsonOptions)
            ?? throw new ApiException(HttpStatusCode.InternalServerError, "Failed to deserialize created group.");
    }

    public async Task<EntraGroup> GetGroupAsync(string groupId)
    {
        var url = $"{_graphBaseUrl}/groups/{groupId}";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<EntraGroup>(content, _jsonOptions)
            ?? throw new NotFoundException($"Group '{groupId}' not found.");
    }

    public async Task<EntraGroup?> FindGroupByNameAsync(string displayName)
    {
        var encodedName = Uri.EscapeDataString(displayName);
        var url = $"{_graphBaseUrl}/groups?$filter=displayName eq '{encodedName}'";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<EntraGroupListResponse>(content, _jsonOptions);
        return result?.Value.FirstOrDefault();
    }

    public async Task<EntraUser> GetUserByEmailAsync(string email)
    {
        // Try direct UPN lookup first
        var url = $"{_graphBaseUrl}/users/{Uri.EscapeDataString(email)}";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);

        if (response.IsSuccessStatusCode)
        {
            var content = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<EntraUser>(content, _jsonOptions)
                ?? throw new NotFoundException($"User '{email}' not found.");
        }

        // Fallback: search by mail property (for guest/external users)
        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            _logger.LogInformation("UPN lookup failed for '{Email}', trying mail filter", email);
            var encodedEmail = Uri.EscapeDataString(email);
            var filterUrl = $"{_graphBaseUrl}/users?$filter=mail eq '{encodedEmail}'";
            request = new HttpRequestMessage(HttpMethod.Get, filterUrl);
            await SetAuthHeaderAsync(request);

            response = await _httpClient.SendAsync(request);
            await EnsureSuccessAsync(response);

            var filterContent = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<EntraUserListResponse>(filterContent, _jsonOptions);
            var user = result?.Value.FirstOrDefault();

            if (user is null)
                throw new NotFoundException($"User '{email}' not found by UPN or mail.");

            return user;
        }

        await EnsureSuccessAsync(response);
        throw new NotFoundException($"User '{email}' not found.");
    }

    public async Task AddGroupMemberAsync(string groupId, string userId)
    {
        var url = $"{_graphBaseUrl}/groups/{groupId}/members/$ref";
        var body = new Dictionary<string, string>
        {
            ["@odata.id"] = $"{_graphBaseUrl}/directoryObjects/{userId}"
        };

        var json = JsonSerializer.Serialize(body);
        var request = new HttpRequestMessage(HttpMethod.Post, url)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Adding user '{UserId}' to group '{GroupId}'", userId, groupId);
        var response = await _httpClient.SendAsync(request);

        // 400 with "already exist" means user is already a member — treat as success
        if (response.StatusCode == HttpStatusCode.BadRequest)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            if (errorBody.Contains("already exist", StringComparison.OrdinalIgnoreCase))
            {
                _logger.LogInformation("User '{UserId}' is already a member of group '{GroupId}'", userId, groupId);
                return;
            }
        }

        await EnsureSuccessAsync(response);
    }

    public async Task RemoveGroupMemberAsync(string groupId, string userId)
    {
        var url = $"{_graphBaseUrl}/groups/{groupId}/members/{userId}/$ref";
        var request = new HttpRequestMessage(HttpMethod.Delete, url);
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Removing user '{UserId}' from group '{GroupId}'", userId, groupId);
        var response = await _httpClient.SendAsync(request);

        // 404 means user is not a member — treat as success
        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            _logger.LogInformation("User '{UserId}' was not a member of group '{GroupId}'", userId, groupId);
            return;
        }

        await EnsureSuccessAsync(response);
    }

    public async Task<List<GroupMember>> ListGroupMembersAsync(string groupId)
    {
        var url = $"{_graphBaseUrl}/groups/{groupId}/members";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<GroupMemberListResponse>(content, _jsonOptions);
        return result?.Value ?? [];
    }

    private async Task SetAuthHeaderAsync(HttpRequestMessage request)
    {
        var token = await _credential.GetTokenAsync(
            new Azure.Core.TokenRequestContext([_graphScope]));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
    }

    private static async Task EnsureSuccessAsync(HttpResponseMessage response)
    {
        if (response.IsSuccessStatusCode || response.StatusCode == HttpStatusCode.NoContent) return;

        var body = await response.Content.ReadAsStringAsync();
        var statusCode = response.StatusCode;

        throw statusCode switch
        {
            HttpStatusCode.NotFound => new NotFoundException($"Resource not found. {body}"),
            HttpStatusCode.BadRequest => new BadRequestException($"Bad request. {body}"),
            HttpStatusCode.Conflict => new ConflictException($"Conflict. {body}"),
            HttpStatusCode.Forbidden => new ApiException(HttpStatusCode.Forbidden, $"Forbidden. Ensure the app has required Graph permissions (Group.ReadWrite.All, User.Read.All). {body}"),
            _ => new ApiException(statusCode, $"Graph API request failed ({(int)statusCode}). {body}")
        };
    }
}
