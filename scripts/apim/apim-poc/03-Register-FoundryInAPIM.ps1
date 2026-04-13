# ============================================================
# Step 3 : Register TWO APIs in APIM (Token + LLM)
# ============================================================
# SECURITY MODEL (what the customer asked for)
#
#   API 1 - POST /auth/token
#     Token generation endpoint.  Caller sends SP credentials,
#     APIM proxies to Azure AD, returns a JWT.
#     This is the ONLY way to get a token.
#
#   API 2 - POST /openai/deployments/gpt-4o/chat/completions
#     LLM endpoint.  Protected by validate-jwt policy.
#     No valid Bearer token = HTTP 401.  Not accessible without
#     first calling /auth/token.
#
#   Flow:
#     Caller -> POST /auth/token (SP creds) -> JWT
#     Caller -> POST /openai/... + Bearer JWT -> APIM validates
#               -> APIM injects Foundry api-key -> gpt-4o -> response
#
# PREREQUISITES
#   - Steps 01, 02 completed
#   - APIM provisioned and healthy
# ============================================================

. "$PSScriptRoot\00-Config.ps1"

$ArmBase = "https://management.azure.com"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host "  STEP 3 - Register APIs in APIM (Token + LLM)" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

# -------------------------------------------------------
# 1. Authenticate
# -------------------------------------------------------
Write-Host "[1/7] Authenticating as Service Principal..." -ForegroundColor Cyan
$headers = Get-ArmHeaders
Write-Host "  Token acquired." -ForegroundColor Green

$apimBase = "$ArmBase/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup" +
            "/providers/Microsoft.ApiManagement/service/$ApimServiceName"

# -------------------------------------------------------
# 2. Retrieve the Foundry API key
# -------------------------------------------------------
Write-Host ""
Write-Host "[2/7] Retrieving Foundry (CognitiveServices) API key..." -ForegroundColor Cyan

$keysUrl = "$ArmBase/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup" +
           "/providers/Microsoft.CognitiveServices/accounts/$FoundryAccountName" +
           "/listKeys?api-version=2024-10-01"

try {
    $keys = Invoke-RestMethod -Method POST -Uri $keysUrl -Headers $headers
    $foundryKey = $keys.key1
    Write-Host "  Got API key (key1)." -ForegroundColor Green
}
catch {
    Write-Host "  Could not retrieve key: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# -------------------------------------------------------
# 3. Store the Foundry key as a Named Value (secret)
# -------------------------------------------------------
Write-Host ""
Write-Host "[3/7] Storing Foundry key as APIM Named Value..." -ForegroundColor Cyan

$nvUrl = "$apimBase/namedValues/foundry-api-key?api-version=$ApimApiVersion"

$nvBody = @{
    properties = @{
        displayName = "foundry-api-key"
        value       = $foundryKey
        secret      = $true
        tags        = @("foundry", "openai", "secret")
    }
} | ConvertTo-Json -Depth 4

try {
    Invoke-RestMethod -Method PUT -Uri $nvUrl -Headers $headers -Body $nvBody | Out-Null
    Write-Host "  Named value 'foundry-api-key' stored." -ForegroundColor Green
}
catch {
    $sc = $null
    try { $sc = $_.Exception.Response.StatusCode.value__ } catch {}
    if ($sc -eq 202) {
        Write-Host "  Accepted (async). Waiting 15s..." -ForegroundColor Gray
        Start-Sleep -Seconds 15
    }
    else {
        Write-Host "  Warning: $($_.Exception.Message) (may already exist)" -ForegroundColor Yellow
    }
}

# ===============================================================
#  API 1 :  Token Generation  (POST /auth/token)
# ===============================================================
Write-Host ""
Write-Host "[4/7] Creating 'auth' API - token generation endpoint..." -ForegroundColor Cyan

$authApiId  = "auth-api"
$authApiUrl = "$apimBase/apis/${authApiId}?api-version=$ApimApiVersion"

$authApiBody = @{
    properties = @{
        displayName          = "Auth - Token Generation"
        description          = "Generates an OAuth2 JWT via Azure AD. Caller POST SP client_id, client_secret, grant_type and scope. Returns a Bearer token needed for the LLM API."
        path                 = "auth"
        protocols            = @("https")
        serviceUrl           = "https://login.microsoftonline.com"
        subscriptionRequired = $false
        apiType              = "http"
    }
} | ConvertTo-Json -Depth 5

try {
    Invoke-RestMethod -Method PUT -Uri $authApiUrl -Headers $headers -Body $authApiBody | Out-Null
    Write-Host "  API 'auth' created at /auth" -ForegroundColor Green
}
catch {
    Write-Host "  Warning: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Operation: POST /auth/token
Write-Host "  Adding POST /auth/token operation..." -ForegroundColor Gray

$authOpUrl = "$apimBase/apis/${authApiId}/operations/get-token?api-version=$ApimApiVersion"

$authOpBody = @{
    properties = @{
        displayName = "Get Access Token"
        method      = "POST"
        urlTemplate = "/token"
        description = "Exchange Service Principal credentials for a JWT. Body: grant_type=client_credentials, client_id, client_secret, scope=https://cognitiveservices.azure.com/.default (form-urlencoded)."
        request     = @{
            description     = "OAuth2 client_credentials grant"
            representations = @(
                @{ contentType = "application/x-www-form-urlencoded" }
            )
        }
        responses   = @(
            @{ statusCode = 200; description = "JWT access token" },
            @{ statusCode = 401; description = "Invalid credentials" }
        )
    }
} | ConvertTo-Json -Depth 8

try {
    Invoke-RestMethod -Method PUT -Uri $authOpUrl -Headers $headers -Body $authOpBody | Out-Null
    Write-Host "  Operation 'get-token' created." -ForegroundColor Green
}
catch {
    Write-Host "  Warning: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Policy: rewrite backend to Azure AD token endpoint for this tenant
$authPolicyXml = @"
<policies>
    <inbound>
        <base />
        <set-backend-service base-url="https://login.microsoftonline.com/$TenantId/oauth2/v2.0" />
        <rewrite-uri template="/token" copy-unmatched-params="true" />
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
</policies>
"@

$authPolUrl  = "$apimBase/apis/${authApiId}/policies/policy?api-version=$ApimApiVersion"
$authPolBody = @{
    properties = @{ value = $authPolicyXml; format = "xml" }
} | ConvertTo-Json -Depth 4

try {
    Invoke-RestMethod -Method PUT -Uri $authPolUrl -Headers $headers -Body $authPolBody | Out-Null
    Write-Host "  Auth API policy applied (rewrite to Azure AD)." -ForegroundColor Green
}
catch {
    Write-Host "  Policy error: $($_.Exception.Message)" -ForegroundColor Red
}

# ===============================================================
#  API 2 :  LLM endpoint  (POST /openai/...)
#           JWT-protected - NO TOKEN = 401
# ===============================================================
Write-Host ""
Write-Host "[5/7] Creating 'azure-openai' API - JWT-protected LLM..." -ForegroundColor Cyan

$llmApiId  = "azure-openai"
$llmApiUrl = "$apimBase/apis/${llmApiId}?api-version=$ApimApiVersion"

$llmApiBody = @{
    properties = @{
        displayName          = "Azure OpenAI (Foundry) - Token Protected"
        description          = "Proxy to Foundry gpt-4o. Requires a valid Bearer JWT from /auth/token. Requests without a token return 401."
        path                 = "openai"
        protocols            = @("https")
        serviceUrl           = "$FoundryEndpoint/openai"
        subscriptionRequired = $false
        apiType              = "http"
    }
} | ConvertTo-Json -Depth 5

try {
    Invoke-RestMethod -Method PUT -Uri $llmApiUrl -Headers $headers -Body $llmApiBody | Out-Null
    Write-Host "  API 'azure-openai' created at /openai" -ForegroundColor Green
}
catch {
    Write-Host "  Warning: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Operation: POST chat completions
Write-Host "  Adding chat-completions operation..." -ForegroundColor Gray

$llmOpUrl = "$apimBase/apis/${llmApiId}/operations/chat-completions?api-version=$ApimApiVersion"

$llmOpBody = @{
    properties = @{
        displayName = "Chat Completions"
        method      = "POST"
        urlTemplate = "/deployments/$ModelDeploymentName/chat/completions"
        description = "Chat with gpt-4o. Requires Authorization: Bearer <jwt> header."
        templateParameters = @()
        request     = @{
            queryParameters = @(
                @{ name = "api-version"; type = "string"; required = $true; defaultValue = $OpenAIApiVersion }
            )
            representations = @(
                @{ contentType = "application/json" }
            )
        }
        responses   = @(
            @{ statusCode = 200; description = "Chat completion response" },
            @{ statusCode = 401; description = "Missing or invalid Bearer token" }
        )
    }
} | ConvertTo-Json -Depth 8

try {
    Invoke-RestMethod -Method PUT -Uri $llmOpUrl -Headers $headers -Body $llmOpBody | Out-Null
    Write-Host "  Operation 'chat-completions' created." -ForegroundColor Green
}
catch {
    Write-Host "  Warning: $($_.Exception.Message)" -ForegroundColor Yellow
}

# -------------------------------------------------------
# 6. Apply JWT validation policy on LLM API
# -------------------------------------------------------
Write-Host ""
Write-Host "[6/7] Applying validate-jwt policy on LLM API..." -ForegroundColor Cyan
Write-Host "  This is the security gate - no token means 401." -ForegroundColor Gray

$llmPolicyXml = @"
<policies>
    <inbound>
        <base />
        <!-- SECURITY: Reject requests without a valid Azure AD JWT -->
        <validate-jwt header-name="Authorization"
                      failed-validation-httpcode="401"
                      failed-validation-error-message="Access denied. Provide a valid Bearer token from POST /auth/token.">
            <openid-config url="https://login.microsoftonline.com/$TenantId/v2.0/.well-known/openid-configuration" />
            <audiences>
                <audience>https://cognitiveservices.azure.com</audience>
            </audiences>
            <issuers>
                <issuer>https://sts.windows.net/$TenantId/</issuer>
            </issuers>
        </validate-jwt>
        <!-- Strip caller's auth header, inject the real Foundry key -->
        <set-header name="Authorization" exists-action="delete" />
        <set-header name="api-key" exists-action="override">
            <value>{{foundry-api-key}}</value>
        </set-header>
        <set-backend-service base-url="$FoundryEndpoint/openai" />
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
</policies>
"@

$llmPolUrl  = "$apimBase/apis/${llmApiId}/policies/policy?api-version=$ApimApiVersion"
$llmPolBody = @{
    properties = @{ value = $llmPolicyXml; format = "xml" }
} | ConvertTo-Json -Depth 4

try {
    Invoke-RestMethod -Method PUT -Uri $llmPolUrl -Headers $headers -Body $llmPolBody | Out-Null
    Write-Host "  JWT validation policy applied." -ForegroundColor Green
    Write-Host "  LLM API is LOCKED - only valid tokens get through." -ForegroundColor Green
}
catch {
    Write-Host "  Policy error: $($_.Exception.Message)" -ForegroundColor Red
    try {
        $d = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Host "  Detail: $($d.error.message)" -ForegroundColor Red
    } catch {}
}

# -------------------------------------------------------
# 7. Summary
# -------------------------------------------------------
Write-Host ""
Write-Host "[7/7] Verifying registrations..." -ForegroundColor Cyan

$apisUrl = "$apimBase/apis?api-version=$ApimApiVersion"
$allApis = Invoke-RestMethod -Method GET -Uri $apisUrl -Headers $headers
$custom  = $allApis.value | Where-Object { $_.properties.path -in @("auth", "openai") }

foreach ($a in $custom) {
    Write-Host "  API: $($a.properties.displayName)  ->  /$($a.properties.path)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Green
Write-Host "  BOTH APIs REGISTERED - TOKEN SECURITY ACTIVE" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API 1 - Token Generation:" -ForegroundColor White
Write-Host "    POST <gateway>/auth/token"
Write-Host "    Body: grant_type=client_credentials&client_id=...&client_secret=...&scope=https://cognitiveservices.azure.com/.default"
Write-Host "    Returns: { access_token: <jwt>, ... }"
Write-Host ""
Write-Host "  API 2 - LLM (Chat Completions):" -ForegroundColor White
Write-Host "    POST <gateway>/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion"
Write-Host "    Header: Authorization: Bearer <jwt from API 1>"
Write-Host "    Without token -> 401 Unauthorized"
Write-Host ""
Write-Host "  Next -> Run 04-Test-Token-Flow.ps1"
Write-Host ""
