# ============================================================
# Step 5 : Customer-Facing Demo (clean, self-contained)
# ============================================================
# This is the script you show the customer.
#
# It demonstrates the complete flow they asked for:
#   1. Service Principal authenticates via APIM's /auth/token
#   2. Gets a JWT from Azure AD (through APIM)
#   3. Uses that JWT to call the LLM (through APIM)
#   4. Without the JWT, the LLM returns 401
#
# Zero az login.  Zero interactive sign-in.  Pure REST.
# ============================================================

. "$PSScriptRoot\00-Config.ps1"

$ArmBase = "https://management.azure.com"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host "  APIM + FOUNDRY LLM - FULL DEMO" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

# -------------------------------------------------------
# Resolve APIM gateway URL
# -------------------------------------------------------
Write-Host "[Setup] Resolving APIM gateway..." -ForegroundColor Cyan
$headers    = Get-ArmHeaders
$apimUrl    = "$ArmBase/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup" +
              "/providers/Microsoft.ApiManagement/service/$ApimServiceName" +
              "?api-version=$ApimApiVersion"
$apimInfo   = Invoke-RestMethod -Method GET -Uri $apimUrl -Headers $headers
$gatewayUrl = $apimInfo.properties.gatewayUrl

Write-Host "  Gateway: $gatewayUrl" -ForegroundColor Green
Write-Host ""

# =============================================================
#  STEP 1 :  Prove the LLM is locked (no-token test)
# =============================================================
Write-Host "-----------------------------------------------------" -ForegroundColor Cyan
Write-Host "  STEP 1 : Verify LLM rejects unauthenticated calls" -ForegroundColor Cyan
Write-Host "-----------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

$llmUrl = "$gatewayUrl/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion"

$dummyBody = @{
    messages   = @( @{ role = "user"; content = "test" } )
    max_tokens = 10
} | ConvertTo-Json -Depth 4

$blocked = $false

try {
    Invoke-WebRequest -Method POST -Uri $llmUrl `
        -Headers @{ "Content-Type" = "application/json" } `
        -Body $dummyBody -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host "  WARNING: Request was NOT blocked. Check APIM policies." -ForegroundColor Red
}
catch {
    $sc = $null
    try { $sc = $_.Exception.Response.StatusCode.value__ } catch {}
    if ($sc -eq 401) {
        $blocked = $true
        Write-Host "  HTTP 401 - LLM correctly rejected the call." -ForegroundColor Green
        Write-Host "  Without a token, nobody gets in." -ForegroundColor Green
    }
    else {
        Write-Host "  Got HTTP $sc (expected 401)." -ForegroundColor Yellow
    }
}

Write-Host ""

# =============================================================
#  STEP 2 :  Generate a token through APIM /auth/token
# =============================================================
Write-Host "-----------------------------------------------------" -ForegroundColor Cyan
Write-Host "  STEP 2 : Acquire JWT via APIM /auth/token" -ForegroundColor Cyan
Write-Host "-----------------------------------------------------" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Using Service Principal: $SpClientId" -ForegroundColor Gray
Write-Host "  Grant type: client_credentials" -ForegroundColor Gray
Write-Host "  Scope: https://cognitiveservices.azure.com/.default" -ForegroundColor Gray
Write-Host ""

$tokenEndpoint = "$gatewayUrl/auth/token"

$tokenBody = "grant_type=client_credentials" +
             "&client_id=$SpClientId" +
             "&client_secret=$([System.Uri]::EscapeDataString($SpClientSecret))" +
             "&scope=https://cognitiveservices.azure.com/.default"

$jwt = $null

try {
    $tokenResp = Invoke-RestMethod -Method POST `
        -Uri $tokenEndpoint `
        -Body $tokenBody `
        -ContentType "application/x-www-form-urlencoded"

    $jwt       = $tokenResp.access_token
    $expiresIn = $tokenResp.expires_in
    $tokenType = $tokenResp.token_type

    Write-Host "  Token acquired." -ForegroundColor Green
    Write-Host "  Type       : $tokenType" -ForegroundColor Gray
    Write-Host "  Expires in : $expiresIn seconds" -ForegroundColor Gray
    Write-Host "  JWT preview: $($jwt.Substring(0, [Math]::Min(60, $jwt.Length)))..." -ForegroundColor Gray
}
catch {
    Write-Host "  FAILED to get token." -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    try { Write-Host "  $($_.ErrorDetails.Message)" -ForegroundColor Red } catch {}
    exit 1
}

Write-Host ""

# =============================================================
#  STEP 3 :  Call the LLM using the token
# =============================================================
Write-Host "-----------------------------------------------------" -ForegroundColor Cyan
Write-Host "  STEP 3 : Call LLM via APIM with Bearer token" -ForegroundColor Cyan
Write-Host "-----------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

$chatBody = @{
    messages    = @(
        @{
            role    = "system"
            content = "You are a helpful assistant. Keep answers to two sentences."
        },
        @{
            role    = "user"
            content = "What is Azure API Management and why is it important for governing AI model access in an enterprise?"
        }
    )
    max_tokens  = 200
    temperature = 0.7
} | ConvertTo-Json -Depth 4

$chatHeaders = @{
    "Authorization" = "Bearer $jwt"
    "Content-Type"  = "application/json"
}

try {
    $chatResp = Invoke-RestMethod -Method POST -Uri $llmUrl -Headers $chatHeaders -Body $chatBody
    $answer   = $chatResp.choices[0].message.content

    Write-Host "  LLM Response:" -ForegroundColor Green
    Write-Host ""
    Write-Host "  $answer" -ForegroundColor White
    Write-Host ""
    Write-Host "  Model   : $($chatResp.model)" -ForegroundColor Gray
    Write-Host "  Tokens  : prompt=$($chatResp.usage.prompt_tokens), completion=$($chatResp.usage.completion_tokens), total=$($chatResp.usage.total_tokens)" -ForegroundColor Gray
}
catch {
    Write-Host "  FAILED" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    try { Write-Host "  $($_.ErrorDetails.Message)" -ForegroundColor Red } catch {}
    exit 1
}

# =============================================================
#  FINAL SUMMARY
# =============================================================
Write-Host ""
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Green
Write-Host "    P O C   C O M P L E T E" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Architecture:" -ForegroundColor White
Write-Host ""
Write-Host "    +-------------------+       +--------+       +-------------------+"
Write-Host "    | Service Principal | ----> |  APIM  | ----> | Azure AI Foundry  |"
Write-Host "    | (client creds)    |       |        |       | (gpt-4o)          |"
Write-Host "    +-------------------+       +--------+       +-------------------+"
Write-Host ""
Write-Host "  What APIM does:" -ForegroundColor White
Write-Host "    1. /auth/token - proxies to Azure AD, returns JWT"
Write-Host "    2. /openai/... - validates JWT (rejects 401 if missing)"
Write-Host "    3. Injects the real Foundry api-key (callers never see it)"
Write-Host "    4. Proxies request to Foundry, returns the response"
Write-Host ""
Write-Host "  Security guarantees:" -ForegroundColor White
Write-Host "    - LLM is NOT accessible without a valid token"
Write-Host "    - Tokens are only issued to registered Service Principals"
Write-Host "    - Foundry API key is never exposed to callers"
Write-Host "    - All traffic flows through APIM (audit, throttle, monitor)"
Write-Host ""
Write-Host "  Endpoints:" -ForegroundColor Gray
Write-Host "    Token   : POST $gatewayUrl/auth/token"
Write-Host "    LLM     : POST $gatewayUrl/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion"
Write-Host ""
Write-Host "  SP Client ID : $SpClientId"
Write-Host "  APIM Gateway : $gatewayUrl"
Write-Host ""
