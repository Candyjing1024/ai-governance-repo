# Deployment Scripts

PowerShell scripts for deploying MCP server and related services to Azure.

## Overview

These scripts automate deployment to:
- Azure Container Apps
- Azure App Service
- Azure Container Registry (ACR)

## Scripts

### `deploy-container.ps1`
Deploys MCP server to Azure Container Apps.

**What it does:**
1. Builds Docker image
2. Pushes to Azure Container Registry
3. Creates/updates Container App
4. Configures environment variables
5. Sets up managed identity
6. Configures ingress (HTTPS)

**Usage:**
```powershell
.\deploy-container.ps1
```

**Parameters:**
```powershell
.\deploy-container.ps1 `
  -ResourceGroup "<your-resource-group>" `
  -Location "<location>" `
  -ContainerAppName "<container-app-name>" `
  -ImageTag "v1.0.0"
```

**Configuration:**
```powershell
$resourceGroup = "<your-resource-group>"
$location = "<location>"  # e.g., eastus
$acrName = "<acr-name>"
$containerAppName = "<container-app-name>"
$containerAppEnv = "<container-app-env>"
$imageName = "mcp-server"
$imageTag = "latest"
```

**Environment variables set:**
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_SEARCH_ENDPOINT`
- `COSMOS_CONNECTION_STRING`
- `KEY_VAULT_NAME`

**Outputs:**
- Container App URL: `https://<container-app-name>.<location>.azurecontainerapps.io`

### `deploy-appservice-westus2.ps1`
Deploys MCP server to Azure App Service (West US 2).

**What it does:**
1. Creates App Service Plan (Linux, P1V2)
2. Creates Web App
3. Configures Docker deployment from ACR
4. Sets environment variables
5. Enables managed identity
6. Configures CORS
7. Sets up custom domain (optional)

**Usage:**
```powershell
.\deploy-appservice-westus2.ps1
```

**Parameters:**
```powershell
.\deploy-appservice-westus2.ps1 `
  -ResourceGroup "<your-resource-group>" `
  -Location "<location>" `
  -AppName "<app-name>" `
  -Sku "P1V2"
```

**Configuration:**
```powershell
$resourceGroup = "<your-resource-group>"
$location = "westus2"
$appServicePlan = "<app-service-plan>"
$appName = "<app-name>"
$sku = "P1V2"  # Premium V2 (Production)
$dockerImage = "<acr-name>.azurecr.io/mcp-server:latest"
```

**SKU Options:**
- **B1**: Basic (Dev/Test) - $54.75/month
- **S1**: Standard - $73.00/month
- **P1V2**: Premium V2 (Production) - $110.96/month
- **P2V2**: Premium V2 (High traffic) - $221.92/month

**Outputs:**
- App Service URL: `https://<app-name>.azurewebsites.net`

### `deploy-production.ps1`
Production deployment with high availability.

**Features:**
- Multi-region deployment (East US + West US 2)
- Azure Front Door for load balancing
- Application Insights for monitoring
- Log Analytics workspace
- Auto-scaling configuration
- Slot deployment (staging → production)

**Usage:**
```powershell
.\deploy-production.ps1
```

**Deployment steps:**
1. Deploy to staging slot
2. Run smoke tests
3. Swap staging → production
4. Monitor for errors
5. Rollback if issues detected

**Configuration:**
```powershell
$primaryRegion = "<primary-location>"  # e.g., eastus
$secondaryRegion = "<secondary-location>"  # e.g., westus2
$frontDoorName = "<front-door-name>"
$appInsightsName = "<app-insights-name>"
$logAnalyticsName = "<log-analytics-workspace>"
```

**Auto-scaling rules:**
```powershell
# Scale out when CPU > 70%
$rule1 = @{
  metricName = "CpuPercentage"
  operator = "GreaterThan"
  threshold = 70
  direction = "Increase"
  changeCount = 1
}

# Scale in when CPU < 30%
$rule2 = @{
  metricName = "CpuPercentage"
  operator = "LessThan"
  threshold = 30
  direction = "Decrease"
  changeCount = 1
}
```

**Outputs:**
- Front Door URL: `https://<front-door-name>.azurefd.net`
- Primary App: `https://<app-name>-<primary-region>.azurewebsites.net`
- Secondary App: `https://<app-name>-<secondary-region>.azurewebsites.net`

### `check-container.ps1`
Checks Container App deployment status.

**What it checks:**
1. Container App exists
2. Revision active
3. Ingress configured
4. Replicas running
5. Health check passing
6. Logs for errors

**Usage:**
```powershell
.\check-container.ps1
```

**Output:**
```
Container App: ca-mcp-server
Status: Running
Replicas: 2/2
URL: https://<container-app-name>.<location>.azurecontainerapps.io
Health: Healthy
```

### `fix-and-redeploy.ps1`
Fixes common issues and redeploys.

**What it fixes:**
1. ACR authentication issues
2. Environment variable errors
3. Port configuration mismatches
4. Health check failures
5. SSL certificate issues

**Usage:**
```powershell
.\fix-and-redeploy.ps1
```

**Troubleshooting steps:**
1. Check ACR credentials
2. Verify environment variables
3. Test health endpoint locally
4. Rebuild image with fixes
5. Deploy new revision
6. Verify deployment

## Prerequisites

### Azure CLI
```powershell
# Install Azure CLI
winget install Microsoft.AzureCLI

# Login
az login

# Set subscription
az account set --subscription "Visual Studio Enterprise"
```

### Docker
```powershell
# Install Docker Desktop
winget install Docker.DockerDesktop
```

### Azure Container Registry
```powershell
# Create ACR
az acr create `
  --name <acr-name> `
  --resource-group <your-resource-group> `
  --sku Premium `
  --location <location>

# Login to ACR
az acr login --name <acr-name>
```

## Deployment Workflows

### Development Deployment
```powershell
# Build and test locally
docker build -t mcp-server:dev .
docker run -p 8000:8000 mcp-server:dev

# Deploy to Container Apps
.\deploy-container.ps1 -ImageTag "dev"
```

### Staging Deployment
```powershell
# Deploy to staging slot
.\deploy-appservice-westus2.ps1 -Slot "staging"

# Run tests
.\test-deployment.ps1 -Environment "staging"

# Swap to production
az webapp deployment slot swap `
  --name app-mcp-server-westus2 `
  --resource-group rg-chubb-mcp-poc `
  --slot staging `
  --target-slot production
```

### Production Deployment
```powershell
# Full production deployment
.\deploy-production.ps1

# Monitor
az monitor app-insights metrics show `
  --app ai-mcp-server `
  --metric requests/count
```

## Configuration Management

### Environment Variables
Store in Key Vault:
```powershell
az keyvault secret set `
  --vault-name <keyvault-name> `
  --name AZURE-OPENAI-KEY `
  --value "..."

# Reference in deployment
@Microsoft.KeyVault(SecretUri=https://<keyvault-name>.vault.azure.net/secrets/AZURE-OPENAI-KEY/)
```

### App Settings
```powershell
az webapp config appsettings set `
  --name <app-name> `
  --resource-group <your-resource-group> `
  --settings `
    AZURE_OPENAI_ENDPOINT="https://..." `
    PORT="8000"
```

## Monitoring

### Container Apps Logs
```powershell
az containerapp logs show `
  --name <container-app-name> `
  --resource-group <your-resource-group> `
  --follow
```

### App Service Logs
```powershell
az webapp log tail `
  --name <app-name> `
  --resource-group <your-resource-group>
```

### Application Insights
```powershell
az monitor app-insights query `
  --app <app-insights-name> `
  --analytics-query "requests | summarize count() by resultCode" `
  --offset 1h
```

## Troubleshooting

### Deployment Fails
```powershell
# Check deployment logs
az containerapp revision list `
  --name <container-app-name> `
  --resource-group <your-resource-group>

# Get revision logs
az containerapp logs show `
  --name <container-app-name> `
  --resource-group <your-resource-group> `
  --revision latest
```

### Container Won't Start
Check:
1. Port configuration (ENV PORT=8000)
2. Health check endpoint (/health)
3. Environment variables set
4. Image exists in ACR

### App Service Shows 403
Check:
1. Managed identity enabled
2. ACR permissions granted
3. RBAC assignments correct

## Cost Optimization

### Container Apps
- **Development**: 0.5 vCPU, 1 GB RAM, min 0 replicas
- **Production**: 2 vCPU, 4 GB RAM, min 2 replicas

### App Service
- Use App Service Plan with multiple apps
- Enable auto-scaling (scale down during off-hours)
- Use reserved instances for 30% discount

### Recommendations
- Dev/Test: Container Apps with 0 min replicas
- Production: App Service P1V2 with auto-scaling
- High availability: Multi-region with Front Door

## References

- [Azure Container Apps Docs](https://docs.microsoft.com/azure/container-apps/)
- [Azure App Service Docs](https://docs.microsoft.com/azure/app-service/)
- [Azure Container Registry Docs](https://docs.microsoft.com/azure/container-registry/)
