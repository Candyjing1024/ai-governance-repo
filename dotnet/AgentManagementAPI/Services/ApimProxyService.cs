using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Azure.Core;
using Azure.Identity;
using AgentManagementAPI.Exceptions;

namespace AgentManagementAPI.Services;

/// <summary>
/// Proxies agent requests through APIM gateway instead of calling Foundry directly.
/// Authenticates with a token for the APIM app registration audience.
/// </summary>
public class ApimProxyService
{
    private readonly HttpClient _httpClient;
    private readonly DefaultAzureCredential _credential;
    private readonly string _gatewayBase;
    private readonly string _apiVersion;
    private readonly ILogger<ApimProxyService> _logger;

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    public ApimProxyService(HttpClient httpClient, IConfiguration configuration, ILogger<ApimProxyService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;

        var tenantId = configuration["AzureFoundry:TenantId"];
        _credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
        {
            TenantId = tenantId,
            ExcludeEnvironmentCredential = true,
            ExcludeManagedIdentityCredential = true,
            ExcludeSharedTokenCacheCredential = true,
            ExcludeWorkloadIdentityCredential = true
        });

        _gatewayBase = configuration["ApimGateway:BaseUrl"]!.TrimEnd('/');
        _apiVersion = configuration["ApimGateway:ApiVersion"] ?? "2025-05-15-preview";

        var audience = configuration["ApimGateway:Audience"]!;
        // Store audience as scope for token acquisition
        _tokenScope = $"api://{audience}/.default";
    }

    private readonly string _tokenScope;

    private string BaseUrl(string apiPath) => $"{_gatewayBase}/{apiPath.Trim('/')}";

    private string WithApiVersion(string url) => $"{url}?api-version={_apiVersion}";

    // In-memory message store (mirrors AgentService pattern)
    private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, List<StoredMessage>> _messageStore = new();

    private record StoredMessage(string Id, string Role, string Content, long CreatedAt);

    public async Task<JsonDocument> CreateThreadAsync(string apiPath, object? body)
    {
        var url = $"{BaseUrl(apiPath)}/openai/v1/conversations";
        return await SendAsync(HttpMethod.Post, url, body, "create conversation via APIM");
    }

    public JsonDocument CreateMessageSync(string threadId, string role, string content)
    {
        var msg = new StoredMessage($"msg_{Guid.NewGuid():N}", role, content, DateTimeOffset.UtcNow.ToUnixTimeSeconds());
        _messageStore.AddOrUpdate(threadId,
            _ => [msg],
            (_, list) => { lock (list) { list.Add(msg); } return list; });

        _logger.LogInformation("APIM proxy: stored message '{MsgId}' on conversation '{ConvId}'", msg.Id, threadId);
        var json = JsonSerializer.Serialize(new { id = msg.Id, @object = "message", thread_id = threadId }, _jsonOptions);
        return JsonDocument.Parse(json);
    }

    public JsonDocument ListMessagesSync(string threadId)
    {
        var messages = _messageStore.TryGetValue(threadId, out var list)
            ? list.Select(m => new
            {
                id = m.Id,
                role = m.Role,
                content = new[] { new { type = "text", text = new { value = m.Content } } },
                created_at = m.CreatedAt
            }).ToList()
            : [];
        var json = JsonSerializer.Serialize(new { data = messages }, _jsonOptions);
        return JsonDocument.Parse(json);
    }

    public async Task<JsonDocument> CreateRunAsync(string apiPath, string conversationId, string agentName)
    {
        // Get the last user message from the store
        var lastUserMsg = _messageStore.TryGetValue(conversationId, out var msgs)
            ? msgs.LastOrDefault(m => m.Role == "user")
            : null;
        var inputText = lastUserMsg?.Content ?? "";

        var body = new
        {
            agent_reference = new { type = "agent_reference", name = agentName },
            conversation = conversationId,
            input = new[] { new { role = "user", content = inputText } }
        };

        var url = $"{BaseUrl(apiPath)}/openai/v1/responses";
        var result = await SendAsync(HttpMethod.Post, url, body, "create response via APIM");

        // Extract assistant reply and store it
        var root = result.RootElement;
        var outputText = ExtractOutputText(root);
        var assistantMsg = new StoredMessage($"msg_{Guid.NewGuid():N}", "assistant", outputText, DateTimeOffset.UtcNow.ToUnixTimeSeconds());
        _messageStore.AddOrUpdate(conversationId,
            _ => [assistantMsg],
            (_, list) => { lock (list) { list.Add(assistantMsg); } return list; });

        return result;
    }

    public JsonDocument GetRunSync(string threadId, string runId)
    {
        var json = JsonSerializer.Serialize(new { id = runId, status = "completed", thread_id = threadId }, _jsonOptions);
        return JsonDocument.Parse(json);
    }

    private static string ExtractOutputText(JsonElement root)
    {
        if (root.TryGetProperty("output_text", out var ot))
            return ot.GetString() ?? "";

        if (root.TryGetProperty("output", out var output) && output.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in output.EnumerateArray())
            {
                if (item.TryGetProperty("type", out var t) && t.GetString() == "message"
                    && item.TryGetProperty("content", out var contentArr))
                {
                    foreach (var c in contentArr.EnumerateArray())
                    {
                        if (c.TryGetProperty("type", out var ct) && ct.GetString() == "output_text"
                            && c.TryGetProperty("text", out var text))
                            return text.GetString() ?? "";
                    }
                }
            }
        }
        return "";
    }

    private async Task<JsonDocument> SendAsync(HttpMethod method, string url, object? body, string operation)
    {
        var request = new HttpRequestMessage(method, url);
        if (body is not null)
            request.Content = new StringContent(
                JsonSerializer.Serialize(body, _jsonOptions), Encoding.UTF8, "application/json");

        try
        {
            var token = await _credential.GetTokenAsync(new TokenRequestContext([_tokenScope]));
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to acquire token for APIM audience scope '{Scope}'", _tokenScope);
            throw new ApiException(HttpStatusCode.Unauthorized,
                $"Failed to acquire token for APIM. Ensure the app registration has the correct API permissions. Error: {ex.Message}");
        }

        _logger.LogInformation("APIM Proxy: {Method} {Url}", method, url);
        var response = await _httpClient.SendAsync(request);

        var content = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
        {
            _logger.LogError("APIM proxy error during {Op}: {Status} {Content}",
                operation, (int)response.StatusCode, content[..Math.Min(content.Length, 500)]);

            throw response.StatusCode switch
            {
                HttpStatusCode.Unauthorized => new ApiException(HttpStatusCode.Unauthorized,
                    $"APIM returned 401 Unauthorized. Check JWT token and policy audience. Details: {content[..Math.Min(content.Length, 300)]}"),
                HttpStatusCode.Forbidden => new ApiException(HttpStatusCode.Forbidden,
                    $"APIM returned 403 Forbidden. User may not be in an authorized group. Details: {content[..Math.Min(content.Length, 300)]}"),
                HttpStatusCode.NotFound => new NotFoundException(
                    $"APIM returned 404. Check that the API and operations are configured. Details: {content[..Math.Min(content.Length, 300)]}"),
                _ => new ApiException(HttpStatusCode.BadGateway,
                    $"APIM proxy error during {operation}: HTTP {(int)response.StatusCode} — {content[..Math.Min(content.Length, 300)]}")
            };
        }

        return JsonDocument.Parse(content);
    }
}
