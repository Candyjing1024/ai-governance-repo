# ALTERNATIVE: Deploy to West US 2 using App Service (if quota available there)

$RESOURCE_GROUP = "rg-chubb-mcp-poc"
$LOCATION = "westus2"  # Different region - may have quota available
$APP_SERVICE_PLAN = "asp-chubb-mcp-westus2"
$APP_SERVICE_NAME = "app-chubb-mcp-westus2-$(Get-Random -Minimum 1000 -Maximum 9999)"
$KEY_VAULT_NAME = "kv-chubb-mcp-9342"

Write-Host "`nTrying App Service deployment in West US 2 region..." -ForegroundColor Green

# Try to create App Service Plan in different region
az appservice plan create `
    --name $APP_SERVICE_PLAN `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --sku F1 `
    --is-linux

if ($LASTEXITCODE -eq 0) {
    Write-Host "App Service Plan created successfully!" -ForegroundColor Green
    
    # Create Web App
    az webapp create `
        --name $APP_SERVICE_NAME `
        --resource-group $RESOURCE_GROUP `
        --plan $APP_SERVICE_PLAN `
        --runtime "PYTHON:3.11"
    
    # Configure environment variables
    az webapp config appsettings set `
        --name $APP_SERVICE_NAME `
        --resource-group $RESOURCE_GROUP `
        --settings KEY_VAULT_NAME=$KEY_VAULT_NAME PORT=8000
    
    # Enable managed identity
    az webapp identity assign `
        --name $APP_SERVICE_NAME `
        --resource-group $RESOURCE_GROUP
    
    $IDENTITY_PRINCIPAL_ID = az webapp identity show `
        --name $APP_SERVICE_NAME `
        --resource-group $RESOURCE_GROUP `
        --query "principalId" -o tsv
    
    # Grant Key Vault access
    az keyvault set-policy `
        --name $KEY_VAULT_NAME `
        --object-id $IDENTITY_PRINCIPAL_ID `
        --secret-permissions get list
    
    # Deploy code
    Push-Location
    az webapp up `
        --name $APP_SERVICE_NAME `
        --resource-group $RESOURCE_GROUP
    Pop-Location
    
    Write-Host "`n========== DEPLOYMENT COMPLETE ==========" -ForegroundColor Green
    Write-Host "App Service URL: https://${APP_SERVICE_NAME}.azurewebsites.net" -ForegroundColor Cyan
    Write-Host "Health Check: https://${APP_SERVICE_NAME}.azurewebsites.net/health" -ForegroundColor Cyan
} else {
    Write-Host "`nQuota issue in West US 2 as well. Use Container Instances instead (deploy-container.ps1)" -ForegroundColor Red
}
