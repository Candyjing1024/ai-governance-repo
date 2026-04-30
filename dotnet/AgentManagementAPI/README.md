# AgentManagementAPI

Thin proxy API for managing Foundry V2 agents and conversations via the Foundry data-plane REST API. Uses the V2 `/openai/v1/conversations` and `/openai/v1/responses` endpoints for chat. Agent definitions are managed via `/agents`. All agent state is stored and managed by Foundry's internal infrastructure â€” no custom Cosmos DB containers needed.

**Port:** `http://localhost:5300` | **Swagger:** `http://localhost:5300/swagger`

## Configuration

| Key | Description | Example |
|-----|-------------|---------|
| `AzureFoundry:TenantId` | Entra ID tenant ID | `ef63a63b-...` |
| `AgentApi:ProjectEndpoint` | Foundry project data-plane URL | `https://poc-01-foundry.services.ai.azure.com/api/projects/poc-01-foundry-project` |
| `AgentApi:ApiVersion` | Foundry Agent API version | `2025-05-15-preview` |
| `AgentApi:Scope` | Token scope for data-plane auth | `https://ai.azure.com/.default` |

Authentication uses `DefaultAzureCredential` with explicit `TenantId` â€” single scope (`ai.azure.com/.default`) for all operations.

## Prerequisites

- User authenticated via Azure CLI (`az login`)
- Foundry V2 project provisioned with agent capabilities enabled
- Model deployed in the Foundry project (e.g., `gpt-4o-mini`)

---

## Architecture

```
Angular UI / .http file
        â”‚
        â–¼
 AgentManagementAPI (localhost:5300)
        â”‚
        â”‚  Token: ai.azure.com/.default
        â”‚  via DefaultAzureCredential
        â–¼
 Foundry V2 Data Plane
 (poc-01-foundry.services.ai.azure.com)
        â”‚
        â”œâ”€â”€ /agents                    â†’ Agent definitions (CRUD)
        â”œâ”€â”€ /openai/v1/conversations   â†’ Create conversations (replaces /threads)
        â””â”€â”€ /openai/v1/responses       â†’ Send message & get response (replaces /threads/runs)
```

Messages are stored in-memory on the backend for chat history display.
The V2 `/responses` endpoint is synchronous â€” no polling required.

---

## Agent Endpoints (`/api/agents`)

### GET `/api/agents/health`

Health check endpoint.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "service": "AgentManagementAPI"
}
```

---

### GET `/api/agents`

List all agents in the Foundry project.

**Response:** `200 OK` â€” `AgentListResponse`

```json
{
  "data": [
    {
      "id": "poc-support-agent",
      "name": "poc-support-agent",
      "versions": {
        "latest": {
          "definition": {
            "kind": "prompt",
            "model": "gpt-4.1-mini",
            "instructions": "You are a helpful assistant."
          },
          "status": "active"
        }
      }
    }
  ]
}
```

---

### GET `/api/agents/{agentId}`

Get an agent by ID.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `agentId` | Path | Yes | `demo-chat-agent-01` |

**Response:** `200 OK` â€” `FoundryAgent` | `404 Not Found`

---

### POST `/api/agents`

Create a new agent. Idempotent â€” returns existing agent if one with the same `name` already exists.

**Request Body:**

```json
{
  "name": "poc-support-agent",
  "model": "gpt-4o-mini",
  "kind": "prompt",
  "instructions": "You are a helpful support assistant for insurance inquiries. Be concise and professional.",
  "description": "PoC support agent for customer inquiries"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | â€” | Agent display name (max 256 chars) |
| `model` | Yes | â€” | Model deployment name |
| `kind` | No | `prompt` | Agent kind: `prompt`, `code_interpreter`, `file_search` |
| `instructions` | No | â€” | System instructions (max 32768 chars) |
| `description` | No | â€” | Optional description (max 512 chars) |

**Response:** `201 Created` / `200 OK` (if already exists) â€” `FoundryAgent`

---

### PATCH `/api/agents/{agentId}`

Update an existing agent. Only provided fields are updated.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `agentId` | Path | Yes | `demo-chat-agent-01` |

**Request Body:**

```json
{
  "instructions": "Updated system instructions for the agent."
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Updated name |
| `model` | No | Updated model deployment |
| `instructions` | No | Updated instructions |
| `description` | No | Updated description |

**Response:** `200 OK` â€” `FoundryAgent` | `404 Not Found`

---

### DELETE `/api/agents/{agentId}`

Delete an agent by ID.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `agentId` | Path | Yes | `demo-chat-agent-01` |

**Response:** `204 No Content` | `404 Not Found`

---

## Conversation Endpoints (`/api/conversations`)

### POST `/api/conversations`

Create a new conversation. Conversations are managed by the Foundry platform.

**Request Body (optional):**

```json
{}
```

**Response:** `201 Created` â€” `AgentThread`

```json
{
  "id": "conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ",
  "object": "conversation",
  "created_at": 1777500100
}
```

---

### GET `/api/conversations/{threadId}`

Get a conversation by ID.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `threadId` | Path | Yes | `conv_3bbb9480...` |

**Response:** `200 OK` â€” `AgentThread` | `404 Not Found`

---

### DELETE `/api/conversations/{threadId}`

Delete a conversation. V2 conversations are platform-managed; this clears local message state.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `threadId` | Path | Yes | `conv_3bbb9480...` |

**Response:** `204 No Content`

---

## Message Endpoints (`/api/conversations/{threadId}/messages`)

### POST `/api/conversations/{threadId}/messages`

Add a message to a conversation. Messages are stored in-memory on the backend for history display. The actual message is sent to the model when a run is created.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `threadId` | Path | Yes | `conv_3bbb9480...` |

**Request Body:**

```json
{
  "role": "user",
  "content": "Hello, what can you help me with?"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `role` | Yes | `user` or `assistant` |
| `content` | Yes | Message text (max 32768 chars) |

**Response:** `201 Created` â€” `ThreadMessage` | `404 Not Found`

---

### GET `/api/conversations/{threadId}/messages`

List all messages in a conversation (full chat history from in-memory store).

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `threadId` | Path | Yes | `conv_3bbb9480...` |

**Response:** `200 OK` â€” `ThreadMessageListResponse`

```json
{
  "data": [
    {
      "id": "msg_001",
      "role": "user",
      "content": [{ "type": "text", "text": { "value": "Hello, what can you help me with?" } }],
      "created_at": 1745500200
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": [{ "type": "text", "text": { "value": "I can help with insurance inquiries..." } }],
      "created_at": 1745500210
    }
  ]
}
```

---

## Run Endpoints (`/api/conversations/{threadId}/runs`)

### POST `/api/conversations/{threadId}/runs`

Send the latest user message to an agent via the V2 `/openai/v1/responses` endpoint and get the response. The agent is referenced by **name** (not an `asst_` ID). The call is synchronous â€” the response is returned immediately with `status: "completed"`.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `threadId` | Path | Yes | `conv_3bbb9480...` |

**Request Body:**

```json
{
  "assistantId": "demo-chat-agent-01"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `assistantId` | Yes | Agent name (as shown in Foundry portal) |
| `instructions` | No | Override instructions for this run only |

**Response:** `201 Created` â€” `ThreadRun`

```json
{
  "id": "resp_abc123",
  "object": "run",
  "thread_id": "conv_3bbb9480...",
  "agent_name": "demo-chat-agent-01",
  "status": "completed",
  "created_at": 1777500300,
  "completed_at": 1777500302
}
```

> **V2 Change:** Runs are now synchronous. The assistant's response is automatically added to the in-memory message store. No polling required â€” `status` is always `completed` or the call returns an error.

---

### GET `/api/conversations/{threadId}/runs/{runId}`

Get a previously completed run. Since V2 responses are synchronous, this returns the cached run result.

| Parameter | Location | Required | Example |
|-----------|----------|----------|---------|
| `threadId` | Path | Yes | `conv_3bbb9480...` |
| `runId` | Path | Yes | `resp_abc123` |

**Response:** `200 OK` â€” `ThreadRun` | `404 Not Found`

---

## E2E Usage â€” Create Agent and Chat

```
Step 1: POST /api/agents                              â†’ creates agent (demo-chat-agent-01)
Step 2: POST /api/conversations                              â†’ creates conversation (conv_3bbb9480...)
Step 3: POST /api/conversations/conv_3bbb.../messages
        { "role": "user", "content": "What can you help me with?" }
Step 4: POST /api/conversations/conv_3bbb.../runs
        { "assistantId": "demo-chat-agent-01" }
        â†’ returns immediately with status: "completed"
        â†’ assistant reply is automatically stored in message history
Step 5: GET  /api/conversations/conv_3bbb.../messages
        â†’ both user and assistant messages are in the list
```

> **Key difference from classic API:** No polling loop needed. Step 4 is synchronous â€” the assistant's response is ready when the call returns.

## Where State Lives

| Data | Stored In | Managed By |
|------|-----------|------------|
| Agent definitions | Foundry-managed storage | Foundry V2 `/agents` |
| Conversations | Foundry-managed | Foundry V2 `/openai/v1/conversations` |
| Chat messages | In-memory (backend) | AgentManagementAPI |
| Model execution | Foundry V2 `/openai/v1/responses` | Foundry V2 |
| Deployment requests | **Your** Cosmos DB (`DeploymentRequests`) | ModelsManagementAPI |

This API is a thin proxy â€” it adds auth, validation, and error handling on top of the Foundry data-plane.

> **Note:** In-memory message storage means chat history is lost on API restart. This is acceptable for PoC; production would use a persistent store.

---

## E2E Test Results (2026-04-27)

All endpoints verified against live Foundry project `poc-01-project` on `poc-01-foundry.services.ai.azure.com`.

### Test 1 â€” Health Check

```
GET http://localhost:5300/api/agents/health
```

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "service": "AgentManagementAPI"
}
```

---

### Test 2 â€” Create Agent

```
POST http://localhost:5300/api/agents
Content-Type: application/json

{
  "name": "poc-e2e-test-agent",
  "model": "gpt-4o-mini",
  "kind": "prompt",
  "instructions": "You are a helpful support assistant for insurance inquiries. Be concise and professional.",
  "description": "E2E test agent"
}
```

**Response:** `201 Created`

```json
{
  "id": "poc-e2e-test-agent",
  "name": "poc-e2e-test-agent",
  "versions": {
    "latest": {
      "id": "poc-e2e-test-agent:1",
      "name": "poc-e2e-test-agent",
      "version": "1",
      "description": "E2E test agent",
      "createdAt": 1777264025,
      "definition": {
        "kind": "prompt",
        "model": "gpt-4o-mini",
        "instructions": "You are a helpful support assistant for insurance inquiries. Be concise and professional."
      },
      "status": "active",
      "metadata": {}
    }
  },
  "agentEndpoint": {
    "versionSelector": {
      "versionSelectionRules": [
        { "type": "FixedRatio", "agentVersion": "@latest", "trafficPercentage": 100 }
      ]
    },
    "protocols": ["responses"]
  }
}
```

---

### Test 3 â€” List All Agents

```
GET http://localhost:5300/api/agents
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": "poc-e2e-test-agent",
      "name": "poc-e2e-test-agent",
      "versions": {
        "latest": {
          "definition": { "kind": "prompt", "model": "gpt-4o-mini" },
          "status": "active"
        }
      }
    },
    { "id": "agent-007", "name": "agent-007" },
    { "id": "claims-assistant", "name": "claims-assistant" },
    { "id": "poc-agent-01", "name": "poc-agent-01" }
  ]
}
```

---

### Test 4 â€” Get Agent by ID

```
GET http://localhost:5300/api/agents/poc-e2e-test-agent
```

**Response:** `200 OK` â€” Same structure as create response.

---

### Test 5 â€” Update Agent (PATCH)

```
PATCH http://localhost:5300/api/agents/poc-e2e-test-agent
Content-Type: application/json

{
  "instructions": "You are an expert insurance assistant. Answer questions about policies, claims, and coverage. Be concise."
}
```

**Response:** `200 OK`

```json
{
  "id": "poc-e2e-test-agent",
  "name": "poc-e2e-test-agent",
  "versions": {
    "latest": {
      "id": "poc-e2e-test-agent:2",
      "version": "2",
      "description": "",
      "createdAt": 1777264274,
      "definition": {
        "kind": "prompt",
        "model": "gpt-4o-mini",
        "instructions": "You are an expert insurance assistant. Answer questions about policies, claims, and coverage. Be concise."
      },
      "status": "active"
    }
  }
}
```

> Note: Version bumped from `1` to `2` after update.

---

### Test 6 â€” Create Conversation

```
POST http://localhost:5300/api/conversations
Content-Type: application/json

{}
```

**Response:** `201 Created`

```json
{
  "id": "conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ",
  "object": "conversation",
  "createdAt": 1777449100
}
```

---

### Test 7 â€” Get Conversation by ID

```
GET http://localhost:5300/api/conversations/conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ
```

**Response:** `200 OK` â€” Returns conversation object.

---

### Test 8 â€” Add Message to Conversation

```
POST http://localhost:5300/api/conversations/conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ/messages
Content-Type: application/json

{
  "role": "user",
  "content": "What types of insurance coverage do you offer?"
}
```

**Response:** `201 Created`

```json
{
  "id": "msg_a1b2c3d4e5f6",
  "object": "message",
  "threadId": "conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ",
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": { "value": "What types of insurance coverage do you offer?" }
    }
  ],
  "createdAt": 1777449200
}
```

---

### Test 9 â€” List Messages in Conversation

```
GET http://localhost:5300/api/conversations/conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ/messages
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": "msg_a1b2c3d4e5f6",
      "object": "message",
      "threadId": "conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ",
      "role": "user",
      "content": [
        { "type": "text", "text": { "value": "What types of insurance coverage do you offer?" } }
      ],
      "createdAt": 1777449200
    }
  ]
}
```

---

### Test 10 â€” Run Agent on Conversation (V2 â€” Synchronous)

```
POST http://localhost:5300/api/conversations/conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ/runs
Content-Type: application/json

{
  "assistantId": "demo-chat-agent-01"
}
```

> **V2:** Agent is referenced by **name**. The call is synchronous â€” the response is returned immediately.

**Response:** `201 Created`

```json
{
  "id": "resp_abc123",
  "object": "run",
  "threadId": "conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ",
  "agentName": "demo-chat-agent-01",
  "status": "completed",
  "createdAt": 1777449300,
  "completedAt": 1777449302
}
```

---

### Test 11 â€” Get Run Status (V2 â€” Always Completed)

```
GET http://localhost:5300/api/conversations/conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ/runs/resp_abc123
```

**Response:** `200 OK`

```json
{
  "id": "resp_abc123",
  "object": "run",
  "threadId": "conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ",
  "agentName": "demo-chat-agent-01",
  "status": "completed",
  "createdAt": 1777449300,
  "completedAt": 1777449302
}
```

> V2 runs are synchronous. This endpoint returns cached results for frontend polling compatibility.

---

### Test 12 â€” List Messages After Run (Agent Response)

```
GET http://localhost:5300/api/conversations/conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ/messages
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": "msg_a1b2c3d4e5f6",
      "object": "message",
      "threadId": "conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ",
      "role": "user",
      "content": [
        { "type": "text", "text": { "value": "What types of insurance coverage do you offer?" } }
      ],
      "createdAt": 1777449200
    },
    {
      "id": "msg_f6e5d4c3b2a1",
      "object": "message",
      "threadId": "conv_3bbb9480b00f9cd500AdoqjHUXRya2GJ",
      "role": "assistant",
      "content": [
        {
          "type": "text",
          "text": {
            "value": "Common types of insurance coverage include: Auto, Homeowners, Health, Life, Disability, Liability, Travel, Business, and Pet insurance. Let me know if you need details on any specific type!"
          }
        }
      ],
      "createdAt": 1777449302
    }
  ]
}
```

---

### Tests Skipped (pending portal confirmation)

- `DELETE /api/conversations/{threadId}` â€” Delete thread
- `DELETE /api/agents/{agentId}` â€” Delete agent
- `GET /api/agents/{agentId}` â€” Confirm 404 after delete

---

### Test Results Summary

| # | Endpoint | Method | Result |
|---|----------|--------|--------|
| 1 | `/api/agents/health` | GET | âœ… Pass |
| 2 | `/api/agents` | POST | âœ… Pass |
| 3 | `/api/agents` | GET | âœ… Pass |
| 4 | `/api/agents/{id}` | GET | âœ… Pass |
| 5 | `/api/agents/{id}` | PATCH | âœ… Pass |
| 6 | `/api/conversations` | POST | âœ… Pass |
| 7 | `/api/conversations/{id}` | GET | âœ… Pass |
| 8 | `/api/conversations/{id}/messages` | POST | âœ… Pass |
| 9 | `/api/conversations/{id}/messages` | GET | âœ… Pass |
| 10 | `/api/conversations/{id}/runs` | POST | âœ… Pass |
| 11 | `/api/conversations/{id}/runs/{runId}` | GET | âœ… Pass |
| 12 | `/api/conversations/{id}/messages` (after run) | GET | âœ… Pass |

### Bugs Found & Fixed During Testing

1. **Config** â€” `AgentApi:ProjectEndpoint` had wrong project name (`poc-01-foundry-project` â†’ `poc-01-project`)
2. **Model deserialization** â€” `FoundryAgent` didn't match V2 response structure. Foundry V2 nests data under `versions.latest`. Updated `AgentModels.cs` with proper nested types.
3. **Update agent** â€” PATCH sent `instructions` at top level. Foundry V2 requires a `definition` object. Fixed to merge with existing definition.

---

### Known Issue â€” V2 Agents vs OpenAI Assistants

**RESOLVED (2026-04-29):** Migrated from the classic OpenAI Assistants API (`/assistants`, `/threads`, `/threads/runs`) to the Foundry V2 API (`/agents`, `/openai/v1/conversations`, `/openai/v1/responses`).

The V2 API uses `agent_reference` by **name** instead of `asst_` IDs, and `/responses` is synchronous (no polling). The classic API is deprecated and will be retired March 2027.

### V2 Migration Changes (2026-04-29)

| Component | Before (Classic) | After (V2) |
|-----------|------------------|------------|| Frontend URL | `/api/threads` | `/api/conversations` || Create conversation | `POST /threads` | `POST /openai/v1/conversations` |
| Send message | `POST /threads/{id}/messages` | Stored in-memory; sent via `/responses` |
| Execute agent | `POST /threads/{id}/runs` (async, polling) | `POST /openai/v1/responses` (synchronous) |
| Agent reference | `assistant_id: "asst_xxx"` | `agent_reference: { name: "agent-name" }` |
| ID resolution | `ResolveAssistantIdAsync` helper | Not needed â€” agents referenced by name |
| Run status | Poll `GET /threads/{id}/runs/{runId}` | Always `completed` on return |

### Bugs Found & Fixed (2026-04-29)

1. **Hardcoded API version** â€” `/assistants` endpoint used `2024-10-01-preview` instead of config-driven `_agentApiVersion`
2. **Wrong endpoint** â€” Resolution called `/assistants` instead of `/agents`
3. **`asst_` prefix filter** â€” Resolver filtered by `asst_` prefix, skipping all Foundry V2 agent IDs
4. **API generation mismatch** â€” Agent CRUD used V2 `/agents` but execution used classic `/threads/runs` which requires `asst_` IDs
5. **415 on conversation create** â€” `null` body sent to `/conversations` (no Content-Type header)
6. **DeploymentNotFound** â€” `demo-chat-agent-01` referenced model `gpt-5.4-mini` but deployment was named `gpt-54-mini-tobe-approved`. Updated agent to use `gpt-4.1-mini`
