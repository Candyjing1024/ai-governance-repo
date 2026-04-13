# Utility Scripts

General utility scripts for configuration, resource management, and troubleshooting.

## Overview

Collection of utility scripts for:
- Configuration management
- Key Vault operations
- Storage inspection
- Resource restoration
- Environment updates
- SKU validation

## Scripts

### `config.py`
Central configuration file for all scripts.

**Contains:**
```python
# Subscription
SUB_ID = "<your-subscription-id>"

# Resource Group
RG = "<your-resource-group>"
LOCATION = "<location>"  # e.g., eastus

# Foundry (NEW)
ACCOUNT_NAME = "<foundry-account-name>"
PROJECT_NAME = "<project-name>"

# Foundry (OLD)
HUB_NAME = "<hub-name>"
PROJECT_NAME_OLD = "<old-project-name>"

# OpenAI
OPENAI_ENDPOINT = "https://<openai-resource-name>.openai.azure.com/"
OPENAI_DEPLOYMENT = "gpt-4o"

# Cosmos DB
COSMOS_ACCOUNT = "<cosmos-account-name>"
COSMOS_DATABASE = "enterprise_memory"

# Key Vault
KEY_VAULT_NAME = "<keyvault-name>"

# Azure Search
SEARCH_ENDPOINT = "https://<search-service-name>.search.windows.net"
SEARCH_INDEX = "ai-governance-docs"

# APIM
APIM_ENDPOINT = "https://<apim-service-name>.azure-api.net"
```

**Usage:**
```python
from config import SUB_ID, RG, ACCOUNT_NAME

print(f"Subscription: {SUB_ID}")
print(f"Resource Group: {RG}")
```

### `check_kv.py`
Checks Key Vault secrets and access.

**What it checks:**
1. Key Vault exists
2. Secrets present
3. Access policies configured
4. Managed identities have access
5. Secret expiration dates

**Usage:**
```bash
python check_kv.py
```

**Output:**
```
Key Vault: <keyvault-name>
Status: Active

Secrets:
  ✓ AZURE-OPENAI-KEY (Expires: 2027-01-01)
  ✓ COSMOS-CONNECTION-STRING (Never expires)
  ✓ AZURE-SEARCH-KEY (Expires: 2026-12-01)

Access Policies:
  ✓ User: <your-email> (Get, List)
  ✓ App: <app-name> (Get, List)
  ✓ Managed Identity: <managed-identity-name> (Get, List)

All checks passed!
```

### `fix_kv_secrets.py`
Fixes common Key Vault secret issues.

**What it fixes:**
1. Missing secrets (creates with placeholder)
2. Expired secrets (rotates)
3. Incorrect format (reformats)
4. Missing access policies (adds)
5. Soft-deleted secrets (purges and recreates)

**Usage:**
```bash
python fix_kv_secrets.py
```

**Actions:**
```python
# 1. Check for missing secrets
required_secrets = [
    "AZURE-OPENAI-KEY",
    "COSMOS-CONNECTION-STRING",
    "AZURE-SEARCH-KEY"
]

for secret_name in required_secrets:
    if not secret_exists(secret_name):
        create_placeholder_secret(secret_name)

# 2. Check expiration
for secret in list_secrets():
    if secret.expires_on and secret.expires_on < datetime.now():
        rotate_secret(secret.name)

# 3. Fix access policies
ensure_access_policy(
    object_id=managed_identity_id,
    permissions=["get", "list"]
)
```

### `fix_and_inspect_storage.py`
Inspects and fixes storage account issues.

**What it checks:**
1. Storage account exists
2. Containers present
3. CORS configured
4. Access tier appropriate
5. Network rules
6. Blob retention policies

**What it fixes:**
1. Missing containers (creates)
2. Incorrect CORS (updates)
3. Public access (disables if not needed)
4. Soft delete not enabled (enables)

**Usage:**
```bash
python fix_and_inspect_storage.py
```

**Output:**
```
Storage Account: <storage-account-name>
Status: Available

Containers:
  ✓ documents (1250 blobs, 450 MB)
  ✓ uploads (34 blobs, 12 MB)
  ! backups (Missing) → Created

CORS Settings:
  ✓ Allowed origins: https://<your-domain>.com
  ✓ Allowed methods: GET, POST
  ✓ Max age: 3600s

Network Rules:
  ✓ Public access: Disabled
  ✓ VNet rules: 2 subnets

Soft Delete:
  ✓ Enabled (7 days retention)

Fixed 1 issue.
```

### `update_appservice_env.py`
Updates App Service environment variables.

**What it updates:**
1. App settings (environment variables)
2. Connection strings
3. Key Vault references
4. Managed identity assignments

**Usage:**
```bash
# Update single setting
python update_appservice_env.py --name AZURE_OPENAI_ENDPOINT --value "https://..."

# Update from file
python update_appservice_env.py --file env.json

# Update with Key Vault reference
python update_appservice_env.py --name AZURE_OPENAI_KEY --keyvault-secret AZURE-OPENAI-KEY
```

**Configuration file (env.json):**
```json
{
  "AZURE_OPENAI_ENDPOINT": "https://<openai-resource-name>.openai.azure.com/",
  "AZURE_SEARCH_ENDPOINT": "https://<search-service-name>.search.windows.net",
  "COSMOS_CONNECTION_STRING": "@Microsoft.KeyVault(SecretUri=...)",
  "PORT": "8000",
  "LOG_LEVEL": "INFO"
}
```

**Example:**
```python
from update_appservice_env import update_settings

# Update app settings
update_settings(
    app_name="<app-name>",
    resource_group="<your-resource-group>",
    settings={
        "AZURE_OPENAI_ENDPOINT": "https://...",
        "PORT": "8000"
    }
)

# Add Key Vault reference
update_settings(
    app_name="<app-name>",
    resource_group="<your-resource-group>",
    settings={
        "AZURE_OPENAI_KEY": "@Microsoft.KeyVault(SecretUri=https://<keyvault-name>.vault.azure.net/secrets/AZURE-OPENAI-KEY/)"
    }
)
```

### `restore_resources.py`
Restores soft-deleted Azure resources.

**What it restores:**
- Key Vault (soft-deleted)
- Cosmos DB account (soft-deleted)
- Cognitive Services account (soft-deleted)
- Storage account (soft-deleted)

**Usage:**
```bash
# List soft-deleted resources
python restore_resources.py --list

# Restore specific resource
python restore_resources.py --restore --name <keyvault-name> --type keyvault

# Restore all
python restore_resources.py --restore-all
```

**Example:**
```python
from restore_resources import restore_keyvault, restore_cognitive_services

# Restore Key Vault
restore_keyvault(
    vault_name="<keyvault-name>",
    location="<location>"
)

# Restore Cognitive Services (Foundry)
restore_cognitive_services(
    account_name="<foundry-account-name>",
    resource_group="<your-resource-group>",
    location="<location>"
)
```

### `verify_restore.py`
Verifies restored resources are functional.

**What it verifies:**
1. Resource exists
2. Provisioning state = Succeeded
3. Endpoints reachable
4. Authentication works
5. Dependencies connected

**Usage:**
```bash
python verify_restore.py --resource <keyvault-name>
```

**Checks:**
```python
# 1. Resource exists
resource = get_resource(name, type)
assert resource.provisioning_state == "Succeeded"

# 2. Endpoint reachable
response = requests.get(f"{resource.endpoint}/health")
assert response.status_code == 200

# 3. Authentication works
credential = DefaultAzureCredential()
token = credential.get_token(f"{resource.endpoint}/.default")
assert token.token

# 4. Dependencies
if resource.type == "foundry":
    assert cosmos_connection_exists()
    assert openai_connection_exists()
```

### `_check_sku.py`
Checks and validates Azure resource SKUs.

**What it checks:**
- Available SKUs for resource type
- Current SKU assignment
- SKU capabilities
- SKU pricing
- SKU regional availability

**Usage:**
```bash
# Check available SKUs for App Service
python _check_sku.py --type appservice --location eastus

# Check current SKU
python _check_sku.py --resource app-mcp-server-westus2

# Compare SKUs
python _check_sku.py --compare B1,S1,P1V2
```

**Output:**
```
App Service SKUs in East US:

Basic (B1):
  vCPU: 1
  RAM: 1.75 GB
  Price: $54.75/month
  ✓ Available

Standard (S1):
  vCPU: 1
  RAM: 1.75 GB
  Price: $73.00/month
  ✓ Available

Premium V2 (P1V2):
  vCPU: 1
  RAM: 3.5 GB
  Price: $110.96/month
  ✓ Available
  ✓ Auto-scaling
  ✓ VNet integration
```

## Dependencies

```bash
pip install azure-identity azure-mgmt-keyvault azure-mgmt-storage azure-mgmt-web azure-mgmt-resource
```

## Common Tasks

### Setup Environment
```bash
# 1. Configure variables
vim config.py

# 2. Check Key Vault
python check_kv.py

# 3. Fix any issues
python fix_kv_secrets.py

# 4. Update App Service
python update_appservice_env.py --file env.json
```

### Troubleshoot Resource
```bash
# 1. Check SKU
python _check_sku.py --resource <resource-name>

# 2. Inspect storage
python fix_and_inspect_storage.py

# 3. Verify Key Vault
python check_kv.py
```

### Disaster Recovery
```bash
# 1. List deleted resources
python restore_resources.py --list

# 2. Restore resources
python restore_resources.py --restore-all

# 3. Verify restoration
python verify_restore.py --all
```

## Best Practices

1. **Always backup** before running fix scripts
2. **Test in dev** before production
3. **Use Key Vault references** for secrets in App Service
4. **Enable soft delete** on critical resources
5. **Monitor costs** when changing SKUs
6. **Document changes** in git commits

## Troubleshooting

### Permission Denied
Ensure you have appropriate RBAC roles:
- Contributor (for resource management)
- Key Vault Administrator (for Key Vault)
- Storage Blob Data Contributor (for Storage)

### Resource Not Found
Check:
1. Resource name spelling
2. Subscription selection
3. Resource not soft-deleted

### Fix Script Fails
Check:
1. Dependencies installed
2. Azure CLI logged in
3. Correct config.py values

## References

- [Azure Key Vault](https://docs.microsoft.com/azure/key-vault/)
- [Azure Storage](https://docs.microsoft.com/azure/storage/)
- [Azure App Service Configuration](https://docs.microsoft.com/azure/app-service/configure-common)
