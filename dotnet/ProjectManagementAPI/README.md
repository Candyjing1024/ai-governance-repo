# ProjectManagementAPI

API for managing Azure AI Foundry accounts (AIServices resources) and projects via ARM REST API (`management.azure.com`).

**Port:** `http://localhost:5218` | **Swagger:** `http://localhost:5218/swagger`

## Configuration

| Key | Description |
|-----|-------------|
| `AzureFoundry:SubscriptionId` | Azure subscription ID |
| `AzureFoundry:TenantId` | Azure AD tenant ID |
| `AzureFoundry:ResourceGroup` | Target resource group |
| `AzureFoundry:AccountName` | Foundry account name |
| `AzureFoundry:ApiVersion` | ARM API version (default: `2025-12-01`) |
| `AzureUrls:ArmBaseUrl` | ARM management endpoint (default: `https://management.azure.com`) |
| `AzureUrls:ArmScope` | ARM token scope (default: `https://management.azure.com/.default`) |

Authentication uses `DefaultAzureCredential` with explicit `TenantId`.

---

## Foundry Accounts Endpoints (`/api/foundry/accounts`)

Manage CognitiveServices accounts (`kind=AIServices`) — the Foundry V2 resource. Resource group and account name come from configuration.

### GET `/api/foundry/accounts`

List all Foundry accounts in the configured resource group.

**Response:** `200 OK` — `FoundryAccountListResponse`

---

### GET `/api/foundry/accounts/current`

Get the configured Foundry account (kind, location, endpoint, managed identity).

**Response:** `200 OK` — `FoundryAccount` | `404 Not Found`

---

### POST `/api/foundry/accounts`

Create the Foundry account. Idempotent — returns existing if found. Auto-enables `allowProjectManagement` if the account exists but has it disabled. Polls `provisioningState` until complete.

**Request Body:**

```json
{
  "location": "eastus",
  "sku": "S0",
  "allowProjectManagement": true,
  "publicNetworkAccess": "Enabled"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `location` | Yes | — | Azure region |
| `sku` | No | `S0` | SKU name |
| `allowProjectManagement` | No | `true` | Enable project management on the account |
| `publicNetworkAccess` | No | `Enabled` | Network access setting |

**Response:** `200 OK` — `FoundryAccount`

---

### PATCH `/api/foundry/accounts`

Update account properties (e.g. enable `allowProjectManagement`). Polls until complete.

**Request Body:**

```json
{
  "allowProjectManagement": true,
  "publicNetworkAccess": "Enabled"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `allowProjectManagement` | No | Enable/disable project management |
| `publicNetworkAccess` | No | `Enabled` or `Disabled` |

**Response:** `200 OK` — `FoundryAccount`

---

### DELETE `/api/foundry/accounts`

Delete the configured Foundry account.

**Response:** `204 No Content` | `404 Not Found`

---

## Foundry Projects Endpoints (`/api/foundry/projects`)

Manage projects under the configured Foundry account (`Microsoft.CognitiveServices/accounts/projects`).

### GET `/api/foundry/projects`

List all projects under the configured Foundry account.

**Response:** `200 OK` — `FoundryProjectListResponse`

---

### GET `/api/foundry/projects/{projectName}`

Get a specific project (endpoints, managed identity, provisioning state).

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `projectName` | Path | Yes | `poc-01-project` |

**Response:** `200 OK` — `FoundryProject` | `404 Not Found`

---

### POST `/api/foundry/projects`

Create a project under the configured Foundry account. Idempotent — returns existing if found. Polls `provisioningState` until complete.

**Request Body:**

```json
{
  "projectName": "poc-01-project",
  "location": "eastus",
  "displayName": "My POC Project",
  "description": "Foundry V2 E2E POC project"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `projectName` | Yes | — | ARM resource name for the project |
| `location` | Yes | — | Azure region |
| `displayName` | No | Same as `projectName` | Friendly display name |
| `description` | No | Auto-generated | Project description (max 2000 chars) |

**Response:** `200 OK` — `FoundryProject`

---

### PATCH `/api/foundry/projects/{projectName}`

Update a project's properties (displayName, description). Verifies the project exists first.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `projectName` | Path | Yes | `poc-01-project` |

**Request Body:**

```json
{
  "displayName": "Updated Display Name",
  "description": "Updated project description"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `displayName` | No | Friendly display name (max 500 chars) |
| `description` | No | Project description (max 2000 chars) |

**Response:** `200 OK` — `FoundryProject` | `404 Not Found`

---

### DELETE `/api/foundry/projects/{projectName}`

Delete a project from the configured Foundry account.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `projectName` | Path | Yes | `poc-01-project` |

**Response:** `204 No Content` | `404 Not Found`
