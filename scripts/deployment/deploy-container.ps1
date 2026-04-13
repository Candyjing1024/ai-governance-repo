# Azure Container Instances Deployment Script for Chubb MCP POC
# This script deploys the MCP server using Azure Container Instances (no quota issues)

# Configuration
$RESOURCE_GROUP = "rg-chubb-mcp-poc"
$LOCATION = "westus2"  # Alternative region to avoid quota issues
$RANDOM_SUFFIX = Get-Random -Minimum 1000 -Maximum 9999
$ACR_NAME = "acrchubbmcp$RANDOM_SUFFIX"
$CONTAINER_NAME = "aci-chubb-mcp-$RANDOM_SUFFIX"
$IMAGE_NAME = "chubb-mcp-server"
$KEY_VAULT_NAME = "kv-chubb-mcp-9342"  # Update if different

Write-Host "`n========== DEPLOYING MCP SERVER VIA AZURE CONTAINER INSTANCES ==========" -ForegroundColor Yellow
Write-Host "`nStep 1: Creating Azure Container Registry..." -ForegroundColor Green

# Create Azure Container Registry
az acr create `
    --resource-group $RESOURCE_GROUP `
    --name $ACR_NAME `
    --sku Basic `
    --location $LOCATION `
    --admin-enabled true

Write-Host "`nStep 2: Building and pushing Docker image..." -ForegroundColor Green

# Build and push image to ACR
az acr build `
    --registry $ACR_NAME `
    --image "${IMAGE_NAME}:latest" `
    --file Dockerfile `
    .

Write-Host "`nStep 3: Getting ACR credentials..." -ForegroundColor Green

# Get ACR credentials
$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --query "loginServer" -o tsv
$ACR_USERNAME = az acr credential show --name $ACR_NAME --query "username" -o tsv
$ACR_PASSWORD = az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv

Write-Host "`nStep 4: Creating Container Instance with Key Vault integration..." -ForegroundColor Green

# Create managed identity for Key Vault access
$IDENTITY_NAME = "id-chubb-mcp-aci"
az identity create --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --location $LOCATION
$IDENTITY_ID = az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --query "id" -o tsv
$IDENTITY_PRINCIPAL_ID = az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --query "principalId" -o tsv

# Grant identity access to Key Vault
az keyvault set-policy `
    --name $KEY_VAULT_NAME `
    --object-id $IDENTITY_PRINCIPAL_ID `
    --secret-permissions get list

Write-Host "`nStep 5: Deploying Container Instance..." -ForegroundColor Green

# Deploy Container Instance
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
    --environment-variables KEY_VAULT_NAME=$KEY_VAULT_NAME `
    --assign-identity $IDENTITY_ID `
    --location $LOCATION

Write-Host "`n========== DEPLOYMENT COMPLETE ==========" -ForegroundColor Green

# Get container details
$CONTAINER_FQDN = az container show --name $CONTAINER_NAME --resource-group $RESOURCE_GROUP --query "ipAddress.fqdn" -o tsv

Write-Host "`nMCP Server Endpoint: http://${CONTAINER_FQDN}:8000" -ForegroundColor Cyan
Write-Host "Health Check: http://${CONTAINER_FQDN}:8000/health" -ForegroundColor Cyan
Write-Host "MCP SSE Endpoint: http://${CONTAINER_FQDN}:8000/sse" -ForegroundColor Cyan
Write-Host "`n=========================================" -ForegroundColor Yellow
