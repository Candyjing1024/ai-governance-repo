# -----------------------------------------------------------------------
# 06b-Create-AIGateway-REST.ps1
#
# Same end result as 06-Create-AIGateway-SDK.ps1, but uses raw ARM
# REST calls instead of Az PowerShell modules.  This is useful if you
# don't want to install the Az modules, or you prefer to see exactly
# what's going over the wire.
#
# Auth approach:
#   - Authenticates to ARM using the Service Principal from 00-Config.ps1
#     (client_credentials grant).  No az login needed.
#   - The gateway backend uses APIM's Managed Identity to call Foundry.
#     No API keys are stored or transmitted.
#
# Existing resources used:
#   - APIM: apim-chubb-mcp-poc  (already provisioned)
#   - Foundry: foundry-test-0020  (already provisioned, gpt-4.1 deployed)
# -----------------------------------------------------------------------

. "$PSScriptRoot\00-Config.ps1"

Write-Host "`nSetting up AI Gateway (REST approach)..."
Write-Host "APIM   : $ApimServiceName"
Write-Host "Foundry: $FoundryAccountName"
Write-Host ""

# -- Helper: get an ARM token using the SP credentials --
function Get-ArmTokenRest {
    $body = @{
        grant_type    = "client_credentials"
        client_id     = $SpClientId
        client_secret = $SpClientSecret
        scope         = "https://management.azure.com/.default"
    }
    $resp = Invoke-RestMethod -Method POST `
        -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" `
        -Body $body -ContentType "application/x-www-form-urlencoded"
    return $resp.access_token
}

function Invoke-Arm {
    param([string]$Method, [string]$Uri, [object]$Body = $null)

    $headers = @{
        "Authorization" = "Bearer $(Get-ArmTokenRest)"
        "Content-Type"  = "application/json"
    }
    $params = @{ Method = $Method; Uri = $Uri; Headers = $headers }
    if ($Body) { $params.Body = ($Body | ConvertTo-Json -Depth 20) }
    return Invoke-RestMethod @params
}

$armBase   = "https://management.azure.com"
$apimId    = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.ApiManagement/service/$ApimServiceName"
$foundryId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$FoundryAccountName"

# -- Step 1: Enable managed identity on APIM --
Write-Host "Checking managed identity on APIM..."

$apimUrl = "$armBase$apimId`?api-version=2024-05-01"
$apim = Invoke-Arm -Method GET -Uri $apimUrl

if ($apim.identity -and $apim.identity.type -match "SystemAssigned") {
    Write-Host "  Already enabled (principal: $($apim.identity.principalId))"
} else {
    Write-Host "  Enabling system-assigned MI..."
    Invoke-Arm -Method PATCH -Uri $apimUrl -Body @{ identity = @{ type = "SystemAssigned" } } | Out-Null
    # Give AAD a moment to propagate
    Write-Host "  Waiting 30s for AAD propagation..."
    Start-Sleep -Seconds 30
    $apim = Invoke-Arm -Method GET -Uri $apimUrl
    Write-Host "  Done (principal: $($apim.identity.principalId))"
}

$miPrincipalId = $apim.identity.principalId

# -- Step 2: Assign "Cognitive Services OpenAI User" to the MI --
Write-Host "Assigning RBAC role on Foundry resource..."

$roleDefId = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"
$roleGuid  = [guid]::NewGuid().ToString()
$roleUrl   = "$armBase$foundryId/providers/Microsoft.Authorization/roleAssignments/$roleGuid`?api-version=2022-04-01"

$roleBody = @{
    properties = @{
        roleDefinitionId = "$foundryId/providers/Microsoft.Authorization/roleDefinitions/$roleDefId"
        principalId      = $miPrincipalId
        principalType    = "ServicePrincipal"
    }
}

try {
    Invoke-Arm -Method PUT -Uri $roleUrl -Body $roleBody | Out-Null
    Write-Host "  Assigned Cognitive Services OpenAI User"
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "  Role already assigned, skipping"
    } else {
        Write-Host "  Warning: $($_.Exception.Message)"
        Write-Host "  You might need to assign this role in the portal manually"
    }
}

# -- Step 3: Create the API --
Write-Host "Creating AI Gateway API in APIM..."

$apiUrl  = "$armBase$apimId/apis/azure-ai-gateway?api-version=2024-05-01"
$apiBody = @{
    properties = @{
        displayName          = "Azure AI Gateway"
        description          = "Routes requests to Foundry ($FoundryAccountName) using Managed Identity"
        path                 = "openai"
        protocols            = @("https")
        serviceUrl           = "$FoundryEndpoint/openai"
        subscriptionRequired = $false
        apiType              = "http"
    }
}

Invoke-Arm -Method PUT -Uri $apiUrl -Body $apiBody | Out-Null
Write-Host "  Created at path /openai"

# -- Step 4: Add operations --
Write-Host "Adding API operations..."

$operations = @(
    @{ id = "chat-completions"; name = "Chat Completions"; method = "POST"; template = "/deployments/{deployment-id}/chat/completions" },
    @{ id = "completions";      name = "Completions";      method = "POST"; template = "/deployments/{deployment-id}/completions" },
    @{ id = "embeddings";       name = "Embeddings";       method = "POST"; template = "/deployments/{deployment-id}/embeddings" },
    @{ id = "list-models";      name = "List Models";      method = "GET";  template = "/models" }
)

foreach ($op in $operations) {
    $opUrl  = "$armBase$apimId/apis/azure-ai-gateway/operations/$($op.id)?api-version=2024-05-01"
    $opBody = @{
        properties = @{
            displayName        = $op.name
            method             = $op.method
            urlTemplate        = $op.template
            templateParameters = @()
        }
    }
    Invoke-Arm -Method PUT -Uri $opUrl -Body $opBody | Out-Null
    Write-Host "  Added: $($op.name)"
}

# -- Step 5: Apply MI auth policy --
# This strips any api-key the caller sends and replaces it with an
# MI-issued token.  No keys stored in APIM config at all.
Write-Host "Applying managed identity policy..."

$policyUrl  = "$armBase$apimId/apis/azure-ai-gateway/policies/policy?api-version=2024-05-01"
$policyBody = @{
    properties = @{
        format = "xml"
        value  = @"
<policies>
    <inbound>
        <base />
        <set-header name="api-key" exists-action="delete" />
        <authentication-managed-identity resource="https://cognitiveservices.azure.com" />
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
    }
}

Invoke-Arm -Method PUT -Uri $policyUrl -Body $policyBody | Out-Null
Write-Host "  Policy applied"

# Done
Write-Host ""
Write-Host "Gateway is ready. Try it:"
Write-Host "  https://$ApimServiceName.azure-api.net/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion"
Write-Host ""
Write-Host "Backend auth is Managed Identity only - no API keys stored anywhere."
Write-Host "Run 07-Test-AIGateway.ps1 next to verify end to end."
Write-Host ""
