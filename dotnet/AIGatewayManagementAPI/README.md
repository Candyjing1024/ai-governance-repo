# AIGatewayManagementAPI

API for managing Azure API Management (APIM) as an AI Gateway for Azure AI Foundry. Handles API creation, JWT + MI policy configuration, and RBAC role assignments — all via ARM REST API.

**Port:** `http://localhost:5099`

## Configuration

| Setting | Description | Example |
|---------|-------------|---------|
| `AzureFoundry:SubscriptionId` | Azure subscription ID | `c7a9455e-...` |
| `AzureFoundry:TenantId` | Entra ID tenant | `ef63a63b-...` |
| `AzureFoundry:ResourceGroup` | Foundry resource group | `ai-foundry-poc-01` |
| `AzureFoundry:AccountName` | Foundry account name | `poc-01-foundry` |
| `AzureFoundry:ApiVersion` | Foundry ARM API version | `2025-12-01` |
| `AzureApim:ResourceGroup` | APIM resource group | `ai-foundry-poc-01` |
| `AzureApim:ServiceName` | APIM instance name | `poc-02-apim` |
| `AzureApim:ApiVersion` | APIM ARM API version | `2024-06-01-preview` |
| `AzureUrls:ArmBaseUrl` | ARM management endpoint | `https://management.azure.com` |
| `AzureUrls:ArmScope` | ARM token scope | `https://management.azure.com/.default` |
| `AzureUrls:LoginBaseUrl` | Entra ID login endpoint | `https://login.microsoftonline.com` |

## Prerequisites

- APIM instance already provisioned (Developer/Basic/Standard/Premium SKU)
- System-assigned managed identity enabled on APIM
- User authenticated via Azure CLI (`az login`)

---

## APIM Instance

### GET `/api/gateway/apim`

Get APIM instance details including SKU, managed identity principal ID, and gateway URL.

**Response:** `200 OK` — `ApimServiceInfo`

---

## APIs

### GET `/api/gateway/apis`

List all APIs configured in APIM.

**Response:** `200 OK` — `ApimApiListResponse`

---

### GET `/api/gateway/apis/{apiId}`

Get a specific API.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `apiId` | Path | Yes | `foundry-api` |

**Response:** `200 OK` — `ApimApi` | `404 Not Found`

---

### POST `/api/gateway/apis`

Create a Foundry API in APIM with default operations. Tries `azure-ai-foundry` type first; falls back to standard HTTP API with manually added operations (chat completions, completions, embeddings, image generations, responses, etc.).

**Request Body:**

```json
{
  "displayName": "Foundry API",
  "apiId": "foundry-api",
  "path": "foundry"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `displayName` | No | `Foundry API` | API display name |
| `apiId` | No | `foundry-api` | API identifier in APIM |
| `path` | No | `foundry` | URL path prefix |

**Response:** `201 Created` — `ApimApi`

---

### DELETE `/api/gateway/apis/{apiId}`

Delete an API from APIM.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `apiId` | Path | Yes | `foundry-api` |

**Response:** `204 No Content` | `404 Not Found`

---

## Operations

### GET `/api/gateway/apis/{apiId}/operations`

List all operations for an API.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `apiId` | Path | Yes | `foundry-api` |

**Response:** `200 OK` — `ApimOperationListResponse`

---

## Policies

### GET `/api/gateway/apis/{apiId}/policy`

Get the current inbound policy XML for an API.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `apiId` | Path | Yes | `foundry-api` |

**Response:** `200 OK` — `ApimPolicyResponse`

---

### PUT `/api/gateway/apis/{apiId}/policy`

Apply JWT validation + Managed Identity token swap policy. Generates full XML policy from structured input.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `apiId` | Path | Yes | `foundry-api` |

**Request Body:**

```json
{
  "audience": "YOUR_APP_CLIENT_ID",
  "allowedGroups": ["group-object-id-1", "group-object-id-2"],
  "foundryEndpoint": null
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `audience` | Yes | Entra ID app registration client ID |
| `allowedGroups` | No | AD group object IDs for authorization (403 if user not in any group) |
| `foundryEndpoint` | No | Foundry endpoint URL (auto-fetched from account if omitted) |

**Policy applies:**
1. JWT validation (Entra ID v1/v2 tokens)
2. Group membership check (if groups specified)
3. MI token swap (user token → `cognitiveservices.azure.com` MI token)
4. Backend routing to Foundry endpoint

**Response:** `200 OK` — `ApimPolicyResponse`

---

## Policy Group Management (Part B — T17–T19)

Manage security group IDs in the APIM JWT policy's `<claim name="groups">` section using read-modify-write operations.

### GET `/api/gateway/apis/{apiId}/policy/groups`

List the group IDs currently in the APIM JWT policy for an API (T18).

| Parameter | Location | Required | Example |
|-----------|----------|----------|--------|
| `apiId` | Path | Yes | `foundry-api` |

**Response:** `200 OK` — `string[]`

```json
["9abb0b3a-8857-4164-a34f-5808b0df6693", "f47ac10b-58cc-4372-a567-0e02b2c3d479"]
```

---

### PUT `/api/gateway/apis/{apiId}/policy/groups/{groupId}`

Add a security group to the APIM JWT policy (T17 — grant access). Performs a read-modify-write: fetches current policy XML, inserts the group ID as a new `<value>` under `<claim name="groups">`, and PUTs the updated policy back. Idempotent — returns existing policy if group is already present.

| Parameter | Location | Required | Example |
|-----------|----------|----------|--------|
| `apiId` | Path | Yes | `foundry-api` |
| `groupId` | Path | Yes | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |

**Response:** `200 OK` — `ApimPolicyResponse` | `400 Bad Request` (no groups claim section found)

---

### DELETE `/api/gateway/apis/{apiId}/policy/groups/{groupId}`

Remove a security group from the APIM JWT policy (T19 — revoke access). Performs a read-modify-write: fetches current policy XML, removes the `<value>` element matching the group ID, and PUTs the updated policy back. Idempotent — returns existing policy if group is not found.

| Parameter | Location | Required | Example |
|-----------|----------|----------|--------|
| `apiId` | Path | Yes | `foundry-api` |
| `groupId` | Path | Yes | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |

**Response:** `200 OK` — `ApimPolicyResponse`

> **Warning:** If you remove ALL groups from the policy, the `<required-claims>` check will reject everyone. Keep at least one group or remove the entire group validation block via `PUT /api/gateway/apis/{apiId}/policy`.

---

## RBAC

### GET `/api/gateway/rbac`

List role assignments on the Foundry scope.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `projectName` | Query | No | `poc-02-project` |

**Response:** `200 OK` — `RoleAssignmentListResponse`

---

### POST `/api/gateway/rbac`

Assign a role to a principal on the Foundry scope. Set `useApimIdentity: true` to auto-fetch the APIM managed identity principal ID.

**Request Body:**

```json
{
  "principalId": "group-or-user-object-id",
  "principalType": "Group",
  "roleName": "Cognitive Services OpenAI User",
  "projectName": null,
  "useApimIdentity": false
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `principalId` | Conditional | Principal object ID (not needed if `useApimIdentity` is true) |
| `principalType` | Yes | `ServicePrincipal`, `Group`, or `User` |
| `roleName` | Yes | Role name (see supported roles below) |
| `projectName` | No | Scope to project level (default: account level) |
| `useApimIdentity` | No | Auto-fetch APIM MI principal ID |

**Supported roles:**
- `Cognitive Services OpenAI User`
- `Cognitive Services User`
- `Azure AI Developer`

**Response:** `200 OK` — `RoleAssignment` (returns existing if already assigned)

---

### DELETE `/api/gateway/rbac/{assignmentName}`

Remove a role assignment by its name (GUID).

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `assignmentName` | Path | Yes | `abc-123-def` (GUID) |
| `projectName` | Query | No | `poc-02-project` |

**Response:** `204 No Content`

---

## 3-Step APIM Setup Walkthrough

Complete setup to secure Azure AI Foundry behind APIM with JWT authentication and Managed Identity credential swap.

### Step 1 — RBAC: Grant APIM Access to Foundry

Assign roles to APIM's managed identity so it can call Foundry models on behalf of users.

#### 1a. Assign "Cognitive Services OpenAI User"

```
POST http://localhost:5099/api/gateway/rbac
Content-Type: application/json
```
```json
{
  "principalId": "bfd8a8fb-ef00-4f56-bc2b-fb03adf9639e",
  "principalType": "ServicePrincipal",
  "roleName": "Cognitive Services OpenAI User",
  "useApimIdentity": false
}
```

**ARM call:** PUT to role assignments on Foundry account scope with role definition ID `5e0bd9bd-7b93-4f28-af87-19fc36ad61bd`.

#### 1b. Assign "Cognitive Services User"

```
POST http://localhost:5099/api/gateway/rbac
Content-Type: application/json
```
```json
{
  "principalId": "bfd8a8fb-ef00-4f56-bc2b-fb03adf9639e",
  "principalType": "ServicePrincipal",
  "roleName": "Cognitive Services User",
  "useApimIdentity": false
}
```

**ARM call:** Role definition ID `a97b65f3-24c7-4388-baec-2e87135dc908`.

---

### Step 2 — API: Create Foundry API in APIM

```
POST http://localhost:5099/api/gateway/apis
Content-Type: application/json
```
```json
{
  "displayName": "Foundry API",
  "apiId": "foundry-api",
  "path": "foundry"
}
```

Tries `azure-ai-foundry` API type first; falls back to standard HTTP API with 7 default operations:

| Operation ID | Method | URL Template |
|---|---|---|
| `chat-completions` | POST | `/openai/deployments/*/chat/completions` |
| `completions` | POST | `/openai/deployments/*/completions` |
| `embeddings` | POST | `/openai/deployments/*/embeddings` |
| `image-generations` | POST | `/openai/deployments/*/images/generations` |
| `responses` | POST | `/openai/responses` |
| `list-models` | GET | `/openai/models` |
| `list-deployments` | GET | `/openai/deployments` |

**ARM call:** PUT to `.../apis/foundry-api` then PUT for each operation under `.../apis/foundry-api/operations/{operationId}`.

---

### Step 3 — Policy: JWT Validation + MI Token Swap

Requires an **Entra ID App Registration** to provide the JWT audience.

```
PUT http://localhost:5099/api/gateway/apis/foundry-api/policy
Content-Type: application/json
```
```json
{
  "audience": "23225605-2a71-4b8a-89c1-110885e70cf5"
}
```

**Generated policy XML:**

```xml
<policies>
  <inbound>
    <base />

    <!-- 1. Validate JWT from Entra ID (v1 + v2 tokens) -->
    <validate-jwt header-name="Authorization"
                  failed-validation-httpcode="401"
                  failed-validation-error-message="Unauthorized"
                  require-expiration-time="true"
                  require-scheme="Bearer"
                  require-signed-tokens="true">
      <openid-config url="https://login.microsoftonline.com/{tenantId}/v2.0/.well-known/openid-configuration" />
      <audiences>
        <audience>{clientId}</audience>
        <audience>api://{clientId}</audience>
      </audiences>
      <issuers>
        <issuer>https://sts.windows.net/{tenantId}/</issuer>
        <issuer>https://login.microsoftonline.com/{tenantId}/v2.0</issuer>
      </issuers>
    </validate-jwt>

    <!-- 2. Swap user token for APIM Managed Identity token -->
    <authentication-managed-identity
      resource="https://cognitiveservices.azure.com"
      output-token-variable-name="managed-id-token" />
    <set-header name="Authorization" exists-action="override">
      <value>@("Bearer " + (string)context.Variables["managed-id-token"])</value>
    </set-header>
    <set-header name="Ocp-Apim-Subscription-Key" exists-action="delete" />

    <!-- 3. Route to Foundry backend -->
    <set-backend-service base-url="https://poc-01-foundry.cognitiveservices.azure.com/" />
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
  <on-error><base /></on-error>
</policies>
```

---

### Pre-requisite: Entra ID App Registration

Create the app registration that provides the JWT audience for Step 3.

```bash
# Create app registration
az ad app create --display-name "poc-02-apim-gateway" --sign-in-audience "AzureADMyOrg"

# Set identifier URI
az ad app update --id {appId} --identifier-uris "api://{appId}"

# Create service principal
az ad sp create --id {appId}

# Add and consent User.Read
az ad app permission add --id {appId} --api 00000003-0000-0000-c000-000000000000 --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope
az ad app permission grant --id {appId} --api 00000003-0000-0000-c000-000000000000 --scope "User.Read"

# Add user_impersonation scope + pre-authorize Azure CLI (via Graph API PATCH)
# Scope ID: generate a new GUID
# Azure CLI app ID: 04b07795-8ddb-461a-bbee-02f9e1bf7b46
```

**Result:** App Registration `poc-02-apim-gateway` — Client ID `23225605-2a71-4b8a-89c1-110885e70cf5`

---

### E2E Test

Get a token and call a deployed model through the APIM gateway:

```bash
# Get token
az account get-access-token --resource "api://23225605-2a71-4b8a-89c1-110885e70cf5" --query accessToken -o tsv
```

```
POST https://poc-02-apim.azure-api.net/foundry/openai/deployments/gpt-5.4-mini-production/chat/completions?api-version=2024-12-01-preview
Authorization: Bearer {token}
Content-Type: application/json
```
```json
{
  "messages": [{"role": "user", "content": "Say hello in one sentence."}],
  "max_completion_tokens": 50
}
```

**Response:** `200 OK` — Model `gpt-5.4-mini-2026-03-17` replies successfully.

**Flow:** Client → JWT auth → APIM Gateway → MI credential swap → Azure AI Foundry → Model response

---

## Automatic Model Availability

Any model deployed in Foundry under the `poc-01-foundry` account is **immediately accessible** through the APIM gateway — no additional APIM configuration needed.

This works because:

1. **Wildcard operations** — URL templates use `*` (e.g., `/openai/deployments/*/chat/completions`), so any deployment name is matched
2. **Account-level RBAC** — The MI roles are assigned on the Foundry account scope, covering all projects and deployments under it
3. **Backend routing** — All requests are forwarded to `https://poc-01-foundry.cognitiveservices.azure.com/`, which resolves any deployment by name

For example, if you deploy a new model called `gpt-4o-finance`, it's immediately callable at:

```
POST https://poc-02-apim.azure-api.net/foundry/openai/deployments/gpt-4o-finance/chat/completions?api-version=2024-12-01-preview
Authorization: Bearer <entra-token>
```

> **Note:** The only scenario requiring extra configuration is adding a **second Foundry account** — that would need a separate API or backend routing rule.

---

## E2E Test Results (2026-04-27)

All tests run against live APIM instance `aistudio-apim-poc` (Developer SKU, East US) with SystemAssigned managed identity.

### Test Results

| # | Test | Method | Endpoint | Status | Result |
|---|------|--------|----------|--------|--------|
| 1 | Get APIM instance | GET | `/api/gateway/apim` | `200` | SKU=Developer, MI principal=`fda6d68c-...`, gateway=`https://aistudio-apim-poc.azure-api.net` |
| 2 | List APIs | GET | `/api/gateway/apis` | `200` | 4 existing APIs listed (azure-openai-api, claimsbot-api, echo-api, test-01) |
| 3 | Create Foundry API | POST | `/api/gateway/apis` | `201` | Created `e2e-test-api` with serviceUrl pointing to Foundry |
| 4 | Get API by ID | GET | `/api/gateway/apis/e2e-test-api` | `200` | Returned correct API details |
| 5 | List operations | GET | `/api/gateway/apis/e2e-test-api/operations` | `200` | 8 operations auto-created (chat-completions, completions, embeddings, agents, etc.) |
| 6 | Set JWT policy | PUT | `/api/gateway/apis/e2e-test-api/policy` | `200` | JWT validation + group check + MI token swap policy applied |
| 7 | Get policy | GET | `/api/gateway/apis/e2e-test-api/policy` | `200` | Full policy XML returned with correct audience and tenant |
| 8 | Get policy groups | GET | `/api/gateway/apis/e2e-test-api/policy/groups` | `200` | Returned `["cdfa3078-ae6f-4830-950a-137a76d827de"]` |
| 9 | Add group to policy | PUT | `/api/gateway/apis/{id}/policy/groups/{groupId}` | `200` | Added second group; verified 2 groups in policy |
| 10 | Remove group from policy | DELETE | `/api/gateway/apis/{id}/policy/groups/{groupId}` | `200` | Removed second group; verified 1 group remains |
| 11 | List RBAC assignments | GET | `/api/gateway/rbac` | `200` | Returned existing role assignments on Foundry scope |
| 12 | Assign role (APIM MI) | POST | `/api/gateway/rbac` | `200` | Assigned Cognitive Services User to APIM MI (principal `fda6d68c-...`) |
| 13 | Delete role assignment | DELETE | `/api/gateway/rbac/{name}` | `204` | Removed the test role assignment |
| 14 | Delete test API (cleanup) | DELETE | `/api/gateway/apis/e2e-test-api` | `204` | Cleaned up test API from APIM |

**All 14 tests passed. No bugs found.**
