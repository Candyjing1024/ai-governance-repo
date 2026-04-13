# Fix and Redeploy Container with proper Key Vault access

$RESOURCE_GROUP = "rg-chubb-mcp-poc"
$KEY_VAULT_NAME = "kv-chubb-mcp-9342"
$CONTAINER_NAME = "aci-chubb-mcp-fixed"
$IDENTITY_NAME = "id-mcp-fixed"
$ACR_NAME = "acrchubbmcp3122"  # Use existing ACR
$IMAGE_NAME = "chubb-mcp-server"

Write-Host "`n========== FIXING CONTAINER DEPLOYMENT ==========" -ForegroundColor Yellow

# Step 1: Create new managed identity
Write-Host "`n[1/4] Creating Managed Identity..." -ForegroundColor Green
az identity create --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --location westus2

$IDENTITY_ID = az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --query "id" -o tsv
$IDENTITY_PRINCIPAL_ID = az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --query "principalId" -o tsv

Write-Host "Identity Principal ID: $IDENTITY_PRINCIPAL_ID" -ForegroundColor Cyan

# Step 2: Grant Key Vault access
Write-Host "`n[2/4] Granting Key Vault access..." -ForegroundColor Green
Start-Sleep -Seconds 15  # Wait for identity to propagate

az keyvault set-policy `
    --name $KEY_VAULT_NAME `
    --object-id $IDENTITY_PRINCIPAL_ID `
    --secret-permissions get list

# Step 3: Get ACR credentials
Write-Host "`n[3/4] Getting ACR credentials..." -ForegroundColor Green
$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --query "loginServer" -o tsv
$ACR_USERNAME = az acr credential show --name $ACR_NAME --query "username" -o tsv
$ACR_PASSWORD = az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv

# Step 4: Deploy container
Write-Host "`n[4/4] Deploying Container Instance..." -ForegroundColor Green
az container create `
    --resource-group $RESOURCE_GROUP `
    --name $CONTAINER_NAME `
    --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest" `
    --cpu 1 `
    --memory 1.5 `
    --registry-login-server $ACR_LOGIN_SERVER `
    --registry-username $ACR_USERNAME `
    --registry-password $ACR_PASSWORD `
    --dns-name-label $CONTAINER_NAME `
    --ports 8000 `
    --environment-variables `
        KEY_VAULT_NAME=$KEY_VAULT_NAME `
        AZURE_OPENAI_API_VERSION=2024-12-01-preview `
        EMBEDDING_VECTOR_DIMENSION=1536 `
    --assign-identity $IDENTITY_ID `
    --location westus2

# Get endpoint
$CONTAINER_FQDN = az container show --name $CONTAINER_NAME --resource-group $RESOURCE_GROUP --query "ipAddress.fqdn" -o tsv

Write-Host "`n========== DEPLOYMENT COMPLETE ==========" -ForegroundColor Green
Write-Host "MCP Server: http://${CONTAINER_FQDN}:8000/sse" -ForegroundColor Cyan
Write-Host "Health Check: http://${CONTAINER_FQDN}:8000/health" -ForegroundColor Cyan
Write-Host "`nWait 30 seconds for container to start, then test with:" -ForegroundColor Yellow
Write-Host "  python mcp_client.py" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Green
