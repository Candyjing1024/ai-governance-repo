# AI Governance Scripts

Organized collection of scripts for managing Azure AI Foundry, MCP servers, APIM integration, and related Azure services.

## 📁 Directory Structure

```
scripts/
├── foundry-new-rest-api/      # NEW Foundry (CognitiveServices) CRUD operations
├── foundry-old-rest-api/       # OLD Foundry (MachineLearningServices) operations
├── cosmos-db/                  # Cosmos DB configuration and validation
├── mcp-server/                 # MCP server implementation and clients
├── apim/                       # Azure API Management integration
├── azure-search/               # Azure AI Search indexing and queries
├── deployment/                 # Deployment scripts (PowerShell)
├── testing/                    # Testing and validation scripts
├── utilities/                  # General utility scripts
└── documentation/              # Guides and validation reports
```

## 🚀 Quick Start

### Prerequisites

```powershell
# Install Azure CLI
winget install Microsoft.AzureCLI

# Install Python dependencies
pip install -r requirements.txt

# Login to Azure
az login
az account set --subscription "<your-subscription-name>"
```

### Common Workflows

#### 1. Create NEW Foundry (Complete Setup)
```bash
cd foundry-new-rest-api
python foundry_project_crud.py full-setup
```

#### 2. Deploy MCP Server
```powershell
cd deployment
.\deploy-container.ps1
```

#### 3. Setup APIM Integration
```powershell
cd apim
.\05-Full-Demo.ps1
```

#### 4. Test Everything
```bash
cd testing
python test_endpoints.py
```

## 📚 Category Overviews

### [foundry-new-rest-api/](foundry-new-rest-api/)
**NEW Azure AI Foundry (CognitiveServices)**

Complete CRUD operations for Microsoft.CognitiveServices/accounts (AIServices) and projects via ARM REST API.

**Key Scripts:**
- `foundry_project_crud.py` ⭐ - Complete CRUD with CLI
- `setup_new_foundry_project.py` - Post-creation setup
- `foundry_storage_validation.py` - Validate Cosmos DB storage

**API Version:** 2025-06-01 (stable)  
**Storage:** Auto-created Cosmos DB with 5 containers

### [foundry-old-rest-api/](foundry-old-rest-api/)
**OLD Azure AI Foundry (MachineLearningServices)**

Hub and Project management using Microsoft.MachineLearningServices/workspaces provider.

**Key Scripts:**
- `create_foundry_hub_project.py` - Create Hub + Project
- `delete_old_foundry.py` - Delete resources
- `recreate_foundry_for_new_ui.py` - Migrate to NEW UI

**API Version:** 2024-10-01, 2025-01-01-preview  
**Storage:** Manual Cosmos DB configuration

### [cosmos-db/](cosmos-db/)
**Cosmos DB Integration**

Configure and validate Cosmos DB for Foundry agent storage.

**Key Scripts:**
- `configure_cosmos_agent_service.py` - Setup enterprise_memory database
- `check_threads_cosmos.py` - Validate thread storage
- `verify_cosmos_config.py` - Full configuration check

**Database:** `enterprise_memory`  
**Containers:** 5 (agent-definitions-v1, thread-message-store, run-state-v1, etc.)

### [mcp-server/](mcp-server/)
**Model Context Protocol Server**

MCP server implementation with RAG capabilities and Azure service integration.

**Key Files:**
- `mcp_server.py` - Main server implementation
- `mcp_client.py` - Standalone client
- `mcp_client_apim.py` - APIM-integrated client
- `rag_tool.py` - RAG tool implementation
- `Dockerfile` - Container image

**Framework:** FastAPI + uvicorn  
**Protocol:** MCP (Model Context Protocol)

### [apim/](apim/)
**Azure API Management**

PowerShell scripts for APIM as AI Gateway with Foundry integration and semantic caching.

**Key Scripts:**
- `05-Full-Demo.ps1` - Complete end-to-end demo
- `03-Register-FoundryInAPIM.ps1` - Register Foundry API
- `06-Create-AIGateway-SDK.ps1` - AI Gateway setup
- `07-Test-AIGateway.ps1` - Test AI Gateway

**Features:** Token management, rate limiting, semantic caching, product-based access control

### [azure-search/](azure-search/)
**Azure AI Search**

Index creation, document upload, and vector search configuration.

**Key Scripts:**
- `create_index.py` - Create search index with vector support
- `upload_documents.py` - Upload and chunk documents
- `ai_search_indexer.py` - Configure automatic indexing

**Capabilities:** Vector search, semantic ranking, hybrid search

### [deployment/](deployment/)
**Deployment Scripts**

PowerShell scripts for deploying to Azure Container Apps and App Service.

**Key Scripts:**
- `deploy-container.ps1` - Deploy to Container Apps
- `deploy-appservice-westus2.ps1` - Deploy to App Service
- `deploy-production.ps1` - Multi-region production deployment
- `check-container.ps1` - Verify deployment

**Targets:** Container Apps, App Service, Azure Container Registry

### [testing/](testing/)
**Testing Scripts**

Validate deployments, connections, and end-to-end flows.

**Key Scripts:**
- `test_endpoints.py` - Test all Azure service endpoints
- `test_appservice_mcp.py` - Test MCP server deployment
- `testOAIconnection.py` - Test OpenAI connection
- `deploy_model_and_test.py` - Deploy and test models

**Frameworks:** pytest, requests

### [utilities/](utilities/)
**Utility Scripts**

Configuration, Key Vault, storage, and resource management.

**Key Scripts:**
- `config.py` - Central configuration file
- `check_kv.py` - Validate Key Vault secrets
- `fix_kv_secrets.py` - Fix Key Vault issues
- `update_appservice_env.py` - Update App Service settings
- `restore_resources.py` - Restore soft-deleted resources

**Purpose:** Configuration management, troubleshooting, disaster recovery

### [documentation/](documentation/)
**Documentation Files**

Guides, validation reports, and reference documentation.

**Key Files:**
- `Foundry_Agent_Setup_Guide.txt` - Complete setup guide (OLD Foundry)
- `Foundry_Storage_Validation_Report_v2.txt` - NEW Foundry validation with screenshots
- `README-original.md` - Original project README

## 🔑 Configuration

Edit `utilities/config.py` with your Azure details:

```python
SUB_ID = "your-subscription-id"
RG = "your-resource-group"
LOCATION = "eastus"
ACCOUNT_NAME = "your-foundry-account"
```

Or set environment variables:

```bash
export AZURE_SUBSCRIPTION_ID="..."
export AZURE_RESOURCE_GROUP="..."
export AZURE_OPENAI_ENDPOINT="..."
export AZURE_OPENAI_KEY="..."
```

## 🔐 Authentication

All scripts use `DefaultAzureCredential`:

```bash
# Interactive login
az login

# Or service principal
export AZURE_CLIENT_ID="..."
export AZURE_CLIENT_SECRET="..."
export AZURE_TENANT_ID="..."
```

## 📦 Dependencies

### Python
```bash
pip install azure-identity azure-ai-agents azure-ai-projects azure-cosmos \
            azure-search-documents azure-mgmt-cognitiveservices requests \
            openai pytest
```

### PowerShell
```powershell
Install-Module -Name Az -AllowClobber -Scope CurrentUser
```

### Tools
- Azure CLI (`az`)
- Docker Desktop
- Git

## 🏗️ Architecture Comparison

| Aspect | OLD Foundry | NEW Foundry |
|--------|------------|-------------|
| **Provider** | MachineLearningServices | CognitiveServices |
| **Resource Type** | workspaces (Hub + Project) | accounts + projects |
| **API Version** | 2024-10-01, 2025-01-01-preview | 2025-06-01, 2026-01-15-preview |
| **Storage** | Manual Cosmos setup | Auto-created Cosmos DB |
| **SDK** | azure-ai-ml | azure-ai-agents, azure-ai-projects |
| **Deletion** | Manual order (Project → Hub) | Soft delete with purge |

## 🛠️ Common Tasks

### Setup New Environment
```bash
# 1. Create Foundry resources
cd foundry-new-rest-api
python foundry_project_crud.py full-setup

# 2. Configure Cosmos DB
cd ../cosmos-db
python configure_cosmos_agent_service.py

# 3. Setup Azure Search
cd ../azure-search
python create_index.py
python upload_documents.py --dir "documents/"

# 4. Deploy MCP server
cd ../deployment
.\deploy-container.ps1

# 5. Setup APIM
cd ../apim
.\03-Register-FoundryInAPIM.ps1

# 6. Test everything
cd ../testing
python test_endpoints.py
```

### Migrate from OLD to NEW Foundry
```bash
# 1. Backup agent definitions
cd foundry-old-rest-api
python backup_agents.py

# 2. Delete OLD resources
python delete_old_foundry.py

# 3. Create NEW resources
cd ../foundry-new-rest-api
python foundry_project_crud.py full-setup

# 4. Restore agents
python restore_agents.py
```

### Troubleshoot Issues
```bash
# Check Key Vault
cd utilities
python check_kv.py

# Check storage
python fix_and_inspect_storage.py

# Check Foundry connections
cd ../foundry-new-rest-api
python check_foundry_connections.py

# Test endpoints
cd ../testing
python test_endpoints.py
```

## 📊 Monitoring

### View Logs
```powershell
# Container Apps
az containerapp logs show --name ca-mcp-server --resource-group rg-chubb-mcp-poc --follow

# App Service
az webapp log tail --name app-mcp-server-westus2 --resource-group rg-chubb-mcp-poc
```

### View Metrics
```powershell
# Query Application Insights
az monitor app-insights query \
  --app ai-mcp-server \
  --analytics-query "requests | summarize count() by resultCode" \
  --offset 1h
```

## 🔒 Security Best Practices

1. **Use Key Vault** for all secrets
2. **Enable Managed Identity** for Azure service authentication
3. **Use RBAC** instead of keys when possible
4. **Enable soft delete** on critical resources
5. **Use Private Endpoints** for production
6. **Rotate keys** every 90 days
7. **Monitor access logs** in Azure Monitor

## 📖 Documentation

Each category has detailed README:
- [NEW Foundry REST API](foundry-new-rest-api/README.md)
- [OLD Foundry REST API](foundry-old-rest-api/README.md)
- [Cosmos DB](cosmos-db/README.md)
- [MCP Server](mcp-server/README.md)
- [APIM](apim/README.md)
- [Azure Search](azure-search/README.md)
- [Deployment](deployment/README.md)
- [Testing](testing/README.md)
- [Utilities](utilities/README.md)

## 🤝 Contributing

1. Create feature branch
2. Test thoroughly in dev environment
3. Update README if adding new scripts
4. Submit pull request with description

## 📝 License

Internal use only

## 🆘 Support

For issues or questions:
1. Check category README
2. Review documentation files
3. Test with validation scripts
4. Contact team lead

---

**Last Updated:** April 13, 2026  
**Maintained By:** AI Governance Team
