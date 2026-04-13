# -----------------------------------------------------------------------
# 06-Create-AIGateway-SDK.ps1
#
# Links the existing APIM (apim-chubb-mcp-poc) to the existing Foundry
# resource (foundry-test-0020) as an AI Gateway.
#
# Auth approach:
#   - This script authenticates to ARM using the Service Principal
#     from 00-Config.ps1 (no az login needed).
#   - The gateway itself uses APIM's System-Assigned Managed Identity
#     to call Foundry. No API keys are stored or passed at any point.
#
# What it does:
#   1. Logs in via Service Principal (Connect-AzAccount)
#   2. Makes sure APIM has a system-assigned managed identity
#   3. Gives that identity the "Cognitive Services OpenAI User" role
#      on the Foundry resource
#   4. Creates an API in APIM that fronts the Foundry OpenAI endpoint
#   5. Sets up 4 operations (chat, completions, embeddings, list models)
#   6. Applies a policy that swaps in the MI token on every request
#
# Prerequisites:
#   - APIM "apim-chubb-mcp-poc" already exists
#   - Foundry "foundry-test-0020" already exists with gpt-4.1 deployed
#   - The SP in 00-Config.ps1 has Contributor on the resource group
#   - Az.ApiManagement module (script will install if missing)
# -----------------------------------------------------------------------

. "$PSScriptRoot\00-Config.ps1"

Write-Host "`nSetting up AI Gateway (SDK approach)..."
Write-Host "APIM  : $ApimServiceName"
Write-Host "Foundry: $FoundryAccountName"
Write-Host ""

# --- Step 1: Sign in with the Service Principal ---
Write-Host "Logging in with Service Principal..."

$secureSecret = ConvertTo-SecureString $SpClientSecret -AsPlainText -Force
$credential   = New-Object System.Management.Automation.PSCredential($SpClientId, $secureSecret)

Connect-AzAccount -ServicePrincipal -Credential $credential -Tenant $TenantId -Subscription $SubscriptionId | Out-Null
Write-Host "Logged in as SP $SpClientId"

# --- Step 2: Make sure the Az.ApiManagement module is available ---
if (-not (Get-Module -ListAvailable -Name Az.ApiManagement)) {
    Write-Host "Installing Az.ApiManagement module (one-time)..."
    Install-Module -Name Az.ApiManagement -Force -Scope CurrentUser -AllowClobber
}
Import-Module Az.ApiManagement

$apimContext = New-AzApiManagementContext -ResourceGroupName $ResourceGroup -ServiceName $ApimServiceName

# --- Step 3: Enable system-assigned managed identity on APIM ---
Write-Host "Checking managed identity on APIM..."

$apim = Get-AzApiManagement -ResourceGroupName $ResourceGroup -Name $ApimServiceName

if ($apim.Identity -and $apim.Identity.Type -match "SystemAssigned") {
    Write-Host "  Already enabled (principal: $($apim.Identity.PrincipalId))"
} else {
    Write-Host "  Enabling system-assigned MI..."
    Set-AzApiManagement -InputObject $apim -SystemAssignedIdentity
    $apim = Get-AzApiManagement -ResourceGroupName $ResourceGroup -Name $ApimServiceName
    Write-Host "  Done (principal: $($apim.Identity.PrincipalId))"
}

$miPrincipalId = $apim.Identity.PrincipalId

# --- Step 4: Grant "Cognitive Services OpenAI User" to the MI ---
Write-Host "Assigning RBAC role on Foundry resource..."

$foundryResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$FoundryAccountName"

# Role GUID for "Cognitive Services OpenAI User"
$roleDefId = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"

$existing = Get-AzRoleAssignment -ObjectId $miPrincipalId -RoleDefinitionId $roleDefId `
                -Scope $foundryResourceId -ErrorAction SilentlyContinue

if ($existing) {
    Write-Host "  Role already assigned, skipping"
} else {
    New-AzRoleAssignment -ObjectId $miPrincipalId -RoleDefinitionId $roleDefId -Scope $foundryResourceId | Out-Null
    Write-Host "  Assigned Cognitive Services OpenAI User to APIM MI"
}

# --- Step 5: Create the API in APIM ---
Write-Host "Creating AI Gateway API..."

$apiId   = "azure-ai-gateway"
$apiPath = "openai"

# Clean up if it already exists from a previous run
try { Remove-AzApiManagementApi -Context $apimContext -ApiId $apiId -ErrorAction SilentlyContinue } catch {}

New-AzApiManagementApi `
    -Context $apimContext `
    -ApiId $apiId `
    -Name "Azure AI Gateway" `
    -Description "Routes requests to Foundry ($FoundryAccountName) using Managed Identity" `
    -ServiceUrl "$FoundryEndpoint/openai" `
    -Path $apiPath `
    -Protocols @("https") `
    -SubscriptionRequired $false | Out-Null

Write-Host "  Created API at path /$apiPath"

# Add operations — these match the OpenAI REST spec
$ops = @(
    @{ Id = "chat-completions"; Name = "Chat Completions"; Method = "POST"; Url = "/deployments/{deployment-id}/chat/completions?api-version={api-version}" },
    @{ Id = "completions";      Name = "Completions";      Method = "POST"; Url = "/deployments/{deployment-id}/completions?api-version={api-version}" },
    @{ Id = "embeddings";       Name = "Embeddings";       Method = "POST"; Url = "/deployments/{deployment-id}/embeddings?api-version={api-version}" },
    @{ Id = "list-models";      Name = "List Models";      Method = "GET";  Url = "/models?api-version={api-version}" }
)

foreach ($op in $ops) {
    New-AzApiManagementApiOperation -Context $apimContext -ApiId $apiId `
        -OperationId $op.Id -Name $op.Name -Method $op.Method -UrlTemplate $op.Url | Out-Null
    Write-Host "  Added: $($op.Name)"
}

# --- Step 6: Apply the MI auth policy ---
# This is the key part — every inbound request gets its api-key header
# stripped, and APIM injects its own managed-identity token instead.
# No secrets stored anywhere.
Write-Host "Applying managed identity policy..."

$policy = @"
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

Set-AzApiManagementPolicy -Context $apimContext -ApiId $apiId -Policy $policy
Write-Host "  Policy applied — MI auth on every request"

# Done
Write-Host ""
Write-Host "Gateway is ready. Try it:"
Write-Host "  https://$ApimServiceName.azure-api.net/openai/deployments/$ModelDeploymentName/chat/completions?api-version=$OpenAIApiVersion"
Write-Host ""
Write-Host "Backend auth is Managed Identity only — no API keys stored anywhere."
Write-Host "Run 07-Test-AIGateway.ps1 next to verify it end-to-end."
Write-Host ""
