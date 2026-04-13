# -----------------------------------------------------------------------
# 07-Test-AIGateway.ps1
#
# Runs a handful of tests against the AI Gateway we set up in step 06.
# Uses the Service Principal for authentication (no az login needed).
# Also prints curl commands at the end so you can test from any shell.
#
# What it tests:
#   1. Basic chat completion through the gateway (MI backend auth)
#   2. Chat completion with a subscription key
#   3. List deployed models
#   4. Chat with an SP JWT token
#   5. Negative test: wrong model name (should 404)
# -----------------------------------------------------------------------

. "$PSScriptRoot\00-Config.ps1"

$gatewayBase = "https://$ApimServiceName.azure-api.net"
$chatUrl     = "$gatewayBase/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion"

$chatBody = @{
    messages    = @(
        @{ role = "system"; content = "You are a helpful assistant." }
        @{ role = "user";   content = "Say hello from the AI Gateway in one sentence." }
    )
    max_tokens  = 50
    temperature = 0.7
} | ConvertTo-Json -Depth 5

Write-Host "`nTesting AI Gateway at $gatewayBase"
Write-Host "Model deployment: $ModelDeploymentName"
Write-Host ""

# ----- Test 1: Plain call, no caller auth (MI handles backend) -----
Write-Host "Test 1 - Chat completion (no caller auth, MI backend)..."

try {
    $r1 = Invoke-RestMethod -Method POST -Uri $chatUrl -Body $chatBody -ContentType "application/json"
    Write-Host "  200 OK"
    Write-Host "  Model : $($r1.model)"
    Write-Host "  Reply : $($r1.choices[0].message.content)"
    Write-Host "  Tokens: $($r1.usage.total_tokens) total"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "  $code - $($_.Exception.Message)"
}

# ----- Test 2: With APIM subscription key -----
Write-Host ""
Write-Host "Test 2 - Chat completion with subscription key..."

# Fetch the built-in master subscription key via ARM
try {
    $armToken = Get-SpToken -Scope "https://management.azure.com/.default"
    $secretsUrl = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.ApiManagement/service/$ApimServiceName/subscriptions/master/listSecrets?api-version=2024-05-01"
    $secrets = Invoke-RestMethod -Method POST -Uri $secretsUrl -Headers @{
        "Authorization" = "Bearer $armToken"
        "Content-Type"  = "application/json"
    }
    $subKey = $secrets.primaryKey

    $r2 = Invoke-RestMethod -Method POST -Uri $chatUrl -Body $chatBody -Headers @{
        "Content-Type"              = "application/json"
        "Ocp-Apim-Subscription-Key" = $subKey
    }
    Write-Host "  200 OK"
    Write-Host "  Reply : $($r2.choices[0].message.content)"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "  $code (this is fine if no product/subscription is configured yet)"
}

# ----- Test 3: List models -----
Write-Host ""
Write-Host "Test 3 - List models..."

$modelsUrl = "$gatewayBase/openai/models?api-version=$OpenAIApiVersion"

try {
    $r3 = Invoke-RestMethod -Method GET -Uri $modelsUrl -ContentType "application/json"
    Write-Host "  200 OK"
    foreach ($m in $r3.data) {
        Write-Host "  - $($m.id)"
    }
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "  $code - $($_.Exception.Message)"
}

# ----- Test 4: Call with SP JWT token -----
Write-Host ""
Write-Host "Test 4 - Chat with SP JWT token..."

try {
    $spToken = Get-SpToken -Scope "https://cognitiveservices.azure.com/.default"
    $r4 = Invoke-RestMethod -Method POST -Uri $chatUrl -Body $chatBody -Headers @{
        "Authorization" = "Bearer $spToken"
        "Content-Type"  = "application/json"
    }
    Write-Host "  200 OK (JWT pass-through)"
    Write-Host "  Reply : $($r4.choices[0].message.content)"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "  $code"
    Write-Host "  Note: the MI policy strips the caller JWT and uses its own token."
    Write-Host "  This is expected if the policy deletes the Authorization header."
}

# ----- Test 5: Bad model name (should 404) -----
Write-Host ""
Write-Host "Test 5 - Wrong model name (expect 404)..."

$badUrl = "$gatewayBase/openai/deployments/nonexistent-model/chat/completions?api-version=$OpenAIApiVersion"

try {
    Invoke-RestMethod -Method POST -Uri $badUrl -Body $chatBody -ContentType "application/json"
    Write-Host "  200 - unexpected, this shouldn't have worked"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "  $code (good, model doesn't exist)"
}

# -----------------------------------------------------------------------
# Curl commands — paste these into any terminal to test manually.
# The gateway uses MI for backend auth, so callers don't need an api-key.
# -----------------------------------------------------------------------
Write-Host ""
Write-Host "---------------------------------------------"
Write-Host "Curl commands you can copy-paste:"
Write-Host "---------------------------------------------"
Write-Host ""

Write-Host "# 1. Basic chat completion"
Write-Host "curl -s -X POST `"https://$ApimServiceName.azure-api.net/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion`" -H `"Content-Type: application/json`" -d '{`"messages`":[{`"role`":`"user`",`"content`":`"Hello from curl`"}],`"max_tokens`":50}'"
Write-Host ""

Write-Host "# 2. With subscription key"
Write-Host "curl -s -X POST `"https://$ApimServiceName.azure-api.net/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion`" -H `"Content-Type: application/json`" -H `"Ocp-Apim-Subscription-Key: <YOUR-KEY>`" -d '{`"messages`":[{`"role`":`"user`",`"content`":`"Hello with sub key`"}],`"max_tokens`":50}'"
Write-Host ""

Write-Host "# 3. List models"
Write-Host "curl -s `"https://$ApimServiceName.azure-api.net/openai/models?api-version=$OpenAIApiVersion`""
Write-Host ""

Write-Host "# 4. Get SP token, then call with it"
Write-Host "curl -s -X POST `"https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token`" -d `"grant_type=client_credentials&client_id=$SpClientId&client_secret=$SpClientSecret&scope=https://cognitiveservices.azure.com/.default`""
Write-Host "# copy access_token from above, then:"
Write-Host "curl -s -X POST `"https://$ApimServiceName.azure-api.net/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion`" -H `"Content-Type: application/json`" -H `"Authorization: Bearer <TOKEN>`" -d '{`"messages`":[{`"role`":`"user`",`"content`":`"Hello with JWT`"}],`"max_tokens`":50}'"
Write-Host ""

Write-Host "# 5. Bad model (should 404)"
Write-Host "curl -s -X POST `"https://$ApimServiceName.azure-api.net/openai/deployments/fake-model/chat/completions?api-version=$OpenAIApiVersion`" -H `"Content-Type: application/json`" -d '{`"messages`":[{`"role`":`"user`",`"content`":`"fail`"}],`"max_tokens`":10}'"
Write-Host ""
