# ============================================================
# APIM + Azure AI Foundry POC - Shared Configuration
# ============================================================
# Update these values for your environment BEFORE running any
# of the other scripts. Every script dot-sources this file.
# ============================================================

# --- Azure Tenant & Subscription ---
$TenantId           = "<your-tenant-id>"    # Azure AD Tenant ID
$SubscriptionId     = "<your-subscription-id>"    # Azure Subscription
$ResourceGroup      = "<your-resource-group>"                        # Resource Group
$Location           = "<location>"                                    # Region (e.g., eastus)

# --- Service Principal credentials (fill in after running Step 01) ---
$SpClientId          = "<service-principal-client-id>"
$SpClientSecret      = "<service-principal-client-secret>"  # Keep this secret! Use Key Vault in production

# --- APIM ---
$ApimServiceName     = "<apim-service-name>"          # Must be globally unique across all Azure
$ApimPublisherEmail  = "admin@yourdomain.com"         # Shows up in the APIM developer portal
$ApimPublisherName   = "AI Governance Team"
$ApimSku             = "Consumption"                   # Consumption tier, first 1M calls/month FREE

# --- Azure AI Foundry / OpenAI ---
# The CognitiveServices (AIServices) account that hosts gpt-4o.
# If your endpoint uses .cognitiveservices.azure.com instead of
# .openai.azure.com, update the URL below accordingly.
$FoundryAccountName  = "<foundry-account-name>"
$FoundryEndpoint     = "https://<foundry-account-name>.openai.azure.com"
$ModelDeploymentName = "gpt-4.1"
$OpenAIApiVersion    = "2024-12-01-preview"

# --- Key Vault (reference only) ---
$KeyVaultName        = "kv-chubb-mcp-9342"

# --- API versions for REST calls ---
$ApimApiVersion      = "2024-05-01"

# ============================================================
# Helper Functions - used by all scripts
# ============================================================

function Get-SpToken {
    <#
    .SYNOPSIS
        Gets an OAuth2 access token using the Service Principal's client credentials.
    .PARAMETER Scope
        The OAuth scope to request. Defaults to ARM management plane.
    #>
    param(
        [string]$Scope = "https://management.azure.com/.default"
    )

    $body = @{
        grant_type    = "client_credentials"
        client_id     = $SpClientId
        client_secret = $SpClientSecret
        scope         = $Scope
    }

    $uri = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"

    try {
        $response = Invoke-RestMethod -Method POST -Uri $uri -Body $body -ContentType "application/x-www-form-urlencoded"
        return $response.access_token
    }
    catch {
        Write-Host "  ERROR getting token for scope $Scope" -ForegroundColor Red
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

function Get-ArmHeaders {
    <#
    .SYNOPSIS
        Returns headers dictionary with a fresh ARM Bearer token.
    #>
    $token = Get-SpToken -Scope "https://management.azure.com/.default"
    return @{
        "Authorization" = "Bearer $token"
        "Content-Type"  = "application/json"
    }
}

function Wait-ArmOperation {
    <#
    .SYNOPSIS
        Polls an ARM resource until provisioningState is terminal.
    #>
    param(
        [string]$ResourceUrl,
        [int]$IntervalSeconds = 30,
        [int]$TimeoutMinutes  = 60
    )

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)

    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds $IntervalSeconds
        $headers = Get-ArmHeaders
        try {
            $res = Invoke-RestMethod -Method GET -Uri $ResourceUrl -Headers $headers
            $state = $res.properties.provisioningState
            Write-Host "  Provisioning state: $state  ($(Get-Date -Format 'HH:mm:ss'))" -ForegroundColor Gray

            if ($state -eq "Succeeded") { return $res }
            if ($state -eq "Failed")    {
                Write-Host "  Provisioning FAILED." -ForegroundColor Red
                return $null
            }
        }
        catch {
            Write-Host "  Poll error: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    Write-Host "  Timed out waiting for provisioning." -ForegroundColor Red
    return $null
}

# Shorthand for the ARM base URL
$ArmBase = "https://management.azure.com"

Write-Host "[Config] Loaded. Sub: $SubscriptionId | RG: $ResourceGroup | Location: $Location" -ForegroundColor DarkCyan
