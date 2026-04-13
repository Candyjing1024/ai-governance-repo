# Cosmos DB Scripts

Scripts for configuring and validating Azure Cosmos DB integration with Foundry projects.

## Overview

Azure AI Foundry (NEW) auto-creates a Cosmos DB database named `enterprise_memory` with 5 containers for agent operations:

1. **agent-definitions-v1** - Agent configurations
2. **agent-entity-store** - Agent entities and state
3. **run-state-v1** - Agent run execution state
4. **thread-message-store** - Conversation messages
5. **system-thread-message-store** - System messages

## Scripts

### Configuration

#### `configure_cosmos_agent_service.py`
Configures Cosmos DB for agent service integration.

**What it configures:**
- Database: `enterprise_memory`
- Containers with partition keys
- Throughput settings (autoscale 1000-4000 RU/s recommended)
- Connection strings as Foundry connections

**Usage:**
```bash
python configure_cosmos_agent_service.py
```

#### `configure_cosmos_threads.py`
Specifically configures thread-related containers.

**Containers:**
- `thread-message-store` (partition key: `/threadId`)
- `system-thread-message-store` (partition key: `/threadId`)

**Usage:**
```bash
python configure_cosmos_threads.py
```

### Validation

#### `check_threads_cosmos.py`
Checks thread data in Cosmos DB.

**What it checks:**
- Thread existence
- Message counts
- Last activity timestamp
- Thread metadata

**Usage:**
```bash
python check_threads_cosmos.py
```

**Sample output:**
```
Thread: thread_abc123
Messages: 10
Last Activity: 2026-04-13T18:30:00Z
Status: Active
```

#### `verify_cosmos_config.py`
Verifies complete Cosmos DB configuration.

**Verification steps:**
1. Database exists
2. All 5 containers exist
3. Partition keys correct
4. Throughput settings appropriate
5. Connection string valid
6. RBAC permissions granted

**Usage:**
```bash
python verify_cosmos_config.py
```

### Creation

#### `create_ml_hub_cosmos.py`
Creates Cosmos DB resources for ML Hub (OLD Foundry).

**What it creates:**
- Cosmos DB account (if not exists)
- `enterprise_memory` database
- Required containers with partition keys

**Usage:**
```bash
python create_ml_hub_cosmos.py
```

## Dependencies

```bash
pip install azure-cosmos azure-identity azure-mgmt-cosmosdb
```

## Configuration

Edit these variables:

```python
SUB_ID = "<your-subscription-id>"
RG = "<your-resource-group>"
COSMOS_ACCOUNT = "<cosmos-account-name>"
DATABASE_NAME = "enterprise_memory"
```

## Cosmos DB Connection String Format

```
AccountEndpoint=https://<account>.documents.azure.com:443/;AccountKey=<key>
```

## Container Specifications

### agent-definitions-v1
- **Partition Key**: `/id`
- **Purpose**: Store agent configurations
- **Sample document**:
```json
{
  "id": "agent_abc123",
  "name": "my-agent",
  "model": "gpt-4o",
  "instructions": "You are a helpful assistant",
  "tools": []
}
```

### thread-message-store
- **Partition Key**: `/threadId`
- **Purpose**: Store conversation messages
- **Sample document**:
```json
{
  "id": "msg_xyz789",
  "threadId": "thread_abc123",
  "role": "user",
  "content": "Hello!",
  "timestamp": "2026-04-13T18:30:00Z"
}
```

### run-state-v1
- **Partition Key**: `/threadId`
- **Purpose**: Store agent run execution state
- **Sample document**:
```json
{
  "id": "run_def456",
  "threadId": "thread_abc123",
  "status": "completed",
  "startTime": "2026-04-13T18:30:00Z",
  "endTime": "2026-04-13T18:30:05Z"
}
```

## Common Operations

### Configure from Scratch
```bash
python create_ml_hub_cosmos.py
python configure_cosmos_agent_service.py
python configure_cosmos_threads.py
```

### Verify Configuration
```bash
python verify_cosmos_config.py
```

### Check Thread Data
```bash
python check_threads_cosmos.py
```

## Throughput Recommendations

- **Development**: 400-1000 RU/s (autoscale)
- **Production**: 1000-4000 RU/s (autoscale)
- **High traffic**: 4000+ RU/s or consider serverless

## RBAC Permissions Required

For Foundry to access Cosmos DB:

```
"Cosmos DB Built-in Data Contributor" role on Cosmos DB account
```

Assign via:
```bash
az cosmosdb sql role assignment create \
  --account-name $COSMOS_ACCOUNT \
  --resource-group $RG \
  --scope "/" \
  --principal-id $FOUNDRY_PRINCIPAL_ID \
  --role-definition-id 00000000-0000-0000-0000-000000000002
```

## Troubleshooting

### Container Not Found
Run configuration scripts:
```bash
python configure_cosmos_agent_service.py
```

### Permission Denied
Check RBAC assignments and ensure Foundry service principal has access.

### High RU Consumption
Monitor queries and consider:
- Adding indexes
- Optimizing partition key design
- Using autoscale throughput

## Monitoring

Query container metrics:
```bash
az cosmosdb sql database throughput show \
  --account-name $COSMOS_ACCOUNT \
  --resource-group $RG \
  --name enterprise_memory
```

## References

- [Azure Cosmos DB Documentation](https://docs.microsoft.com/azure/cosmos-db/)
- [Cosmos DB Python SDK](https://pypi.org/project/azure-cosmos/)
- [Foundry Storage Validation Report](../documentation/Foundry_Storage_Validation_Report_v2.txt)
