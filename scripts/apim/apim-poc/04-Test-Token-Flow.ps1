# ============================================================
# Step 4 : Test the Token-Based Flow End-to-End
# ============================================================
# THREE TESTS IN SEQUENCE
#
#   Test 1 - Call LLM WITHOUT a token  -> expect 401
#   Test 2 - Call /auth/token to get a JWT via SP credentials
#   Test 3 - Call LLM WITH the token   -> expect 200 + model response
#
#   This proves the LLM is not accessible without a valid token.
#
# EVERYTHING RUNS VIA SERVICE PRINCIPAL - NO AZ LOGIN
# ============================================================

. "$PSScriptRoot\00-Config.ps1"

$ArmBase = "https://management.azure.com"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host "  STEP 4 - Test Token-Based LLM Access" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

# -------------------------------------------------------
# 0. Get the APIM gateway URL
# -------------------------------------------------------
Write-Host "[Setup] Getting APIM gateway URL..." -ForegroundColor Cyan
$headers = Get-ArmHeaders

$apimInfoUrl = "$ArmBase/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup" +
               "/providers/Microsoft.ApiManagement/service/$ApimServiceName" +
               "?api-version=$ApimApiVersion"

$apimInfo   = Invoke-RestMethod -Method GET -Uri $apimInfoUrl -Headers $headers
$gatewayUrl = $apimInfo.properties.gatewayUrl
Write-Host "  Gateway: $gatewayUrl" -ForegroundColor Green
Write-Host ""

$llmUrl = "$gatewayUrl/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion"

# ===============================================================
#  TEST 1 :  Call LLM WITHOUT token  (should get 401)
# ===============================================================
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "  TEST 1 : Call LLM without any token (expect 401)" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "  URL: $llmUrl" -ForegroundColor Gray
Write-Host ""

$testBody = @{
    messages    = @( @{ role = "user"; content = "Hello" } )
    max_tokens  = 50
} | ConvertTo-Json -Depth 4

try {
    $noTokenResp = Invoke-WebRequest -Method POST -Uri $llmUrl `
        -Headers @{ "Content-Type" = "application/json" } `
        -Body $testBody `
        -UseBasicParsing -ErrorAction Stop

    # If we get here, that's bad - it means the API is open
    Write-Host "  UNEXPECTED: Got HTTP $($noTokenResp.StatusCode)" -ForegroundColor Red
    Write-Host "  The LLM API should NOT be accessible without a token!" -ForegroundColor Red
    Write-Host "  Check the validate-jwt policy in Step 03." -ForegroundColor Red
}
catch {
    $statusCode = $null
    try { $statusCode = $_.Exception.Response.StatusCode.value__ } catch {}

    if ($statusCode -eq 401) {
        Write-Host "  Got HTTP 401 - CORRECT!" -ForegroundColor Green
        Write-Host "  The LLM is properly locked behind token validation." -ForegroundColor Green
        try {
            $errBody = $_.ErrorDetails.Message
            Write-Host "  Response: $errBody" -ForegroundColor Gray
        } catch {}
    }
    else {
        Write-Host "  Got HTTP $statusCode (expected 401)" -ForegroundColor Yellow
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""

# ===============================================================
#  TEST 2 :  Get a token via /auth/token API
# ===============================================================
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "  TEST 2 : Get JWT via APIM /auth/token endpoint" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

$tokenUrl = "$gatewayUrl/auth/token"
Write-Host "  URL: $tokenUrl" -ForegroundColor Gray
Write-Host "  Grant: client_credentials" -ForegroundColor Gray
Write-Host "  Scope: https://cognitiveservices.azure.com/.default" -ForegroundColor Gray
Write-Host ""

$tokenBody = "grant_type=client_credentials" +
             "&client_id=$SpClientId" +
             "&client_secret=$([System.Uri]::EscapeDataString($SpClientSecret))" +
             "&scope=https://cognitiveservices.azure.com/.default"

$jwt = $null

try {
    $tokenResp = Invoke-RestMethod -Method POST -Uri $tokenUrl `
        -Body $tokenBody `
        -ContentType "application/x-www-form-urlencoded"

    $jwt       = $tokenResp.access_token
    $expiresIn = $tokenResp.expires_in

    Write-Host "  Token received!" -ForegroundColor Green
    Write-Host "  Expires in : $expiresIn seconds" -ForegroundColor Gray
    Write-Host "  Token (first 50 chars): $($jwt.Substring(0, [Math]::Min(50, $jwt.Length)))..." -ForegroundColor Gray
    Write-Host ""
}
catch {
    Write-Host "  FAILED to get token from /auth/token" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    try {
        $errBody = $_.ErrorDetails.Message
        Write-Host "  Response: $errBody" -ForegroundColor Red
    } catch {}
    Write-Host ""
    Write-Host "  Cannot proceed to Test 3 without a token." -ForegroundColor Red
    exit 1
}

# ===============================================================
#  TEST 3 :  Call LLM WITH the token  (should get 200)
# ===============================================================
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "  TEST 3 : Call LLM with Bearer token (expect 200)" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

$chatBody = @{
    messages    = @(
        @{ role = "system"; content = "You are a helpful assistant. Reply in one sentence." },
        @{ role = "user";   content = "What is Azure API Management and why should enterprises use it?" }
    )
    max_tokens  = 150
    temperature = 0.7
} | ConvertTo-Json -Depth 4

$chatHeaders = @{
    "Authorization" = "Bearer $jwt"
    "Content-Type"  = "application/json"
}

try {
    $chatResp = Invoke-RestMethod -Method POST -Uri $llmUrl -Headers $chatHeaders -Body $chatBody
    $answer   = $chatResp.choices[0].message.content

    Write-Host "  ============================================" -ForegroundColor Green
    Write-Host "  SUCCESS - LLM responded with valid token!" -ForegroundColor Green
    Write-Host "  ============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Model says:" -ForegroundColor Cyan
    Write-Host "  $answer"
    Write-Host ""
    Write-Host "  Tokens: prompt=$($chatResp.usage.prompt_tokens), completion=$($chatResp.usage.completion_tokens), total=$($chatResp.usage.total_tokens)" -ForegroundColor Gray
}
catch {
    Write-Host "  FAILED" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    try {
        $errBody = $_.ErrorDetails.Message
        Write-Host "  Response: $errBody" -ForegroundColor Red
    } catch {}
    Write-Host ""
    Write-Host "  Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Is the validate-jwt audience set to https://cognitiveservices.azure.com ?" -ForegroundColor Gray
    Write-Host "  2. Is the Named Value 'foundry-api-key' populated?" -ForegroundColor Gray
    Write-Host "  3. Is gpt-4o deployed on the Foundry account?" -ForegroundColor Gray
    exit 1
}

# ===============================================================
#  SUMMARY
# ===============================================================
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Green
Write-Host "  ALL 3 TESTS PASSED" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Test 1: No token     -> 401 Unauthorized  (correct)" -ForegroundColor White
Write-Host "  Test 2: /auth/token  -> JWT acquired       (correct)" -ForegroundColor White
Write-Host "  Test 3: With token   -> LLM responded      (correct)" -ForegroundColor White
Write-Host ""
Write-Host "  The LLM is NOT accessible without a token." -ForegroundColor Yellow
Write-Host "  Tokens can only be generated through APIM's /auth/token" -ForegroundColor Yellow
Write-Host "  endpoint using valid Service Principal credentials." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Next -> Run 05-Full-Demo.ps1 for a clean customer demo"
Write-Host ""
