using System.Net;
using System.Net.Http.Headers;
using System.Security;
using System.Text;
using System.Text.Json;
using Azure.Identity;
using AIGatewayManagementAPI.Exceptions;
using AIGatewayManagementAPI.Models;

namespace AIGatewayManagementAPI.Services;

public class ApimService : IApimService
{
    private readonly HttpClient _httpClient;
    private readonly DefaultAzureCredential _credential;
    private readonly string _subscriptionId;
    private readonly string _apimResourceGroup;
    private readonly string _apimServiceName;
    private readonly string _apimApiVersion;
    private readonly string _foundryResourceGroup;
    private readonly string _foundryAccountName;
    private readonly string _foundryApiVersion;
    private readonly string _tenantId;
    private readonly string _armBaseUrl;
    private readonly string _armScope;
    private readonly string _loginBaseUrl;
    private readonly ILogger<ApimService> _logger;
    private static readonly JsonSerializerOptions _jsonOptions = new() { PropertyNameCaseInsensitive = true };

    public ApimService(HttpClient httpClient, IConfiguration configuration, ILogger<ApimService> logger)
    {
        _httpClient = httpClient;
        _tenantId = configuration["AzureFoundry:TenantId"]!;
        _armBaseUrl = configuration["AzureUrls:ArmBaseUrl"] ?? "https://management.azure.com";
        _armScope = configuration["AzureUrls:ArmScope"] ?? "https://management.azure.com/.default";
        _loginBaseUrl = configuration["AzureUrls:LoginBaseUrl"] ?? "https://login.microsoftonline.com";
        _credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
        {
            TenantId = _tenantId,
            ExcludeEnvironmentCredential = true,
            ExcludeManagedIdentityCredential = true,
            ExcludeSharedTokenCacheCredential = true,
            ExcludeWorkloadIdentityCredential = true
        });
        _subscriptionId = configuration["AzureFoundry:SubscriptionId"]!;
        _apimResourceGroup = configuration["AzureApim:ResourceGroup"]!;
        _apimServiceName = configuration["AzureApim:ServiceName"]!;
        _apimApiVersion = configuration["AzureApim:ApiVersion"] ?? "2024-06-01-preview";
        _foundryResourceGroup = configuration["AzureFoundry:ResourceGroup"]!;
        _foundryAccountName = configuration["AzureFoundry:AccountName"]!;
        _foundryApiVersion = configuration["AzureFoundry:ApiVersion"] ?? "2025-12-01";
        _foundryProjectEndpoint = configuration["AzureFoundry:ProjectEndpoint"]!;
        _logger = logger;
    }

    private readonly string _foundryProjectEndpoint;

    private string ApimBaseUrl =>
        $"{_armBaseUrl}/subscriptions/{_subscriptionId}/resourceGroups/{_apimResourceGroup}" +
        $"/providers/Microsoft.ApiManagement/service/{_apimServiceName}";

    private string FoundryAccountUrl =>
        $"{_armBaseUrl}/subscriptions/{_subscriptionId}/resourceGroups/{_foundryResourceGroup}" +
        $"/providers/Microsoft.CognitiveServices/accounts/{_foundryAccountName}";

    public async Task<ApimServiceInfo> GetApimInstanceAsync()
    {
        var url = $"{ApimBaseUrl}?api-version={_apimApiVersion}";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ApimServiceInfo>(content, _jsonOptions)
            ?? throw new NotFoundException("APIM instance not found.");
    }

    public async Task<ApimApiListResponse> ListApisAsync()
    {
        var url = $"{ApimBaseUrl}/apis?api-version={_apimApiVersion}";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ApimApiListResponse>(content, _jsonOptions)
            ?? new ApimApiListResponse();
    }

    public async Task<ApimApi> GetApiAsync(string apiId)
    {
        var url = $"{ApimBaseUrl}/apis/{apiId}?api-version={_apimApiVersion}";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ApimApi>(content, _jsonOptions)
            ?? throw new NotFoundException($"API '{apiId}' not found.");
    }

    public async Task<ApimApi> CreateFoundryApiAsync(CreateFoundryApiDto dto)
    {
        var foundryEndpoint = _foundryProjectEndpoint;
        var apiUrl = $"{ApimBaseUrl}/apis/{dto.ApiId}?api-version={_apimApiVersion}";

        // Try azure-ai-foundry type first
        var body = new
        {
            properties = new
            {
                displayName = $"{dto.DisplayName} - {_foundryAccountName}",
                description = "Microsoft Foundry API — models, agents, chat",
                path = dto.Path,
                protocols = new[] { "https" },
                type = "azure-ai-foundry",
                serviceUrl = foundryEndpoint,
                subscriptionRequired = false,
                azureAIFoundryProperties = new
                {
                    resourceId = $"/subscriptions/{_subscriptionId}/resourceGroups/{_foundryResourceGroup}" +
                                 $"/providers/Microsoft.CognitiveServices/accounts/{_foundryAccountName}"
                }
            }
        };

        var json = JsonSerializer.Serialize(body);
        var request = new HttpRequestMessage(HttpMethod.Put, apiUrl)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Creating Foundry API '{ApiId}' with type azure-ai-foundry", dto.ApiId);
        var response = await _httpClient.SendAsync(request);

        if (response.IsSuccessStatusCode)
        {
            _logger.LogInformation("Foundry API created with azure-ai-foundry type (operations auto-generated)");
            // Also add V2 operations that may not be auto-generated
            await AddDefaultOperationsAsync(dto.ApiId);
            var content = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<ApimApi>(content, _jsonOptions)!;
        }

        // Fallback to standard HTTP API
        _logger.LogWarning("azure-ai-foundry type returned {StatusCode}, falling back to HTTP API", (int)response.StatusCode);

        var fallbackBody = new
        {
            properties = new
            {
                displayName = $"{dto.DisplayName} - {_foundryAccountName}",
                description = "Microsoft Foundry API — models, agents, chat",
                path = dto.Path,
                protocols = new[] { "https" },
                serviceUrl = foundryEndpoint,
                subscriptionRequired = false
            }
        };

        json = JsonSerializer.Serialize(fallbackBody);
        request = new HttpRequestMessage(HttpMethod.Put, apiUrl)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        _logger.LogInformation("API created with HTTP fallback, adding operations manually");
        await AddDefaultOperationsAsync(dto.ApiId);

        var apiContent = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ApimApi>(apiContent, _jsonOptions)!;
    }

    private async Task AddDefaultOperationsAsync(string apiId)
    {
        var operations = new[]
        {
            new { Id = "chat-completions", Name = "Chat Completions", Method = "POST",
                  Template = "/openai/deployments/{deployment-id}/chat/completions", HasDeployParam = true, HasThreadParam = false, HasRunParam = false, IsV1Path = false },
            new { Id = "completions", Name = "Completions", Method = "POST",
                  Template = "/openai/deployments/{deployment-id}/completions", HasDeployParam = true, HasThreadParam = false, HasRunParam = false, IsV1Path = false },
            new { Id = "embeddings", Name = "Embeddings", Method = "POST",
                  Template = "/openai/deployments/{deployment-id}/embeddings", HasDeployParam = true, HasThreadParam = false, HasRunParam = false, IsV1Path = false },
            new { Id = "image-generations", Name = "Image Generations", Method = "POST",
                  Template = "/openai/deployments/{deployment-id}/images/generations", HasDeployParam = true, HasThreadParam = false, HasRunParam = false, IsV1Path = false },
            new { Id = "responses", Name = "Responses", Method = "POST",
                  Template = "/openai/v1/responses", HasDeployParam = false, HasThreadParam = false, HasRunParam = false, IsV1Path = true },
            new { Id = "list-models", Name = "List Models", Method = "GET",
                  Template = "/openai/models", HasDeployParam = false, HasThreadParam = false, HasRunParam = false, IsV1Path = false },
            new { Id = "list-deployments", Name = "List Deployments", Method = "GET",
                  Template = "/openai/deployments", HasDeployParam = false, HasThreadParam = false, HasRunParam = false, IsV1Path = false },
            // Agent V2 operations (conversations + synchronous responses)
            new { Id = "conversation-create", Name = "Create Conversation", Method = "POST",
                  Template = "/openai/v1/conversations", HasDeployParam = false, HasThreadParam = false, HasRunParam = false, IsV1Path = true },
        };

        foreach (var op in operations)
        {
            var opUrl = $"{ApimBaseUrl}/apis/{apiId}/operations/{op.Id}?api-version={_apimApiVersion}";
            object opBody;

            // Build template parameters list based on URL params
            var templateParams = new List<object>();
            if (op.HasDeployParam)
                templateParams.Add(new { name = "deployment-id", description = "Deployment name", type = "string", required = true });
            if (op.HasThreadParam)
                templateParams.Add(new { name = "thread-id", description = "Thread ID", type = "string", required = true });
            if (op.HasRunParam)
                templateParams.Add(new { name = "run-id", description = "Run ID", type = "string", required = true });

            if (templateParams.Count > 0)
            {
                if (op.IsV1Path)
                {
                    opBody = new
                    {
                        properties = new
                        {
                            displayName = op.Name,
                            method = op.Method,
                            urlTemplate = op.Template,
                            templateParameters = templateParams
                        }
                    };
                }
                else
                {
                    opBody = new
                    {
                        properties = new
                        {
                            displayName = op.Name,
                            method = op.Method,
                            urlTemplate = op.Template,
                            templateParameters = templateParams,
                            request = new
                            {
                                queryParameters = new[]
                                {
                                    new { name = "api-version", description = "API version", type = "string", required = true }
                                }
                            }
                        }
                    };
                }
            }
            else if (op.IsV1Path)
            {
                opBody = new
                {
                    properties = new
                    {
                        displayName = op.Name,
                        method = op.Method,
                        urlTemplate = op.Template
                    }
                };
            }
            else
            {
                opBody = new
                {
                    properties = new
                    {
                        displayName = op.Name,
                        method = op.Method,
                        urlTemplate = op.Template,
                        request = new
                        {
                            queryParameters = new[]
                            {
                                new { name = "api-version", description = "API version", type = "string", required = true }
                            }
                        }
                    }
                };
            }

            var json = JsonSerializer.Serialize(opBody);
            var request = new HttpRequestMessage(HttpMethod.Put, opUrl)
            {
                Content = new StringContent(json, Encoding.UTF8, "application/json")
            };
            await SetAuthHeaderAsync(request);

            var response = await _httpClient.SendAsync(request);
            var status = response.IsSuccessStatusCode ? "OK" : $"ERR {(int)response.StatusCode}";
            _logger.LogInformation("Operation '{OpName}': {Status}", op.Name, status);
        }
    }

    public async Task DeleteApiAsync(string apiId)
    {
        await GetApiAsync(apiId); // Existence check

        var url = $"{ApimBaseUrl}/apis/{apiId}?api-version={_apimApiVersion}";
        var request = new HttpRequestMessage(HttpMethod.Delete, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);
    }

    public async Task<ApimOperationListResponse> ListOperationsAsync(string apiId)
    {
        var url = $"{ApimBaseUrl}/apis/{apiId}/operations?api-version={_apimApiVersion}";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ApimOperationListResponse>(content, _jsonOptions)
            ?? new ApimOperationListResponse();
    }

    public async Task<ApimPolicyResponse> GetPolicyAsync(string apiId)
    {
        var url = $"{ApimBaseUrl}/apis/{apiId}/policies/policy?api-version={_apimApiVersion}";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ApimPolicyResponse>(content, _jsonOptions)
            ?? new ApimPolicyResponse();
    }

    public async Task<ApimPolicyResponse> SetPolicyAsync(string apiId, SetPolicyDto dto)
    {
        var foundryEndpoint = dto.FoundryEndpoint ?? _foundryProjectEndpoint;
        var policyXml = BuildPolicyXml(dto.Audience, dto.AllowedGroups, foundryEndpoint, dto.ModelRestrictions);

        var url = $"{ApimBaseUrl}/apis/{apiId}/policies/policy?api-version={_apimApiVersion}";
        var body = new { properties = new { format = "xml", value = policyXml } };
        var json = JsonSerializer.Serialize(body);

        var request = new HttpRequestMessage(HttpMethod.Put, url)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Setting policy on API '{ApiId}'", apiId);
        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ApimPolicyResponse>(content, _jsonOptions)!;
    }

    public async Task<string> GetFoundryEndpointAsync()
    {
        var url = $"{FoundryAccountUrl}?api-version={_foundryApiVersion}";
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        await SetAuthHeaderAsync(request);

        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(content);
        return doc.RootElement
            .GetProperty("properties")
            .GetProperty("endpoint")
            .GetString()
            ?? throw new NotFoundException("Foundry endpoint not found on account.");
    }

    public async Task<ApimPolicyResponse> AddGroupToPolicyAsync(string apiId, string groupId)
    {
        // T17: Read-modify-write — add group ID to <claim name="groups"> in policy XML
        var policy = await GetPolicyAsync(apiId);
        var xml = policy.Properties?.Value
            ?? throw new NotFoundException($"No policy found on API '{apiId}'.");

        // Check if group is already present
        if (xml.Contains($"<value>{System.Security.SecurityElement.Escape(groupId)}</value>"))
        {
            _logger.LogInformation("Group '{GroupId}' already exists in policy for API '{ApiId}'", groupId, apiId);
            return policy;
        }

        // Insert the new group value before </claim> inside the groups claim section
        var escapedGroupId = System.Security.SecurityElement.Escape(groupId);
        var updatedXml = System.Text.RegularExpressions.Regex.Replace(
            xml,
            @"(<claim\s+name=""groups""[^>]*>)(.*?)(</claim>)",
            m => m.Groups[1].Value + m.Groups[2].Value.TrimEnd() +
                 $"\n                    <value>{escapedGroupId}</value>\n                " +
                 m.Groups[3].Value,
            System.Text.RegularExpressions.RegexOptions.Singleline
        );

        if (updatedXml == xml)
            throw new BadRequestException("Could not find <claim name=\"groups\"> section in the policy. Ensure the policy was set with allowed groups first.");

        return await PutPolicyXmlAsync(apiId, updatedXml);
    }

    public async Task<ApimPolicyResponse> RemoveGroupFromPolicyAsync(string apiId, string groupId)
    {
        // T19: Read-modify-write — remove group ID from <claim name="groups"> in policy XML
        var policy = await GetPolicyAsync(apiId);
        var xml = policy.Properties?.Value
            ?? throw new NotFoundException($"No policy found on API '{apiId}'.");

        var escapedGroupId = System.Text.RegularExpressions.Regex.Escape(
            System.Security.SecurityElement.Escape(groupId));

        var updatedXml = System.Text.RegularExpressions.Regex.Replace(
            xml,
            @"\s*<value>" + escapedGroupId + @"</value>",
            string.Empty
        );

        if (updatedXml == xml)
        {
            _logger.LogInformation("Group '{GroupId}' was not found in policy for API '{ApiId}'", groupId, apiId);
            return policy;
        }

        return await PutPolicyXmlAsync(apiId, updatedXml);
    }

    public async Task<List<string>> GetPolicyGroupIdsAsync(string apiId)
    {
        var policy = await GetPolicyAsync(apiId);
        var xml = policy.Properties?.Value ?? string.Empty;

        var groupIds = new List<string>();
        var match = System.Text.RegularExpressions.Regex.Match(
            xml,
            @"<claim\s+name=""groups""[^>]*>(.*?)</claim>",
            System.Text.RegularExpressions.RegexOptions.Singleline
        );

        if (match.Success)
        {
            var values = System.Text.RegularExpressions.Regex.Matches(match.Groups[1].Value, @"<value>(.*?)</value>");
            foreach (System.Text.RegularExpressions.Match v in values)
                groupIds.Add(v.Groups[1].Value);
        }

        return groupIds;
    }

    private async Task<ApimPolicyResponse> PutPolicyXmlAsync(string apiId, string policyXml)
    {
        var url = $"{ApimBaseUrl}/apis/{apiId}/policies/policy?api-version={_apimApiVersion}";
        var body = new { properties = new { format = "xml", value = policyXml } };
        var json = JsonSerializer.Serialize(body);

        var request = new HttpRequestMessage(HttpMethod.Put, url)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        await SetAuthHeaderAsync(request);

        _logger.LogInformation("Updating policy on API '{ApiId}'", apiId);
        var response = await _httpClient.SendAsync(request);
        await EnsureSuccessAsync(response);

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ApimPolicyResponse>(content, _jsonOptions)!;
    }

    private string BuildPolicyXml(string audience, List<string>? allowedGroups, string foundryEndpoint,
        List<AIGatewayManagementAPI.Models.ModelRestrictionDto>? modelRestrictions = null)
    {
        var openidUrl = $"{_loginBaseUrl}/{_tenantId}/v2.0/.well-known/openid-configuration";
        var escapedAudience = SecurityElement.Escape(audience);
        var escapedEndpoint = SecurityElement.Escape(foundryEndpoint);

        var groupSection = "";
        if (allowedGroups?.Count > 0)
        {
            var groupValues = string.Join("\n",
                allowedGroups.Select(g => $"                    <value>{SecurityElement.Escape(g)}</value>"));

            groupSection = $@"
        <!-- Group membership check -->
        <validate-jwt header-name=""Authorization"" failed-validation-httpcode=""403""
                      failed-validation-error-message=""Forbidden. User is not in an authorized group."">
            <openid-config url=""{openidUrl}"" />
            <audiences>
                <audience>{escapedAudience}</audience>
                <audience>api://{escapedAudience}</audience>
            </audiences>
            <issuers>
                <issuer>https://sts.windows.net/{_tenantId}/</issuer>
                <issuer>{_loginBaseUrl}/{_tenantId}/v2.0</issuer>
            </issuers>
            <required-claims>
                <claim name=""groups"" match=""any"">
{groupValues}
                </claim>
            </required-claims>
        </validate-jwt>";
        }

        var modelRestrictionSection = BuildModelRestrictionXml(modelRestrictions);

        return $@"<policies>
    <inbound>
        <base />
        <!-- Validate JWT (Entra ID) — accepts both v1 and v2 tokens -->
        <validate-jwt header-name=""Authorization"" failed-validation-httpcode=""401""
                      failed-validation-error-message=""Unauthorized""
                      require-expiration-time=""true"" require-scheme=""Bearer""
                      require-signed-tokens=""true"" output-token-variable-name=""jwt-token"">
            <openid-config url=""{openidUrl}"" />
            <audiences>
                <audience>{escapedAudience}</audience>
                <audience>api://{escapedAudience}</audience>
            </audiences>
            <issuers>
                <issuer>https://sts.windows.net/{_tenantId}/</issuer>
                <issuer>{_loginBaseUrl}/{_tenantId}/v2.0</issuer>
            </issuers>
        </validate-jwt>{groupSection}{modelRestrictionSection}
        <!-- Swap user token for Managed Identity token -->
        <authentication-managed-identity resource=""https://ai.azure.com"" output-token-variable-name=""managed-id-token"" />
        <set-header name=""Authorization"" exists-action=""override"">
            <value>@(""Bearer "" + (string)context.Variables[""managed-id-token""])</value>
        </set-header>
        <set-header name=""Ocp-Apim-Subscription-Key"" exists-action=""delete"" />
        <!-- Route to Foundry endpoint -->
        <set-backend-service base-url=""{escapedEndpoint}"" />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>";
    }

    private static string BuildModelRestrictionXml(List<AIGatewayManagementAPI.Models.ModelRestrictionDto>? restrictions)
    {
        if (restrictions is null || restrictions.Count == 0) return "";

        var sb = new StringBuilder();
        sb.AppendLine();
        sb.AppendLine("        <!-- Model-level access control per group -->");
        sb.AppendLine("        <choose>");

        foreach (var r in restrictions)
        {
            var escapedGroup = SecurityElement.Escape(r.GroupId);
            // Use simple alternation of model names — deployment names are alphanumeric+hyphens only.
            // Avoid Regex.Escape since its backslashes conflict with APIM's C# expression parsing.
            var modelsPattern = string.Join("|", r.AllowedModels);

            // Block if user IS in this group but the URL does NOT match an allowed deployment
            sb.AppendLine($@"            <when condition=""@(((Jwt)context.Variables[&quot;jwt-token&quot;]).Claims.ContainsKey(&quot;groups&quot;) &amp;&amp; ((Jwt)context.Variables[&quot;jwt-token&quot;]).Claims[&quot;groups&quot;].Contains(&quot;{escapedGroup}&quot;) &amp;&amp; !System.Text.RegularExpressions.Regex.IsMatch(context.Request.Url.Path, &quot;/deployments/({modelsPattern})/&quot;))"">");
            sb.AppendLine("                <return-response>");
            sb.AppendLine($@"                    <set-status code=""403"" reason=""Model not authorized for your group ({escapedGroup})"" />");
            sb.AppendLine(@"                    <set-body>{ ""error"": ""Your group does not have access to this model deployment."" }</set-body>");
            sb.AppendLine("                </return-response>");
            sb.AppendLine("            </when>");
        }

        sb.Append("        </choose>");
        return sb.ToString();
    }

    // ========== Model-level restrictions (read-modify-write on policy XML) ==========

    private static readonly System.Text.RegularExpressions.Regex _modelChooseBlockRegex = new(
        @"\s*<!-- Model-level access control per group -->\s*<choose>.*?</choose>",
        System.Text.RegularExpressions.RegexOptions.Singleline);

    private static readonly System.Text.RegularExpressions.Regex _modelWhenRegex = new(
        @"<when condition=""@\(\(\(Jwt\)context\.Variables\[&quot;jwt-token&quot;\]\)\.Claims\.ContainsKey\(&quot;groups&quot;\) &amp;&amp; \(\(Jwt\)context\.Variables\[&quot;jwt-token&quot;\]\)\.Claims\[&quot;groups&quot;\]\.Contains\(&quot;(?<groupId>[^&]*?)&quot;\) &amp;&amp; !System\.Text\.RegularExpressions\.Regex\.IsMatch\(context\.Request\.Url\.Path, &quot;/deployments/\((?<models>[^)]*?)\)/&quot;\)\)"">",
        System.Text.RegularExpressions.RegexOptions.Singleline);

    public async Task<ApimPolicyResponse> AddModelRestrictionAsync(string apiId, string groupId, List<string> allowedModels)
    {
        var policy = await GetPolicyAsync(apiId);
        var xml = policy.Properties?.Value
            ?? throw new NotFoundException($"No policy found on API '{apiId}'.");

        // Parse existing restrictions
        var existing = ParseModelRestrictions(xml);

        // Replace or add the restriction for this group
        existing.RemoveAll(r => r.GroupId == groupId);
        existing.Add(new AIGatewayManagementAPI.Models.ModelRestrictionDto { GroupId = groupId, AllowedModels = allowedModels });

        // Remove existing model-level block from XML
        var cleanXml = _modelChooseBlockRegex.Replace(xml, "");

        // Ensure validate-jwt stores token in variable (needed for model restriction checks)
        if (!cleanXml.Contains("output-token-variable-name"))
        {
            cleanXml = cleanXml.Replace(
                "require-signed-tokens=\"true\">",
                "require-signed-tokens=\"true\" output-token-variable-name=\"jwt-token\">");
        }

        // Build new block and insert before <!-- Swap user token
        var newBlock = BuildModelRestrictionXml(existing);
        var updatedXml = cleanXml.Replace(
            "<!-- Swap user token for Managed Identity token -->",
            newBlock.TrimEnd() + "\n        <!-- Swap user token for Managed Identity token -->");

        _logger.LogInformation("Setting model restriction for group '{GroupId}' on API '{ApiId}': {Models}",
            groupId, apiId, string.Join(", ", allowedModels));

        return await PutPolicyXmlAsync(apiId, updatedXml);
    }

    public async Task<ApimPolicyResponse> RemoveModelRestrictionAsync(string apiId, string groupId)
    {
        var policy = await GetPolicyAsync(apiId);
        var xml = policy.Properties?.Value
            ?? throw new NotFoundException($"No policy found on API '{apiId}'.");

        var existing = ParseModelRestrictions(xml);
        var before = existing.Count;
        existing.RemoveAll(r => r.GroupId == groupId);

        if (existing.Count == before)
        {
            _logger.LogInformation("No model restriction found for group '{GroupId}' on API '{ApiId}'", groupId, apiId);
            return policy;
        }

        // Remove existing block
        var cleanXml = _modelChooseBlockRegex.Replace(xml, "");

        if (existing.Count > 0)
        {
            var newBlock = BuildModelRestrictionXml(existing);
            cleanXml = cleanXml.Replace(
                "<!-- Swap user token for Managed Identity token -->",
                newBlock.TrimEnd() + "\n        <!-- Swap user token for Managed Identity token -->");
        }

        _logger.LogInformation("Removed model restriction for group '{GroupId}' on API '{ApiId}'", groupId, apiId);
        return await PutPolicyXmlAsync(apiId, cleanXml);
    }

    public Task<List<AIGatewayManagementAPI.Models.ModelRestrictionDto>> GetModelRestrictionsAsync(string apiId)
    {
        return GetModelRestrictionsFromPolicyAsync(apiId);
    }

    private async Task<List<AIGatewayManagementAPI.Models.ModelRestrictionDto>> GetModelRestrictionsFromPolicyAsync(string apiId)
    {
        var policy = await GetPolicyAsync(apiId);
        var xml = policy.Properties?.Value ?? string.Empty;
        return ParseModelRestrictions(xml);
    }

    private static List<AIGatewayManagementAPI.Models.ModelRestrictionDto> ParseModelRestrictions(string policyXml)
    {
        var results = new List<AIGatewayManagementAPI.Models.ModelRestrictionDto>();
        var matches = _modelWhenRegex.Matches(policyXml);

        foreach (System.Text.RegularExpressions.Match m in matches)
        {
            var groupId = m.Groups["groupId"].Value;
            var modelsRaw = m.Groups["models"].Value;
            // Models are regex-escaped and pipe-delimited; unescape them
            var models = modelsRaw.Split('|')
                .Select(s => System.Text.RegularExpressions.Regex.Unescape(s))
                .ToList();

            results.Add(new AIGatewayManagementAPI.Models.ModelRestrictionDto
            {
                GroupId = groupId,
                AllowedModels = models
            });
        }

        return results;
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
