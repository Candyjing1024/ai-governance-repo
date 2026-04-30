# UserManagementAPI

API for managing Entra ID security groups and user membership via Microsoft Graph REST API. Supports the user access management workflow (Part B — T13–T16) for controlling access to AI model deployments.

**Port:** `http://localhost:5145` | **Swagger:** `http://localhost:5145/swagger`

## Configuration

| Key | Description | Example |
|-----|-------------|---------|
| `AzureAd:TenantId` | Entra ID tenant ID | `ef63a63b-...` |
| `MicrosoftGraph:BaseUrl` | Graph API base URL | `https://graph.microsoft.com/v1.0` |
| `MicrosoftGraph:Scope` | Graph API token scope | `https://graph.microsoft.com/.default` |

Authentication uses `DefaultAzureCredential` with explicit `TenantId`.

## Prerequisites

- User authenticated via Azure CLI (`az login`)
- Service principal / app registration with **Graph API application permissions**:
  - `Group.ReadWrite.All` — create groups, add/remove members
  - `User.Read.All` — look up users by email

---

## Users Endpoints (`/api/users`)

### GET `/api/users/health`

Health check endpoint.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "service": "UserManagementAPI"
}
```

---

### GET `/api/users/{email}`

Look up an Entra ID user by email or UPN (T14A). Tries direct UPN lookup first; falls back to `$filter=mail eq '...'` for guest/external users.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `email` | Path | Yes | `developer@company.com` |

**Response:** `200 OK` — `EntraUser` | `404 Not Found`

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "displayName": "Developer Name",
  "userPrincipalName": "developer@company.com",
  "mail": "developer@company.com"
}
```

---

## Groups Endpoints (`/api/groups`)

### POST `/api/groups`

Create an Entra ID security group (T13). Idempotent — returns existing group if a group with the same `displayName` already exists.

**Request Body:**

```json
{
  "displayName": "sg-customer-support-users",
  "description": "Users authorized to access gpt-4o-mini-prod deployment"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `displayName` | Yes | — | Group display name (max 256 chars) |
| `description` | No | Auto-generated | Group description (max 500 chars) |

**Response:** `201 Created` / `200 OK` (if already exists) — `EntraGroup`

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "displayName": "sg-customer-support-users",
  "description": "Users authorized to access gpt-4o-mini-prod deployment",
  "securityEnabled": true,
  "mailEnabled": false,
  "mailNickname": "sg-customer-support-users"
}
```

---

### GET `/api/groups/{groupId}`

Get an Entra ID security group by its object ID.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `groupId` | Path | Yes | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |

**Response:** `200 OK` — `EntraGroup` | `404 Not Found`

---

### GET `/api/groups/{groupId}/members`

List all members of a security group (T16).

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `groupId` | Path | Yes | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |

**Response:** `200 OK` — `GroupMember[]`

```json
[
  {
    "id": "a1b2c3d4-...",
    "displayName": "Developer Name",
    "userPrincipalName": "developer@company.com",
    "mail": "developer@company.com"
  }
]
```

---

### POST `/api/groups/{groupId}/members`

Add a user to a security group by email (T14). Automatically resolves the user's object ID via Graph API (T14A), then adds them as a member (T14B). Idempotent — returns success if the user is already a member.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `groupId` | Path | Yes | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |

**Request Body:**

```json
{
  "userEmail": "developer@company.com"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `userEmail` | Yes | User's email address (valid email format required) |

**Response:** `204 No Content` | `404 Not Found` (user or group not found)

---

### DELETE `/api/groups/{groupId}/members/{userId}`

Remove a user from a security group (T15). Idempotent — returns success if the user is not a member.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `groupId` | Path | Yes | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |
| `userId` | Path | Yes | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |

**Response:** `204 No Content` | `404 Not Found` (group not found)

---

## Spec Reference

This API implements Part B tasks T13–T16 from the Model Deployment Lifecycle specification:

| Task | Endpoint | Description |
|------|----------|-------------|
| T13 | `POST /api/groups` | Create Entra security group |
| T14A | `GET /api/users/{email}` | Look up user by email |
| T14B | `POST /api/groups/{groupId}/members` | Add user to group |
| T15 | `DELETE /api/groups/{groupId}/members/{userId}` | Remove user from group |
| T16 | `GET /api/groups/{groupId}/members` | List group members |

---

## E2E Test Results (2026-04-27)

All tests run against live Entra ID tenant `kiran11mroutlook.onmicrosoft.com`.

### Test Users Created

| User | UPN | Object ID |
|------|-----|-----------|
| Alice Admin | `alice.admin@kiran11mroutlook.onmicrosoft.com` | `395d51f3-0f49-432d-b833-f18876ec67fe` |
| Bob Developer | `bob.developer@kiran11mroutlook.onmicrosoft.com` | `199b5d9d-17d8-4b9e-a5bb-0961db87c329` |
| Carol Reviewer | `carol.reviewer@kiran11mroutlook.onmicrosoft.com` | `9651da32-ece0-455e-983d-bc36850d2126` |
| Dave Viewer | `dave.viewer@kiran11mroutlook.onmicrosoft.com` | *(not looked up — available for future tests)* |

### Test Results

| # | Test | Method | Endpoint | Status | Result |
|---|------|--------|----------|--------|--------|
| 1 | Health check | GET | `/api/users/health` | `200` | `{"status":"healthy","service":"UserManagementAPI"}` |
| 2 | Lookup user (Alice) | GET | `/api/users/alice.admin@...` | `200` | Returned `EntraUser` with correct ID and UPN |
| 3 | Lookup user (Bob) | GET | `/api/users/bob.developer@...` | `200` | Returned `EntraUser` with correct ID and UPN |
| 4 | Lookup non-existent user | GET | `/api/users/nonexistent@...` | `404` | `"User 'nonexistent@...' not found by UPN or mail."` |
| 5 | Create security group | POST | `/api/groups` | `201` | Created `AI-Platform-Developers` (ID: `cdfa3078-ae6f-4830-950a-137a76d827de`) |
| 6 | Create group (idempotent) | POST | `/api/groups` | `200` | Returned existing group — same ID confirmed |
| 7 | Get group by ID | GET | `/api/groups/cdfa3078-...` | `200` | Returned correct group with `securityEnabled: true` |
| 8 | Add member (Alice) | POST | `/api/groups/{id}/members` | `204` | Added successfully |
| 9 | Add member (Bob) | POST | `/api/groups/{id}/members` | `204` | Added successfully |
| 10 | Add member (Carol) | POST | `/api/groups/{id}/members` | `204` | Added successfully |
| 11 | List members | GET | `/api/groups/{id}/members` | `200` | Returned 3 members (Alice, Bob, Carol) |
| 12 | Remove member (Carol) | DELETE | `/api/groups/{id}/members/{userId}` | `204` | Removed successfully |
| 13 | List members (post-remove) | GET | `/api/groups/{id}/members` | `200` | Returned 2 members (Alice, Bob) — Carol confirmed removed |

**All 13 tests passed. No bugs found.**
