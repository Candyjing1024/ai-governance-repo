# deploy-poc.ps1 - Deploy MCP server to ACI (POC)
Write-Host "`n========== DEPLOYING POC MCP SERVER ==========" -ForegroundColor Yellow

$rg = "rg-chubb-mcp-poc"
$aciName = "aci-chubb-mcp-poc"
$acrName = "acrchubbmcp3122"
$image = "$acrName.azurecr.io/chubb-mcp-server:v2"
$location = "westus2"

# Get ACR credentials
Write-Host "Getting ACR credentials..." -ForegroundColor Cyan
$acrPass = az acr credential show --name $acrName --query "passwords[0].value" -o tsv

# Get secrets from Key Vault
Write-Host "Getting secrets from Key Vault..." -ForegroundColor Cyan
$oaiEp = az keyvault secret show --vault-name kv-chubb-mcp-9342 --name aisvc-endpoint --query value -o tsv
$oaiKey = az keyvault secret show --vault-name kv-chubb-mcp-9342 --name aisvc-key --query value -o tsv
$srchEp = az keyvault secret show --vault-name kv-chubb-mcp-9342 --name aisearch-endpoint --query value -o tsv
$srchKey = az keyvault secret show --vault-name kv-chubb-mcp-9342 --name aisearch-key --query value -o tsv

Write-Host "  OAI: $oaiEp" -ForegroundColor Gray
Write-Host "  Search: $srchEp" -ForegroundColor Gray

# Delete old containers
Write-Host "Cleaning up old containers..." -ForegroundColor Cyan
az container delete --name aci-chubb-mcp-fixed --resource-group $rg --yes 2>$null
az container delete --name $aciName --resource-group $rg --yes 2>$null

# Deploy new container with env vars (no Key Vault dependency at startup)
Write-Host "Deploying container: $aciName ..." -ForegroundColor Green
az container create `
    --resource-group $rg `
    --name $aciName `
    --image $image `
    --registry-login-server "$acrName.azurecr.io" `
    --registry-username $acrName `
    --registry-password $acrPass `
    --cpu 1 --memory 1.5 `
    --ports 8000 `
    --ip-address Public `
    --location $location `
    --environment-variables `
        AZURE_OPENAI_ENDPOINT=$oaiEp `
        AZURE_SEARCH_ENDPOINT=$srchEp `
    --secure-environment-variables `
        AZURE_OPENAI_API_KEY=$oaiKey `
        AZURE_SEARCH_KEY=$srchKey `
    --query "{fqdn:ipAddress.fqdn, ip:ipAddress.ip, state:instanceView.state, ports:ipAddress.ports}" `
    -o table

Write-Host "`nWaiting 15 seconds for container to start..." -ForegroundColor Cyan
Start-Sleep 15

# Test health endpoint
$fqdn = az container show --name $aciName --resource-group $rg --query "ipAddress.fqdn" -o tsv
Write-Host "`nTesting health endpoint: http://${fqdn}:8000/health" -ForegroundColor Yellow
try {
    $resp = Invoke-WebRequest -Uri "http://${fqdn}:8000/health" -TimeoutSec 10
    Write-Host "Health: $($resp.StatusCode) - $($resp.Content)" -ForegroundColor Green
} catch {
    Write-Host "Health check failed: $_" -ForegroundColor Red
}

Write-Host "`n========== DEPLOYMENT COMPLETE ==========" -ForegroundColor Green
Write-Host "MCP Endpoint: http://${fqdn}:8000/mcp" -ForegroundColor Cyan
