# OLD Foundry REST API Scripts (MachineLearningServices)

This folder contains scripts for managing **OLD Azure AI Foundry** resources using the **Microsoft.MachineLearningServices** provider.

## Architecture

- **Resource Type**: `Microsoft.MachineLearningServices/workspaces`
- **Structure**: Hub (kind: Hub) → Project (kind: Project)
- **API Version**: `2024-10-01`, `2025-01-01-preview`
- **Storage**: Manual Cosmos DB configuration required

## Scripts

### Hub & Project Creation

#### `create_foundry_hub_project.py`
Creates OLD Foundry Hub and Project using ARM REST API.

**What it creates:**
1. Hub workspace (parent)
2. Project workspace (child - references hub via `hubResourceId`)
3. Waits for provisioning (polling with retry)

**Usage:**
```bash
python create_foundry_hub_project.py
```

**API Calls:**
```python
# Hub creation
PUT /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.MachineLearningServices/workspaces/{hub}?api-version=2025-01-01-preview
Body: {
  "kind": "Hub",
  "location": "eastus",
  "properties": {...}
}

# Project creation
PUT /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.MachineLearningServices/workspaces/{project}?api-version=2025-01-01-preview
Body: {
  "kind": "Project",
  "properties": {
    "hubResourceId": "<hub-resource-id>"
  }
}
```

### Deletion

#### `delete_old_foundry.py`
Deletes OLD Foundry Hub and Project.

**What it does:**
1. Deletes Project first (child must be deleted before parent)
2. Deletes Hub
3. Polls until deletion completes (40 attempts × 10s)

**Usage:**
```bash
python delete_old_foundry.py
```

**Important:** Always delete Project before Hub to avoid dependency errors.

### Migration

#### `recreate_foundry_for_new_ui.py`
Migrates from OLD to NEW Foundry UI.

**What it does:**
1. Deletes OLD Hub/Project resources
2. Recreates using `az ml workspace create` CLI
3. Re-adds connections (OpenAI, Cosmos, KeyVault)
4. Re-assigns RBAC roles
5. Verifies in Azure portal

**Usage:**
```bash
python recreate_foundry_for_new_ui.py
```

**Note:** This script uses Azure CLI (`az ml`) instead of pure REST API.

### Agent Management

#### `create_foundry_agent.py`
Creates AI agents in OLD Foundry using azure-ai-agents SDK.

**SDK Operations:**
```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import Agent

# Create agent
agent = project_client.agents.create_agent(
    model="gpt-4o",
    name="my-agent",
    instructions="You are a helpful assistant"
)
```

#### `test_foundry_agent.py`
Tests agents with conversation flows.

**What it tests:**
1. Thread creation
2. Message sending
3. Run execution
4. Response retrieval
5. Multi-turn conversations

**Usage:**
```bash
python test_foundry_agent.py
```

#### `retry_agent_test.py`
Retry logic for failed agent tests with exponential backoff.

#### `diagnose_agent_failure.py`
Diagnoses agent failures and provides debugging info.

**Checks:**
- Agent definition exists
- Thread state
- Run status (failed/cancelled/expired)
- Error messages
- Connection issues

## Dependencies

```bash
pip install azure-identity azure-ai-ml azure-ai-agents azure-ai-projects requests
```

## Authentication

```bash
az login
```

Or use service principal:
```bash
export AZURE_CLIENT_ID="<client-id>"
export AZURE_CLIENT_SECRET="<client-secret>"
export AZURE_TENANT_ID="<tenant-id>"
```

## Configuration

Edit these variables before running:

```python
SUB_ID   = "<your-subscription-id>"
RG       = "<your-resource-group>"
LOCATION = "<location>"  # e.g., eastus
HUB_NAME = "<hub-name>"
PROJECT_NAME = "<project-name>"
```

## Common Operations

### Create Hub + Project
```bash
python create_foundry_hub_project.py
```

### Delete Hub + Project
```bash
python delete_old_foundry.py
```

### Create and Test Agent
```bash
python create_foundry_agent.py
python test_foundry_agent.py
```

### Migrate to NEW UI
```bash
python recreate_foundry_for_new_ui.py
```

## Key Differences from NEW Foundry

| Aspect | OLD Foundry | NEW Foundry |
|--------|------------|-------------|
| Provider | MachineLearningServices | CognitiveServices |
| Resource Type | workspaces (Hub + Project) | accounts + accounts/projects |
| Deletion | Manual, requires order | Soft-delete with purge |
| Storage | Manual Cosmos setup | Auto-created Cosmos DB |
| SDK | azure-ai-ml | azure-ai-agents, azure-ai-projects |
| Portal UI | OLD UI | NEW UI (2025+) |

## Troubleshooting

### Project Deletion Fails
Delete Project before Hub:
```bash
# Correct order
DELETE /workspaces/{project}  # Child first
DELETE /workspaces/{hub}      # Parent second
```

### Hub Already Exists
Delete existing hub first:
```bash
python delete_old_foundry.py
```

### Agent Creation Fails
Check:
1. Hub and Project exist
2. OpenAI connection configured
3. RBAC roles assigned
4. Model deployed

## Migration Path

To migrate from OLD to NEW Foundry:

1. **Export agent definitions** (backup)
2. **Delete OLD resources**:
   ```bash
   python delete_old_foundry.py
   ```
3. **Create NEW resources**:
   ```bash
   # Switch to foundry-new-rest-api folder
   python ../foundry-new-rest-api/foundry_project_crud.py full-setup
   ```
4. **Recreate agents** using azure-ai-agents SDK

## References

- [OLD Foundry Setup Guide](../documentation/Foundry_Agent_Setup_Guide.txt)
- [Azure ML Workspaces REST API](https://docs.microsoft.com/rest/api/azureml/workspaces)
- [Azure AI ML SDK](https://pypi.org/project/azure-ai-ml/)
