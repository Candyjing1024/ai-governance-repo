# Azure API Management (APIM) Scripts

Scripts and documentation for Azure API Management integration with Foundry and AI services.

## Overview

This folder contains PowerShell scripts for setting up Azure API Management as an AI Gateway, integrating with Microsoft Foundry, implementing semantic caching, and managing product-based access control.

## Architecture

```
Client → APIM (AI Gateway) → Foundry/OpenAI → Response
           ↓
     Semantic Cache
     Token Management
     Rate Limiting
```

## Scripts

### Setup Scripts

#### `00-Config.ps1`
Configuration file with all variables.

**Variables:**
```powershell
$subscriptionId = "<your-subscription-id>"
$resourceGroup = "<your-resource-group>"
$location = "<location>"  # e.g., eastus
$apimName = "<apim-service-name>"
$foundryEndpoint = "https://..."
```

#### `01-Create-ServicePrincipal.ps1`
Creates service principal for APIM authentication.

**What it creates:**
- App registration in Entra ID
- Service principal
- Client secret
- RBAC assignments

**Usage:**
```powershell
.\01-Create-ServicePrincipal.ps1
```

#### `02-Create-APIM.ps1`
Creates Azure API Management instance.

**What it creates:**
- APIM resource (Developer or Premium tier)
- Virtual network integration (optional)
- Managed identity
- Initial configuration

**Usage:**
```powershell
.\02-Create-APIM.ps1
```

**Note:** APIM creation takes 30-45 minutes.

#### `03-Register-FoundryInAPIM.ps1`
Registers Foundry API in APIM.

**What it configures:**
- API definition
- Operations (invoke agent, create thread, send message)
- Backend configuration
- Authentication policies

**Usage:**
```powershell
.\03-Register-FoundryInAPIM.ps1
```

### Testing Scripts

#### `04-Test-Token-Flow.ps1`
Tests OAuth token flow.

**What it tests:**
1. Get token from Entra ID
2. Call APIM with token
3. APIM forwards to Foundry
4. Response returned

**Usage:**
```powershell
.\04-Test-Token-Flow.ps1
```

#### `05-Full-Demo.ps1`
Complete end-to-end demo.

**Demo flow:**
1. Create service principal
2. Deploy APIM
3. Register Foundry API
4. Test token flow
5. Invoke agent
6. Show semantic cache

**Usage:**
```powershell
.\05-Full-Demo.ps1
```

### AI Gateway Scripts

#### `06-Create-AIGateway-SDK.ps1`
Creates AI Gateway using APIM SDK approach.

**Features:**
- Azure OpenAI integration
- Token management
- Rate limiting
- Response streaming

**Usage:**
```powershell
.\06-Create-AIGateway-SDK.ps1
```

#### `06b-Create-AIGateway-REST.ps1`
Creates AI Gateway using REST API approach.

**Features:**
- Direct REST API calls
- Custom policies
- More control over configuration

**Usage:**
```powershell
.\06b-Create-AIGateway-REST.ps1
```

#### `07-Test-AIGateway.ps1`
Tests AI Gateway functionality.

**What it tests:**
- OpenAI completion requests
- Streaming responses
- Rate limiting
- Semantic cache hits
- Error handling

**Usage:**
```powershell
.\07-Test-AIGateway.ps1
```

### Test Commands

#### `Test-APIM-Commands.txt`
Collection of curl/PowerShell commands for testing.

**Examples:**
```bash
# Test health endpoint
curl https://apim-chubb-mcp-poc.azure-api.net/health

# Invoke agent
curl -X POST https://apim-chubb-mcp-poc.azure-api.net/agents/invoke \
  -H "Ocp-Apim-Subscription-Key: $KEY" \
  -d '{"message": "Hello"}'
```

## Documentation

### `APIM-Foundry-Integration-Guide-Updated.txt`
Complete guide for APIM + Foundry integration.

**Sections:**
1. Prerequisites
2. Service principal setup
3. APIM creation
4. Foundry registration
5. Policy configuration
6. Testing

### `APIM-Product-Based-Access-Control-Guide.txt`
Guide for implementing product-based access control.

**Topics:**
- Product creation
- Subscription management
- Rate limit policies
- User groups
- API visibility

### `APIM-Semantic-Cache-POC-End-to-End.txt`
End-to-end guide for semantic caching.

**Sections:**
1. Cache setup
2. Similarity detection
3. Cache hit/miss handling
4. Performance metrics

### `APIM-Semantic-Cache-Solution.txt`
Technical solution for semantic caching.

**Implementation:**
- Vector embeddings for cache keys
- Cosine similarity matching
- TTL configuration
- Cache invalidation

### `AI-Gateway-Scripts-Guide.txt`
Guide for AI Gateway scripts (06, 06b, 07).

### `AI-Gateway-Quick-Reference.txt`
Quick reference for common AI Gateway operations.

## Key Features

### 1. Token Management
```xml
<policies>
  <inbound>
    <authentication-managed-identity resource="https://cognitiveservices.azure.com"/>
  </inbound>
</policies>
```

### 2. Rate Limiting
```xml
<rate-limit calls="100" renewal-period="60"/>
<quota calls="10000" renewal-period="86400"/>
```

### 3. Semantic Caching
```xml
<cache-lookup-value key="@(context.Request.Body.As<string>())" variable-name="cachedResponse"/>
<choose>
  <when condition="@(context.Variables.ContainsKey("cachedResponse"))">
    <return-response>
      <set-body>@((string)context.Variables["cachedResponse"])</set-body>
    </return-response>
  </when>
</choose>
```

### 4. Request Transformation
```xml
<set-header name="Content-Type" exists-action="override">
  <value>application/json</value>
</set-header>
<set-backend-service base-url="https://foundry.azure.com"/>
```

## Common Operations

### Setup APIM + Foundry
```powershell
.\00-Config.ps1
.\01-Create-ServicePrincipal.ps1
.\02-Create-APIM.ps1
.\03-Register-FoundryInAPIM.ps1
.\04-Test-Token-Flow.ps1
```

### Setup AI Gateway
```powershell
.\06-Create-AIGateway-SDK.ps1
.\07-Test-AIGateway.ps1
```

### Test Everything
```powershell
.\05-Full-Demo.ps1
```

## Configuration

### Products
- **Starter**: 10 requests/minute, 1000/day
- **Professional**: 100 requests/minute, 100000/day
- **Enterprise**: Unlimited

### Policies
- Authentication (OAuth 2.0, Managed Identity)
- Rate limiting per product
- Semantic caching (5 min TTL)
- Request/response logging

## Monitoring

### View logs
```powershell
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ApiManagementGatewayLogs | take 100"
```

### View metrics
- Request count
- Response time
- Error rate
- Cache hit ratio

## Troubleshooting

### Authentication Fails
Check:
1. Service principal credentials
2. RBAC assignments
3. Token expiration

### API Not Found
Check:
1. API registered in APIM
2. Operations defined
3. Backend URL correct

### Cache Not Working
Check:
1. Cache policy enabled
2. TTL configured
3. Cache key format

## Security Best Practices

1. **Use Managed Identity** for Azure service authentication
2. **Rotate subscription keys** every 90 days
3. **Enable VNet integration** for production
4. **Use products** for access control
5. **Log all requests** for audit

## References

- [Azure APIM Documentation](https://docs.microsoft.com/azure/api-management/)
- [APIM Policies](https://docs.microsoft.com/azure/api-management/api-management-policies)
- [Semantic Caching](https://docs.microsoft.com/azure/api-management/api-management-howto-cache)
