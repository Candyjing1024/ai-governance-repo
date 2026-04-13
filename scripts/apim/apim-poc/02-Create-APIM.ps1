# ============================================================
# Step 2 : Provision Azure API Management (Developer tier)
# ============================================================
# WHAT THIS DOES
#   Creates an APIM instance in the Consumption SKU (serverless).
#   First 1 million calls per month are free - effectively $0
#   for a proof of concept.  No dedicated gateway, so there
#   is a cold-start on the first request (~1-2s).
#
# WAIT TIME
#   Consumption tier provisions in 1-5 minutes (much faster
#   than Developer/Basic tiers).
#
# PREREQUISITES
#   - 00-Config.ps1 has been updated with SP credentials
#   - Step 01 has been run (SP exists with Contributor role)
# ============================================================

. "$PSScriptRoot\00-Config.ps1"

$ArmBase = "https://management.azure.com"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host "  STEP 2 - Create API Management (Consumption tier)" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

# -------------------------------------------------------
# 1. Authenticate as the Service Principal
# -------------------------------------------------------
Write-Host "[1/4] Getting token via Service Principal..." -ForegroundColor Cyan
$headers = Get-ArmHeaders
Write-Host "  Token acquired." -ForegroundColor Green

# -------------------------------------------------------
# 2. Check if APIM already exists
# -------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Checking if APIM '$ApimServiceName' already exists..." -ForegroundColor Cyan

$apimUrl = "$ArmBase/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup" +
           "/providers/Microsoft.ApiManagement/service/${ApimServiceName}?api-version=$ApimApiVersion"

try {
    $existing = Invoke-RestMethod -Method GET -Uri $apimUrl -Headers $headers
    $state = $existing.properties.provisioningState

    if ($state -eq "Succeeded") {
        Write-Host "  APIM already exists and is healthy." -ForegroundColor Green
        Write-Host "  Gateway URL : $($existing.properties.gatewayUrl)" -ForegroundColor Cyan
        Write-Host "  Portal URL  : $($existing.properties.developerPortalUrl)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Skipping creation. Move on to Step 03." -ForegroundColor Gray
        exit 0
    }
    elseif ($state -eq "Activating" -or $state -eq "Creating") {
        Write-Host "  APIM exists but is still provisioning ($state)." -ForegroundColor Yellow
        Write-Host "  Will wait for it to finish..." -ForegroundColor Gray
        $result = Wait-ArmOperation -ResourceUrl $apimUrl -IntervalSeconds 30 -TimeoutMinutes 60
        if ($result) {
            Write-Host "  Gateway URL : $($result.properties.gatewayUrl)" -ForegroundColor Cyan
        }
        exit 0
    }
}
catch {
    # 404 means it doesn't exist - that's what we want
    $statusCode = $null
    try { $statusCode = $_.Exception.Response.StatusCode.value__ } catch {}
    if ($statusCode -ne 404) {
        Write-Host "  Unexpected error checking APIM: $($_.Exception.Message)" -ForegroundColor Red
    }
    else {
        Write-Host "  Does not exist yet. Will create it now." -ForegroundColor Green
    }
}

# -------------------------------------------------------
# 3. Create the APIM instance
# -------------------------------------------------------
Write-Host ""
Write-Host "[3/4] Creating APIM instance..." -ForegroundColor Cyan
Write-Host "  Name     : $ApimServiceName" -ForegroundColor Gray
Write-Host "  SKU      : $ApimSku  (first 1M calls/month free)" -ForegroundColor Gray
Write-Host "  Location : $Location" -ForegroundColor Gray
Write-Host "  Publisher: $ApimPublisherName <$ApimPublisherEmail>" -ForegroundColor Gray
Write-Host ""

$apimBody = @{
    location   = $Location
    sku        = @{
        name     = $ApimSku
        capacity = 0          # Consumption tier uses 0 capacity (serverless)
    }
    properties = @{
        publisherEmail = $ApimPublisherEmail
        publisherName  = $ApimPublisherName
    }
} | ConvertTo-Json -Depth 4

try {
    Invoke-RestMethod -Method PUT -Uri $apimUrl -Headers $headers -Body $apimBody | Out-Null
    Write-Host "  APIM creation kicked off." -ForegroundColor Green
    Write-Host "  Consumption tier usually provisions in 1-5 minutes..." -ForegroundColor Yellow
}
catch {
    Write-Host "  Failed to create APIM: $($_.Exception.Message)" -ForegroundColor Red
    try {
        $errDetail = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Host "  Details: $($errDetail.error.message)" -ForegroundColor Red
    } catch {}
    exit 1
}

# -------------------------------------------------------
# 4. Wait for provisioning to complete
# -------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Waiting for APIM provisioning to complete..." -ForegroundColor Cyan
Write-Host "  Polling every 15 seconds (timeout: 15 minutes)" -ForegroundColor Gray

$result = Wait-ArmOperation -ResourceUrl $apimUrl -IntervalSeconds 15 -TimeoutMinutes 15

if ($result) {
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor Green
    Write-Host "  APIM CREATED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "=========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Service Name  : $ApimServiceName"
    Write-Host "  Gateway URL   : $($result.properties.gatewayUrl)"
    Write-Host "  Management URL: $($result.properties.managementApiUrl)"
    Write-Host "  Portal URL    : $($result.properties.developerPortalUrl)"
    Write-Host "  SKU           : $($result.sku.name)"
    Write-Host ""
    Write-Host "  Next step -> Run 03-Register-FoundryInAPIM.ps1"
    Write-Host ""
}
else {
    Write-Host ""
    Write-Host "  APIM provisioning did not complete in time." -ForegroundColor Red
    Write-Host "  Check the Azure Portal for status." -ForegroundColor Red
    exit 1
}
