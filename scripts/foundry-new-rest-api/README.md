# NEW Foundry REST API Scripts (CognitiveServices)

This folder contains scripts for managing **NEW Azure AI Foundry** resources using the **Microsoft.CognitiveServices** provider.

## Architecture

- **Resource Type**: `Microsoft.CognitiveServices/accounts` (kind: AIServices)
- **Structure**: Account (parent) → Projects (children)
- **API Version**: `2025-06-01` (stable), `2026-01-15-preview` (connections)
- **Storage**: Automatic Cosmos DB `enterprise_memory` database with 5 containers

## Scripts

### Core CRUD Operations

#### `foundry_project_crud.py` ⭐ **PRIMARY SCRIPT**
Complete CRUD operations for NEW Foundry via ARM REST API.

**Features:**
- **CREATE**: Account (AIServices) + Projects
- **READ**: List accounts, Get account/project details, Get endpoints
- **UPDATE**: Tags, Network settings
- **DELETE**: Projects, Accounts, Purge soft-deleted accounts
- **CONNECTIONS**: Cosmos DB, OpenAI, Key Vault
- **RBAC**: Assign roles for service principals and users
- **DEPLOYMENTS**: Deploy and manage models

**CLI Usage:**
```bash
# Create full setup (account + project + connections + RBAC)
python foundry_project_crud.py full-setup

# Create account only
python foundry_project_crud.py create

# Read account details
python foundry_project_crud.py read

# Update account tags
python foundry_project_crud.py update

# Delete project and account
python foundry_project_crud.py delete

# Deploy model
python foundry_project_crud.py deploy-model

# Full teardown (delete everything)
python foundry_project_crud.py full-teardown
```

### Setup & Configuration

#### `setup_new_foundry_project.py`
Post-portal-creation setup script.

**What it does:**
1. Discovers CognitiveServices account + project
2. Adds connections (Cosmos, OpenAI, KeyVault)
3. Assigns RBAC roles
4. Creates agents via azure-ai-agents SDK
5. Tests conversations
6. Validates Cosmos DB integration

**Usage:**
```bash
python setup_new_foundry_project.py
```

### Validation & Testing

#### `foundry_storage_validation.py`
Validates NEW Foundry storage configuration (Cosmos DB).

#### `setup_foundry_storage_val.py`
Sets up storage validation environment.

#### `run_foundry_validation.py`
Runs end-to-end validation tests.

### Connection Management

#### `check_new_foundry_connections.py`
Checks connections for NEW Foundry projects.

#### `check_foundry_connections.py`
Lists and validates all connections (Cosmos, OpenAI, KV).

#### `check_foundry_kv.py`
Specifically checks Key Vault connections.

#### `check_foundry_portal.py`
Validates portal visibility and configuration.

### Resource Discovery

#### `find_foundry_resources.py`
Discovers all NEW Foundry resources in subscription.

**Output:**
- Lists all CognitiveServices accounts (kind: AIServices)
- Lists projects under each account
- Shows endpoints and properties

#### `compare_foundry_resources.py`
Compares OLD vs NEW Foundry resources.

**What it compares:**
- Resource types (MachineLearningServices vs CognitiveServices)
- Properties and capabilities
- Storage configurations
- Connection types

## Dependencies

```bash
pip install azure-identity azure-mgmt-cognitiveservices azure-ai-agents azure-ai-projects azure-cosmos requests
```

## Authentication

All scripts use `DefaultAzureCredential` from `azure-identity`:
- Run `az login` before executing scripts
- Or set environment variables for service principal auth

## Key Differences from OLD Foundry

| Aspect | OLD Foundry | NEW Foundry |
|--------|------------|-------------|
| Provider | MachineLearningServices | CognitiveServices |
| Resource Type | workspaces (Hub + Project) | accounts + accounts/projects |
| API Version | 2024-10-01, 2025-01-01-preview | 2025-06-01, 2026-01-15-preview |
| Storage | Manual setup | Auto-created Cosmos DB |
| Cosmos Containers | None | 5 (agent-definitions-v1, agent-entity-store, run-state-v1, thread-message-store, system-thread-message-store) |
| SDK | azure-ai-ml | azure-ai-agents, azure-ai-projects |

## Configuration

Edit these variables in scripts before running:

```python
SUB_ID       = "<your-subscription-id>"  # Your subscription
RG           = "<your-resource-group>"                       # Your resource group
LOCATION     = "<location>"                                 # Azure region (e.g., eastus)
ACCOUNT_NAME = "<foundry-account-name>"                      # AIServices account name
PROJECT_NAME = "<project-name>"                        # Project name
```

## Common Operations

### Create NEW Foundry (Complete Setup)
```bash
python foundry_project_crud.py full-setup
```

### Check Storage Validation
```bash
python foundry_storage_validation.py
```

### List All Connections
```bash
python foundry_project_crud.py list-connections
```

### Add Standard Connections
```bash
python foundry_project_crud.py add-connections
```

## Troubleshooting

### Account Already Exists
NEW Foundry uses soft-delete. If account name is taken:
```bash
python foundry_project_crud.py delete  # Soft delete
python foundry_project_crud.py purge    # Hard delete (wait 5 minutes)
```

### Connection Failures
Check RBAC assignments:
```bash
python foundry_project_crud.py assign-rbac
```

### Cosmos DB Not Created
Cosmos DB is auto-created on first agent operation. Run:
```bash
python setup_new_foundry_project.py
```

## References

- [NEW Foundry Storage Validation Report](../documentation/Foundry_Storage_Validation_Report_v2.txt)
- [Azure Cognitive Services REST API](https://docs.microsoft.com/rest/api/cognitiveservices/)
- [Azure AI Agents SDK](https://pypi.org/project/azure-ai-agents/)
