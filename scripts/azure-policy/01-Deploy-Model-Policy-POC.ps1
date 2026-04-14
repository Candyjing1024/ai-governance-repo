<#
.SYNOPSIS
    POC: Azure Policy to Limit AI Model Deployments in Foundry.

.DESCRIPTION
    This script demonstrates how to:
    1. Find the built-in Azure Policy for Cognitive Services model deployments
    2. Assign the policy to a resource group with an approved model list
    3. Test deploying a BLOCKED model (should fail with policy violation)
    4. Test deploying an ALLOWED model (should succeed)

    Built-in policy: "Cognitive Services Deployments should only use approved Registry Models"

.NOTES
    Prerequisites:
    - Azure CLI installed and logged in
    - Owner or Resource Policy Contributor role on the target resource group
    - Wait ~15 minutes after policy assignment before testing

    Reference: https://learn.microsoft.com/en-us/azure/foundry/how-to/model-deployment-policy?tabs=cli
#>

# ============================================================
# CONFIGURATION - Update these values for your environment
# ============================================================
$SubscriptionId   = "<your-subscription-id>"
$ResourceGroup    = "<your-resource-group>"
$AccountName      = "<your-foundry-account-name>"      # CognitiveServices/AIServices account
$Location         = "eastus"
$ParamsFile       = "$PSScriptRoot\policy-params.json"

# Policy assignment name
$PolicyAssignmentName = "limit-foundry-model-deployments"
$PolicyDisplayName    = "Limit Foundry Model Deployments - POC"

# Models for testing — must match validated results:
#   Allowed: gpt-4.1 (in allowedAssetIds) -> HTTP 201
#   Blocked: gpt-4o  (NOT in allowedAssetIds) -> HTTP 400 NonCompliant
$AllowedModel        = "gpt-4.1"
$AllowedModelVersion = "2025-04-14"
$BlockedModel        = "gpt-4o"
$BlockedModelVersion = "2024-11-20"

# ============================================================
# STEP 0: Login and set subscription
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "STEP 0: Verify Azure CLI login" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan

az account show --output none 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Logging in..."
    az login
}
az account set --subscription $SubscriptionId
$acctInfo = az account show --query "{name:name, id:id}" --output json | ConvertFrom-Json
Write-Host "  Subscription: $($acctInfo.name) ($($acctInfo.id))"

# ============================================================
# STEP 1: Find the built-in policy definition
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "STEP 1: Find built-in policy definition" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan

$policyDef = az policy definition list `
    --query "[?displayName=='Cognitive Services Deployments should only use approved Registry Models'].{name:name, id:id, displayName:displayName}" `
    --output json | ConvertFrom-Json

if (-not $policyDef -or $policyDef.Count -eq 0) {
    Write-Host "  ERROR: Built-in policy not found!" -ForegroundColor Red
    Write-Host "  Check if the policy exists in your tenant with:"
    Write-Host '    az policy definition list --query "[?contains(displayName, ''Registry Models'')]"'
    exit 1
}

$policyDefId = $policyDef[0].id
$policyDefName = $policyDef[0].name
Write-Host "  Found: $($policyDef[0].displayName)"
Write-Host "  Definition ID: $policyDefId"
Write-Host "  Name: $policyDefName"

# Show policy parameters for reference
Write-Host "`n  Policy definition parameters:"
az policy definition show --name $policyDefName --query "parameters" --output json

# ============================================================
# STEP 2: Verify parameters file
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "STEP 2: Verify policy parameters" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan

if (-not (Test-Path $ParamsFile)) {
    Write-Host "  ERROR: Parameters file not found: $ParamsFile" -ForegroundColor Red
    exit 1
}

$params = Get-Content $ParamsFile -Raw | ConvertFrom-Json
Write-Host "  Effect: $($params.effect.value)"
Write-Host "  Allowed Publishers: $($params.allowedPublishers.value -join ', ')"
Write-Host "  Allowed Asset IDs:"
foreach ($assetId in $params.allowedAssetIds.value) {
    Write-Host "    - $assetId"
}

# ============================================================
# STEP 3: Assign the policy to the resource group
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "STEP 3: Assign policy to resource group" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan

$rgScope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup"
Write-Host "  Scope: $rgScope"

# Check if assignment already exists
$existing = az policy assignment show `
    --name $PolicyAssignmentName `
    --scope $rgScope `
    --output json 2>$null | ConvertFrom-Json

if ($existing) {
    Write-Host "  Policy assignment already exists. Updating..." -ForegroundColor Yellow
    az policy assignment delete --name $PolicyAssignmentName --scope $rgScope
}

Write-Host "  Creating policy assignment..."
$assignment = az policy assignment create `
    --name $PolicyAssignmentName `
    --display-name $PolicyDisplayName `
    --scope $rgScope `
    --policy $policyDefId `
    --params $ParamsFile `
    --output json | ConvertFrom-Json

if ($LASTEXITCODE -eq 0) {
    Write-Host "  SUCCESS: Policy assigned" -ForegroundColor Green
    Write-Host "  Assignment ID: $($assignment.id)"
    Write-Host "  Enforcement: $($assignment.enforcementMode)"
} else {
    Write-Host "  ERROR: Policy assignment failed!" -ForegroundColor Red
    exit 1
}

# ============================================================
# STEP 4: Wait for policy propagation
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "STEP 4: Policy propagation" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan
Write-Host "  Azure Policy can take up to 15 minutes to propagate."
Write-Host "  The script will now test deployments."
Write-Host "  If tests pass unexpectedly, wait and re-run Steps 5-6."
Write-Host ""
Write-Host "  Press ENTER to continue with deployment tests..." -ForegroundColor Yellow
Read-Host

# ============================================================
# STEP 5: Test BLOCKED model deployment (should FAIL)
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "STEP 5: Test BLOCKED model deployment ($BlockedModel)" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan

$deploymentName = "test-blocked-$BlockedModel"
$accountRid = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$AccountName"

Write-Host "  Attempting to deploy: $BlockedModel (version $BlockedModelVersion)"
Write-Host "  Expected: DENIED by policy`n"

$blockedBody = @{
    sku = @{
        name = "GlobalStandard"
        capacity = 1
    }
    properties = @{
        model = @{
            format = "OpenAI"
            name = $BlockedModel
            version = $BlockedModelVersion
        }
    }
} | ConvertTo-Json -Depth 5

$blockedBodyFile = "$env:TEMP\blocked-deploy.json"
$blockedBody | Out-File -FilePath $blockedBodyFile -Encoding utf8

$result = az rest --method PUT `
    --url "https://management.azure.com${accountRid}/deployments/${deploymentName}?api-version=2024-10-01" `
    --body "@$blockedBodyFile" `
    --output json 2>&1

if ($result -match "NonCompliant" -or $result -match "RequestDisallowedByPolicy" -or $result -match "PolicyViolation" -or $result -match "disallowed by policy") {
    Write-Host "  PASS: Deployment correctly BLOCKED by policy!" -ForegroundColor Green
    Write-Host "  Policy violation detected as expected."
} elseif ($LASTEXITCODE -ne 0) {
    Write-Host "  Result: Deployment failed (may be policy or other error)" -ForegroundColor Yellow
    Write-Host "  Response: $($result | Select-Object -First 5)"
} else {
    Write-Host "  WARNING: Deployment was NOT blocked!" -ForegroundColor Red
    Write-Host "  Policy may not have propagated yet. Wait 15 minutes and retry."
    # Clean up if it was created
    Write-Host "  Cleaning up test deployment..."
    az rest --method DELETE `
        --url "https://management.azure.com${accountRid}/deployments/${deploymentName}?api-version=2024-10-01" `
        --output none 2>$null
}

Remove-Item $blockedBodyFile -ErrorAction SilentlyContinue

# ============================================================
# STEP 6: Test ALLOWED model deployment (should SUCCEED)
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "STEP 6: Test ALLOWED model deployment ($AllowedModel)" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan

$allowedDeployName = "test-allowed-$AllowedModel"

Write-Host "  Attempting to deploy: $AllowedModel (version $AllowedModelVersion)"
Write-Host "  Expected: ALLOWED by policy`n"

$allowedBody = @{
    sku = @{
        name = "GlobalStandard"
        capacity = 1
    }
    properties = @{
        model = @{
            format = "OpenAI"
            name = $AllowedModel
            version = $AllowedModelVersion
        }
    }
} | ConvertTo-Json -Depth 5

$allowedBodyFile = "$env:TEMP\allowed-deploy.json"
$allowedBody | Out-File -FilePath $allowedBodyFile -Encoding utf8

$result = az rest --method PUT `
    --url "https://management.azure.com${accountRid}/deployments/${allowedDeployName}?api-version=2024-10-01" `
    --body "@$allowedBodyFile" `
    --output json 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  PASS: Allowed model deployed successfully!" -ForegroundColor Green
    # Clean up
    Write-Host "  Cleaning up test deployment..."
    az rest --method DELETE `
        --url "https://management.azure.com${accountRid}/deployments/${allowedDeployName}?api-version=2024-10-01" `
        --output none 2>$null
} elseif ($result -match "RequestDisallowedByPolicy") {
    Write-Host "  FAIL: Allowed model was blocked by policy!" -ForegroundColor Red
    Write-Host "  Check that the allowedAssetIds includes this model version."
} else {
    Write-Host "  Result: HTTP error (may be quota or region issue)" -ForegroundColor Yellow
    Write-Host "  Response: $($result | Select-Object -First 5)"
}

Remove-Item $allowedBodyFile -ErrorAction SilentlyContinue

# ============================================================
# STEP 7: Check compliance status
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "STEP 7: Check policy compliance" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan

Write-Host "  Note: Compliance evaluation can take up to 24 hours."
$compliance = az policy assignment show `
    --name $PolicyAssignmentName `
    --scope $rgScope `
    --query "{name:name, displayName:displayName, enforcementMode:enforcementMode, scope:scope}" `
    --output json | ConvertFrom-Json

Write-Host "  Assignment: $($compliance.displayName)"
Write-Host "  Enforcement: $($compliance.enforcementMode)"
Write-Host "  Scope: $($compliance.scope)"

# Trigger on-demand compliance evaluation
Write-Host "`n  Triggering on-demand compliance scan..."
az policy state trigger-scan --resource-group $ResourceGroup --no-wait 2>$null
Write-Host "  Compliance scan triggered (runs async in background)."

# ============================================================
# SUMMARY
# ============================================================
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "POC SUMMARY" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan
Write-Host "  Policy:       Cognitive Services Deployments - Approved Registry Models"
Write-Host "  Assignment:   $PolicyAssignmentName"
Write-Host "  Scope:        $ResourceGroup (resource group)"
Write-Host "  Effect:       Deny"
Write-Host "  Allowed:      $($params.allowedPublishers.value -join ', ') publisher(s)"
Write-Host "  Asset IDs:    $($params.allowedAssetIds.value.Count) model(s) approved"
Write-Host ""
Write-Host "  To remove the policy assignment:" -ForegroundColor Yellow
Write-Host "    az policy assignment delete --name $PolicyAssignmentName --scope `"$rgScope`""
Write-Host ""
