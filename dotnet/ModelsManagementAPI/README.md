# ModelsManagementAPI

API for managing Azure AI Foundry model deployments — both direct ARM operations and an approval-based workflow backed by Cosmos DB.

**Port:** `http://localhost:5076` | **Swagger:** `http://localhost:5076/swagger`

## Configuration

| Key | Description |
|-----|-------------|
| `AzureFoundry:SubscriptionId` | Azure subscription ID |
| `AzureFoundry:TenantId` | Azure AD tenant ID |
| `AzureFoundry:ResourceGroup` | Target resource group |
| `AzureFoundry:AccountName` | Foundry account name |
| `AzureFoundry:ApiVersion` | ARM API version (default: `2025-12-01`) |
| `CosmosDb:AccountEndpoint` | Cosmos DB endpoint |
| `CosmosDb:AccountKey` | Cosmos DB key |
| `CosmosDb:DatabaseName` | Database name |
| `CosmosDb:ContainerName` | Container name |
| `AzureUrls:ArmBaseUrl` | ARM management endpoint (default: `https://management.azure.com`) |
| `AzureUrls:ArmScope` | ARM token scope (default: `https://management.azure.com/.default`) |

Authentication to Azure ARM uses `DefaultAzureCredential` with explicit `TenantId`.

---

## Foundry-Direct Endpoints (`/api/foundry/models`)

All data is fetched from / written to Azure AI Foundry directly via ARM REST API. Resource group and account name come from configuration.

### GET `/api/foundry/models`

List all model deployments on the configured Foundry account.

**Response:** `200 OK` — `FoundryDeploymentListResponse`

---

### GET `/api/foundry/models/{deploymentName}`

Get a specific model deployment.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `deploymentName` | Path | Yes | `gpt4o-production` |

**Response:** `200 OK` — `FoundryDeployment` | `404 Not Found`

---

### POST `/api/foundry/models`

Create a model deployment directly on Azure AI Foundry. Idempotent — returns existing deployment if already created. Polls `provisioningState` until complete.

**Request Body:**

```json
{
  "modelName": "gpt-4o",
  "deploymentName": "gpt4o-production",
  "modelVersion": "2024-08-06",
  "skuName": "GlobalStandard",
  "skuCapacity": 10
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `modelName` | Yes | — | Model name (e.g. `gpt-4o`) |
| `deploymentName` | Yes | — | ARM deployment name |
| `modelVersion` | No | `""` | Model version |
| `skuName` | No | `GlobalStandard` | SKU name |
| `skuCapacity` | No | `10` | SKU capacity (1–1000) |

**Response:** `200 OK` — `FoundryDeployment`

---

### DELETE `/api/foundry/models/{deploymentName}`

Delete a model deployment from Azure AI Foundry.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `deploymentName` | Path | Yes | `gpt4o-production` |

**Response:** `204 No Content` | `404 Not Found`

---

### PATCH `/api/foundry/models/{deploymentName}`

Update an existing model deployment (SKU name or capacity). Fetches the existing deployment, merges changes, sends PUT to ARM, and polls until complete.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `deploymentName` | Path | Yes | `gpt4o-production` |

**Request Body:**

```json
{
  "skuName": "GlobalStandard",
  "skuCapacity": 20
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `skuName` | No | New SKU name |
| `skuCapacity` | No | New SKU capacity (1–1000) |

**Response:** `200 OK` — `FoundryDeployment` | `404 Not Found`

---

## Deployment Requests Endpoints (`/api/DeploymentRequests`)

Approval-based workflow. Requests are stored in Cosmos DB with status `requested_pending_approval`. Admin approves or rejects. Approval triggers Foundry deployment (T7), polls until complete (T8), then updates the document with deployment result (T9).

### Status Lifecycle (R3)

| Status | Description |
|--------|-------------|
| `requested_pending_approval` | Initial state — request submitted, awaiting admin review |
| `approved` | Admin approved — Foundry deployment in progress |
| `rejected` | Admin rejected with optional reason |
| `deployed` | Foundry deployment succeeded — `deploymentId` populated |
| `access_granted` | Entra group created, user added, APIM policy updated (via UserManagementAPI + AIGatewayManagementAPI) |
| `failed` | Foundry deployment failed |
| `revoked` | Access removed — group removed from APIM policy |

### Cosmos Document Schema

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `id` | string | Auto | UUID, auto-generated |
| `modelName` | string | Request | OpenAI model name |
| `deploymentName` | string | Request | Desired deployment name in Foundry |
| `projectName` | string | Request | Foundry project name (partition key) |
| `region` | string | Request | Azure region |
| `businessJustification` | string | Request | Why the model is needed |
| `skuName` | string | Request | SKU name (default: GlobalStandard) |
| `skuCapacity` | int | Request | SKU capacity (default: 10) |
| `modelVersion` | string | Request | Model version |
| `requestGroup` | string | Request | Security group name for model access |
| `requestUser` | string | Request | User email to add to the group |
| `status` | string | System | Workflow status (see R3 above) |
| `createdAt` | datetime | System | When request was submitted |
| `createdBy` | string | System | Who submitted the request |
| `reviewedBy` | string? | Admin | Admin who reviewed (null until reviewed) |
| `reviewedAt` | datetime? | Admin | When reviewed (null until reviewed) |
| `rejectionReason` | string? | Admin | Reason for rejection |
| `deployedAt` | datetime? | System | When Foundry deployment completed |
| `deploymentId` | string? | System | Foundry deployment name after deploy (T9) |
| `groupId` | string? | System | *(Part B)* Entra group object ID |
| `policyUpdated` | bool | System | *(Part B)* Whether APIM policy was updated |

> **Note:** `foundry_resource`, `resource_group`, and `tpm` are not per-request fields — they come from `appsettings.json` configuration.

---

### POST `/api/DeploymentRequests`

Submit a new deployment request (status = `requested_pending_approval`).

**Request Body:**

```json
{
  "modelName": "gpt-5.4-mini",
  "deploymentName": "gpt-5.4-mini-production",
  "projectName": "poc-02-project",
  "region": "eastus",
  "businessJustification": "Required for claims processing automation.",
  "skuName": "GlobalStandard",
  "skuCapacity": 10,
  "modelVersion": "2026-03-17",
  "requestGroup": "sg-claims-ai-users",
  "requestUser": "developer@company.com"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `modelName` | Yes | — | Model name |
| `deploymentName` | Yes | — | Deployment name |
| `projectName` | Yes | — | Foundry project name (also used as Cosmos partition key) |
| `region` | Yes | — | Azure region |
| `businessJustification` | Yes | — | Business reason for request |
| `skuName` | No | `GlobalStandard` | SKU name |
| `skuCapacity` | No | `10` | SKU capacity |
| `modelVersion` | No | `""` | Model version |
| `requestGroup` | Yes | — | Security group name for model access |
| `requestUser` | Yes | — | User email to add to the group |

**Response:** `201 Created` — `ModelDeploymentRequest`

---

### GET `/api/DeploymentRequests`

Retrieve all deployment requests (ordered by `createdAt` descending).

**Response:** `200 OK` — `ModelDeploymentRequest[]`

---

### GET `/api/DeploymentRequests/{id}`

Retrieve a specific deployment request by ID.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `id` | Path | Yes | `abc-123-def` |
| `projectName` | Query | Yes | `Claims-AI` |

**Response:** `200 OK` — `ModelDeploymentRequest` | `404 Not Found`

---

### PUT `/api/DeploymentRequests/{id}/approve`

Approve a pending request. Executes the following chain:

1. **T5** — Sets status to `approved`, records reviewer
2. **T7** — Deploys model to Azure AI Foundry via ARM REST API
3. **T8** — Polls `provisioningState` until `Succeeded` or `Failed` (up to ~10 min)
4. **T9** — Updates Cosmos document: status → `deployed`, persists `deploymentId` and `deployedAt`

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `id` | Path | Yes | `abc-123-def` |
| `projectName` | Query | Yes | `Claims-AI` |

**Request Body:**

```json
{
  "reviewedBy": "admin@contoso.com"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `reviewedBy` | Yes | Reviewer identity |

**Response:** `200 OK` — `ModelDeploymentRequest` (status=`deployed`, `deploymentId` populated) | `404 Not Found` | `400 Bad Request` (if not `requested_pending_approval`)

---

### PUT `/api/DeploymentRequests/{id}/reject`

Reject a pending request with an optional reason.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `id` | Path | Yes | `abc-123-def` |
| `projectName` | Query | Yes | `Claims-AI` |

**Request Body:**

```json
{
  "reviewedBy": "admin@contoso.com",
  "rejectionReason": "Insufficient business justification."
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `reviewedBy` | Yes | Reviewer identity |
| `rejectionReason` | No | Reason for rejection (max 2000 chars) |

**Response:** `200 OK` — `ModelDeploymentRequest` (status=`rejected`) | `404 Not Found` | `400 Bad Request` (if not `requested_pending_approval`)

