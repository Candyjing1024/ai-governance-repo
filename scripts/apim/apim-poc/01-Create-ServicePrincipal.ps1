# ============================================================
# Step 1 : Create a Service Principal  (one-time bootstrap)
# ============================================================
# WHY THIS EXISTS
#   Every other script in this POC authenticates as a Service
#   Principal (SP).  Somebody has to create that SP first.
#   This script does it entirely through REST API calls -
#   no Azure CLI, no Az PowerShell module.
#
# HOW IT WORKS
#   1. An Azure AD admin authenticates once via Device Code
#      flow (browser sign-in, takes ~15 seconds).
#   2. The script uses that admin token to call Microsoft Graph
#      and create an App Registration + SP + client secret.
#   3. It then exchanges the refresh token for an ARM token
#      and assigns the two RBAC roles the SP needs.
#   4. Outputs the SP credentials - copy them into 00-Config.ps1.
#
# AFTER RUNNING THIS SCRIPT
#   Update 00-Config.ps1 with the Tenant ID, SP Client ID,
#   and SP Client Secret printed at the end.
# ============================================================

. "$PSScriptRoot\00-Config.ps1"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host "  STEP 1 - Create Service Principal (one-time bootstrap)" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

# -------------------------------------------------------
# 1. Device-code authentication  (admin signs in once)
# -------------------------------------------------------
# We use the well-known Azure PowerShell first-party client.
# It can request tokens for both Graph and ARM.
$publicClientId = "1950a258-227b-4e31-a9cf-717495945fc2"

Write-Host "[1/7] Starting device-code sign-in..." -ForegroundColor Cyan
Write-Host "      An Azure AD admin who can create App Registrations" -ForegroundColor Gray
Write-Host "      and assign RBAC roles needs to complete this." -ForegroundColor Gray
Write-Host ""

$dcBody = @{
    client_id = $publicClientId
    scope     = "https://graph.microsoft.com/.default offline_access"
}

$dcResponse = Invoke-RestMethod -Method POST `
    -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/devicecode" `
    -Body $dcBody `
    -ContentType "application/x-www-form-urlencoded"

Write-Host "  Open your browser to:  $($dcResponse.verification_uri)" -ForegroundColor Green
Write-Host "  Enter this code:       $($dcResponse.user_code)"         -ForegroundColor Green
Write-Host ""
Write-Host "  Waiting for sign-in..." -ForegroundColor Gray

# Poll until the admin finishes signing in
$graphToken   = $null
$refreshToken = $null
$elapsed      = 0

while ($elapsed -lt $dcResponse.expires_in) {
    Start-Sleep -Seconds $dcResponse.interval
    $elapsed += $dcResponse.interval

    try {
        $tokenBody = @{
            grant_type  = "urn:ietf:params:oauth:grant-type:device_code"
            client_id   = $publicClientId
            device_code = $dcResponse.device_code
        }
        $tr = Invoke-RestMethod -Method POST `
            -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" `
            -Body $tokenBody `
            -ContentType "application/x-www-form-urlencoded"

        $graphToken   = $tr.access_token
        $refreshToken = $tr.refresh_token
        Write-Host "  Signed in successfully." -ForegroundColor Green
        break
    }
    catch {
        $errPayload = $null
        try { $errPayload = $_.ErrorDetails.Message | ConvertFrom-Json } catch {}
        if ($errPayload.error -eq "authorization_pending") { continue }
        if ($errPayload.error -eq "expired_token") {
            Write-Host "  Code expired. Run the script again." -ForegroundColor Red
            exit 1
        }
        # Transient error - keep trying
        continue
    }
}

if (-not $graphToken) {
    Write-Host "  Could not get admin token. Exiting." -ForegroundColor Red
    exit 1
}

$graphHeaders = @{
    "Authorization" = "Bearer $graphToken"
    "Content-Type"  = "application/json"
}

# -------------------------------------------------------
# 2. Exchange refresh token for an ARM token
# -------------------------------------------------------
Write-Host ""
Write-Host "[2/7] Exchanging refresh token for ARM token..." -ForegroundColor Cyan

$armTokenBody = @{
    grant_type    = "refresh_token"
    client_id     = $publicClientId
    refresh_token = $refreshToken
    scope         = "https://management.azure.com/.default"
}

$armTr = Invoke-RestMethod -Method POST `
    -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" `
    -Body $armTokenBody `
    -ContentType "application/x-www-form-urlencoded"

$armAdminToken = $armTr.access_token
Write-Host "  ARM token acquired." -ForegroundColor Green

$armAdminHeaders = @{
    "Authorization" = "Bearer $armAdminToken"
    "Content-Type"  = "application/json"
}

# -------------------------------------------------------
# 3. Create the App Registration  (Microsoft Graph)
# -------------------------------------------------------
Write-Host ""
Write-Host "[3/7] Creating App Registration: sp-chubb-apim-poc ..." -ForegroundColor Cyan

$appBody = @{
    displayName    = "sp-chubb-apim-poc"
    signInAudience = "AzureADMyOrg"
} | ConvertTo-Json

try {
    $app = Invoke-RestMethod -Method POST `
        -Uri "https://graph.microsoft.com/v1.0/applications" `
        -Headers $graphHeaders `
        -Body $appBody

    $appObjectId = $app.id
    $appClientId = $app.appId
    Write-Host "  Created.  Client ID : $appClientId" -ForegroundColor Green
    Write-Host "            Object ID : $appObjectId"
}
catch {
    Write-Host "  Failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# -------------------------------------------------------
# 4. Add a client secret  (valid 12 months)
# -------------------------------------------------------
Write-Host ""
Write-Host "[4/7] Generating client secret (12-month expiry)..." -ForegroundColor Cyan

$secretBody = @{
    passwordCredential = @{
        displayName = "apim-poc-key"
        endDateTime = (Get-Date).AddMonths(12).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
} | ConvertTo-Json -Depth 3

$secret = Invoke-RestMethod -Method POST `
    -Uri "https://graph.microsoft.com/v1.0/applications/$appObjectId/addPassword" `
    -Headers $graphHeaders `
    -Body $secretBody

$clientSecretValue = $secret.secretText
Write-Host "  Secret created." -ForegroundColor Green
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Yellow
Write-Host "  CLIENT SECRET (copy now, shown only once):" -ForegroundColor Yellow
Write-Host "  $clientSecretValue" -ForegroundColor Yellow
Write-Host "  ============================================" -ForegroundColor Yellow

# -------------------------------------------------------
# 5. Create the Service Principal (Enterprise Application)
# -------------------------------------------------------
Write-Host ""
Write-Host "[5/7] Creating Service Principal object..." -ForegroundColor Cyan

$spBody = @{ appId = $appClientId } | ConvertTo-Json

$sp = Invoke-RestMethod -Method POST `
    -Uri "https://graph.microsoft.com/v1.0/servicePrincipals" `
    -Headers $graphHeaders `
    -Body $spBody

$spObjectId = $sp.id
Write-Host "  Created.  SP Object ID: $spObjectId" -ForegroundColor Green

# -------------------------------------------------------
# 6. Assign RBAC roles via ARM
# -------------------------------------------------------
Write-Host ""
Write-Host "[6/7] Assigning RBAC roles..." -ForegroundColor Cyan

# Built-in role definition IDs
$roles = @(
    @{
        Name  = "Contributor"
        Id    = "b24988ac-6180-42a0-ab88-20f7382dd24c"
        Scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup"
    },
    @{
        Name  = "Cognitive Services OpenAI User"
        Id    = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"
        Scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$FoundryAccountName"
    }
)

foreach ($role in $roles) {
    $assignId  = [guid]::NewGuid().ToString()
    $assignUrl = "$ArmBase$($role.Scope)/providers/Microsoft.Authorization/roleAssignments/${assignId}?api-version=2022-04-01"

    $assignBody = @{
        properties = @{
            roleDefinitionId = "$($role.Scope)/providers/Microsoft.Authorization/roleDefinitions/$($role.Id)"
            principalId      = $spObjectId
            principalType    = "ServicePrincipal"
        }
    } | ConvertTo-Json -Depth 4

    try {
        Invoke-RestMethod -Method PUT -Uri $assignUrl -Headers $armAdminHeaders -Body $assignBody | Out-Null
        Write-Host "  + $($role.Name) on $($role.Scope.Split('/')[-1])" -ForegroundColor Green
    }
    catch {
        $errBody = $null
        try { $errBody = $_.ErrorDetails.Message | ConvertFrom-Json } catch {}
        if ($errBody.error.code -eq "RoleAssignmentExists") {
            Write-Host "  ~ $($role.Name) already assigned (skipped)" -ForegroundColor Gray
        }
        else {
            Write-Host "  ! $($role.Name) failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# -------------------------------------------------------
# 7. Summary
# -------------------------------------------------------
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Green
Write-Host "  SERVICE PRINCIPAL READY" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Copy these into 00-Config.ps1 :" -ForegroundColor White
Write-Host ""
Write-Host "    `$TenantId       = `"$TenantId`""
Write-Host "    `$SpClientId     = `"$appClientId`""
Write-Host "    `$SpClientSecret = `"$clientSecretValue`""
Write-Host ""
Write-Host "  Roles assigned:" -ForegroundColor Cyan
Write-Host "    Contributor                     -> $ResourceGroup"
Write-Host "    Cognitive Services OpenAI User  -> $FoundryAccountName"
Write-Host ""
Write-Host "  From now on, every script authenticates as this SP."
Write-Host "  No more interactive sign-in needed."
Write-Host ""
