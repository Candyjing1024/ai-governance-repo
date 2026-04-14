# AI Governance Scripts

Organized collection of scripts for managing Azure AI Foundry, MCP servers, APIM integration, and related Azure services.

## 📁 Directory Structure

```
scripts/
├── foundry-new-rest-api/      # NEW Foundry (CognitiveServices) CRUD operations
├── foundry-old-rest-api/       # OLD Foundry (MachineLearningServices) operations
├── apim/                       # Azure API Management integration
├── azure-policy/               # Azure Policy for AI model governance
└── documentation/              # Guides and validation reports
```

## 🚀 Quick Start

### Prerequisites

```powershell
# Install Azure CLI
winget install Microsoft.AzureCLI

# Login to Azure
az login
az account set --subscription "<your-subscription-name>"

# Install PowerShell Az module (for APIM scripts)
Install-Module -Name Az -AllowClobber -Scope CurrentUser
```

For Python scripts, install required packages:
```bash
pip install azure-identity azure-ai-agents azure-ai-projects azure-mgmt-cognitiveservices requests
```

### Common Workflows

#### 1. Create NEW Foundry (Complete Setup)
```bash
cd foundry-new-rest-api
python foundry_project_crud.py full-setup
```

#### 2. Setup APIM Integration
```powershell
cd apim
.\05-Full-Demo.ps1
```

## 📚 Category Overviews

### [foundry-new-rest-api/](foundry-new-rest-api/)
**NEW Azure AI Foundry (CognitiveServices)**

Complete CRUD operations for Microsoft.CognitiveServices/accounts (AIServices) and projects via ARM REST API.

**Key Scripts:**
- `foundry_project_crud.py` ⭐ - Complete CRUD with CLI
- `setup_new_foundry_project.py` - Post-creation setup
- `foundry_storage_validation.py` - Validate Cosmos DB storage
- `check_foundry_connections.py` - Validate connections
- `find_foundry_resources.py` - Discover resources

**API Version:** 2025-06-01 (stable)  
**Storage:** Auto-created Cosmos DB with 5 containers

### [foundry-old-rest-api/](foundry-old-rest-api/)
**OLD Azure AI Foundry (MachineLearningServices)**

Hub and Project management using Microsoft.MachineLearningServices/workspaces provider.

**Key Scripts:**
- `create_foundry_hub_project.py` - Create Hub + Project
- `delete_old_foundry.py` - Delete resources
- `recreate_foundry_for_new_ui.py` - Migrate to NEW UI
- `create_foundry_agent.py` - Create agents
- `test_foundry_agent.py` - Test agent functionality

**API Version:** 2024-10-01, 2025-01-01-preview  
**Storage:** Manual Cosmos DB configuration

### [apim/](apim/)
**Azure API Management**

PowerShell scripts for APIM as AI Gateway with Foundry integration and semantic caching.

**Key Scripts:**
- `05-Full-Demo.ps1` - Complete end-to-end demo
- `03-Register-FoundryInAPIM.ps1` - Register Foundry API
- `06-Create-AIGateway-SDK.ps1` - AI Gateway setup
- `07-Test-AIGateway.ps1` - Test AI Gateway
- `01-Create-ServicePrincipal.ps1` - Setup authentication
- `02-Create-APIM.ps1` - Create APIM instance

**Features:** Token management, rate limiting, semantic caching, product-based access control

**Documentation:**
- APIM-Foundry-Integration-Guide-Updated.txt
- APIM-Semantic-Cache-POC-End-to-End.txt
- APIM-Product-Based-Access-Control-Guide.txt

### [azure-policy/](azure-policy/)
**Azure Policy for AI Model Governance**

POC for controlling which AI models can be deployed in Foundry using Azure Policy built-in definitions.

**Key Scripts:**
- `01-Deploy-Model-Policy-POC.ps1` - Full POC (PowerShell/Azure CLI)
- `02-Validate-Model-Policy.py` - Full POC (Python/ARM REST API)
- `policy-params.json` - Approved model list configuration

**Features:** Policy assignment, deployment testing, compliance monitoring, cleanup

### [documentation/](documentation/)
**Documentation Files**

Guides, validation reports, and reference documentation.

**Key Files:**
- `Foundry_Agent_Setup_Guide.txt` - Complete setup guide (OLD Foundry)
- `Foundry_Storage_Validation_Report_v2.txt` - NEW Foundry validation with screenshots
- `Foundry_Storage_Validation_Report.txt` - Initial validation report
- `README-original.md` - Original project README

## 🔑 Configuration

Scripts use Azure environment variables or configuration within each script:

```bash
export AZURE_SUBSCRIPTION_ID="..."
export AZURE_RESOURCE_GROUP="..."
export AZURE_TENANT_ID="..."
export AZURE_LOCATION="..."
```

For APIM scripts, edit `apim/apim-poc/00-Config.ps1`:

```powershell
$TenantId           = "<your-tenant-id>"
$SubscriptionId     = "<your-subscription-id>"
$ResourceGroup      = "<your-resource-group>"
$Location           = "<location>"
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

### Python (for Foundry scripts)
```bash
pip install azure-identity azure-ai-agents azure-ai-projects \
            azure-mgmt-cognitiveservices requests
```

### PowerShell (for APIM scripts)
```powershell
Install-Module -Name Az -AllowClobber -Scope CurrentUser
```

### Tools
- Azure CLI (`az`) - Required for authentication and resource management
- Git - For version control

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

### Setup New Foundry Environment
```bash
# Create NEW Foundry resources with complete setup
cd foundry-new-rest-api
python foundry_project_crud.py full-setup
```

### Setup APIM Integration
```powershell
# Complete APIM + Foundry integration
cd apim
.\01-Create-ServicePrincipal.ps1
.\02-Create-APIM.ps1
.\03-Register-FoundryInAPIM.ps1
.\04-Test-Token-Flow.ps1

# Or run full demo
.\05-Full-Demo.ps1
```

### Migrate from OLD to NEW Foundry
```bash
# 1. Delete OLD resources
cd foundry-old-rest-api
python delete_old_foundry.py

# 2. Create NEW resources
cd ../foundry-new-rest-api
python foundry_project_crud.py full-setup
```

### Manage Foundry Resources
```bash
# List all Foundry resources
cd foundry-new-rest-api
python find_foundry_resources.py

# Check connections
python check_foundry_connections.py

# Validate storage
python foundry_storage_validation.py
```

##  Security Best Practices

1. **Use Azure Key Vault** for storing secrets and credentials
2. **Enable Managed Identity** for Azure service authentication  
3. **Use RBAC** for access control instead of keys when possible
4. **Enable soft delete** on critical resources like Key Vault
5. **Rotate secrets** regularly (recommended: every 90 days)
6. **Use service principals** with minimal required permissions
7. **Monitor Azure Activity Logs** for security events

## 📖 Documentation

Each category has detailed documentation:
- [NEW Foundry REST API](foundry-new-rest-api/) - See scripts for inline documentation
- [OLD Foundry REST API](foundry-old-rest-api/) - See scripts for inline documentation
- [APIM](apim/) - Comprehensive guides in apim-poc/ folder
- [Documentation Files](documentation/) - Setup guides and validation reports

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
