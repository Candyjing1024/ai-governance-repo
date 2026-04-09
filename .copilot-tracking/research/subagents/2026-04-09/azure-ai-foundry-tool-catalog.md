---
title: Azure AI Foundry tool catalog research
description: Research notes on Azure AI Foundry tool catalog support, SDKs, REST APIs, RBAC, and limitations as of 2026-04-09.
author: GitHub Copilot
ms.date: 2026-04-09
ms.topic: reference
---

## Scope

Research questions:

* What Azure AI Foundry tool catalog is and which main object names or API concepts are involved
* Whether SDKs exist to create, list, or get tool catalog tools, including package and client names
* Whether REST APIs exist to create, list, or get tool catalog entries, including operation names or path shapes
* How RBAC and permissions work for tool catalog access or usage
* Important limitations and distinctions between tool catalog entries, connections, and agent tool definitions

## Findings

### 1. What the tool catalog is

* The main concept page defines Foundry Tools as the portal experience where developers discover, configure, and manage tools for agents and workflows, and defines the tool catalog as the browsable list of available tools, including public and organizational tools.
* The same page distinguishes between portal catalog concepts and runtime concepts. Important object names are: Foundry project, agent, agent definition, tool, project connection, MCP server, remote MCP server, local MCP server, private tool catalog, and custom tool.
* In the portal catalog, the documented catalog entry types are remote MCP server, local MCP server, and custom tools derived from Azure Logic Apps connectors. Built-in agent tools such as web search, code interpreter, Azure AI Search, Azure Functions, OpenAPI, and image generation are documented as agent tools, not as a separate public catalog-entry resource type.
* In code and REST, tools are generally represented inside an agent definition. The public schemas and samples use types such as `PromptAgentDefinition`, `DeclarativeAgentDefinition`, `WebSearchTool`, `CodeInterpreterTool`, `AzureAISearchTool`, `AzureFunctionTool`, `OpenApiTool`, `MCPTool`, `A2APreviewTool`, and other preview tool models.

### 2. SDK support

* Public SDKs exist to create agents that include tools, and to list or get project connections that many tools depend on.
* The documented primary project SDKs are:
	* Python: `azure-ai-projects` with `azure.ai.projects.AIProjectClient`
	* JavaScript or TypeScript: `@azure/ai-projects` with `AIProjectClient`
	* .NET: `Azure.AI.Projects` with `AIProjectClient`
	* Java: `azure-ai-projects`, plus `azure-ai-agents` for some agent tool surfaces
* Relevant documented SDK methods and patterns include:
	* Python: `project.agents.create_version(...)`, `project.connections.list()`, `project.connections.get(...)`, `project.connections.get_default(...)`
	* JavaScript or TypeScript: `project.agents.createVersion(...)`, `project.connections.list()`, `project.connections.get(...)`, `project.connections.getWithCredentials(...)`
	* .NET: `projectClient.AgentAdministrationClient.CreateAgentVersion(...)` or `CreateAgentVersionAsync(...)` and connection APIs exposed from `AIProjectClient`
	* Java: `AgentsClient.createAgentVersion(...)`; for OpenAPI tools, the docs explicitly note that `com.azure:azure-ai-agents` should be used because `com.azure:azure-ai-projects` does not currently expose OpenAPI agent tool types
* The public docs and SDK samples consistently show tool creation as part of agent creation or update, not as a first-class public SDK for CRUD over tool catalog entries themselves.
* I did not find authoritative public SDK documentation for create, list, or get operations over a standalone Foundry tool catalog entry resource. The closest programmable public surface is project connections plus agent tool definitions. Private catalog authoring is documented through Azure API Center, not `AIProjectClient`.

### 3. REST API support

* The public Foundry data-plane REST surface exposes agent resources and project connection resources. Tools are supplied in agent definitions or response payloads.
* Authoritative spec evidence shows agent routes such as:
	* `POST /agents`
	* `GET /agents`
	* `GET /agents/{agent_name}`
	* `POST /agents/{agent_name}/versions`
	* `GET /agents/{agent_name}/versions`
	* `GET /agents/{agent_name}/versions/{agent_version}`
* The corresponding request body carries the tool definitions in `definition.tools`. REST samples in the docs show creating an agent with tools by posting to the project endpoint with payloads such as `{"definition":{"tools":[...]}}`.
* Authoritative spec evidence also shows connection routes such as:
	* `GET /connections`
	* `GET /connections/{name}`
	* action operation `getWithCredentials` for a named connection
* The connection model includes tool-relevant connection types. The Foundry data-plane schema includes `RemoteTool_Preview` in `ConnectionType`, which aligns with MCP and remote tool connection scenarios.
* I did not find an authoritative public Foundry REST route for CRUD of standalone tool catalog entries such as `/toolcatalog`, `/toolCatalogEntries`, or `/tools` as a resource collection. The catalog is documented primarily as a portal discovery and configuration surface. For organization-scoped private catalogs, the documented management plane is Azure API Center registration plus Foundry portal discovery.

### 4. RBAC and permission model

* The main Foundry RBAC article says access is controlled through Azure RBAC at the Foundry resource and project scope. The current built-in Foundry roles documented there are `Azure AI User`, `Azure AI Project Manager`, `Azure AI Account Owner`, and `Azure AI Owner`.
* The role table states that `Azure AI User` is the least-privilege role for building and developing in a project.
* Tool-specific pages add two important refinements:
	* Some pages still reference `Azure AI Developer` in prerequisites, which suggests docs are in transition or use older naming on some pages.
	* Some setup flows require broader resource-management roles such as `Contributor` or `Owner` on the Foundry resource for management tasks, while agent-building still requires project-level permissions such as `Azure AI User`.
* There is no separate documented standalone "tool catalog RBAC" model for the general public catalog. In practice, permissions split across three layers:
	* Foundry project or account RBAC determines whether a developer can discover, configure, and use tools in the project.
	* Project connections store authentication and target metadata for many tools, and tool definitions frequently reference `project_connection_id`.
	* Downstream Azure resources still require their own RBAC or connection-based credentials for the project identity, agent identity, or user identity that calls them.
* For private tool catalogs, discovery permission is explicitly handled through Azure API Center RBAC. The private tool catalog article requires at least the `Azure API Center Data Reader` role on the API Center resource for developers who need to discover the catalog.
* For agent identity-based tool auth, the agent identity documentation says:
	* MCP server connections use connection category `RemoteTool` with auth type `AgenticIdentityToken`
	* A2A endpoint connections use connection category `RemoteA2A` with auth type `AgenticIdentity`
	* Agent Service then acquires a token for the configured `audience` and uses it to authenticate to the downstream tool endpoint

### 5. Important limitations, preview caveats, and distinctions

* The tool catalog page explicitly states that the Foundry tool catalog and core tools framework are generally available, but some individual tools remain in preview.
* The private tool catalog feature is explicitly preview.
* Many tool types are still preview, including examples such as browser automation, image generation, A2A, SharePoint grounding, Fabric, memory, and some MCP-related scenarios.
* The most important conceptual distinction is:
	* A catalog entry is a portal discovery and setup item.
	* A project connection is a reusable configuration and authentication object.
	* An agent tool definition is the runtime configuration attached to `definition.tools` in an agent or request.
* Catalog-based setup can create or simplify MCP tool configuration in the portal without changing application code. The Azure DevOps MCP Server preview is a documented example of a catalog entry that can be added directly from the portal.
* Connection-based tools often require `project_connection_id` and sometimes extra setup in the target service.
* The MCP tool defaults to approval-based usage for remote calls. The docs emphasize reviewing tool-call data before approving remote MCP actions.
* The Foundry MCP Server is a separate preview service from the Foundry tool catalog. Its published limitations include no network isolation through private endpoints, no SLA, possible EU or US processing, and tool definitions that can change during preview.
* Language support is not perfectly uniform across SDKs. One explicit example is Java OpenAPI tool support, which requires `azure-ai-agents` rather than `azure-ai-projects`.

## Sources

* Microsoft Learn: Agent tools overview for Foundry Agent Service
	* https://learn.microsoft.com/azure/foundry/agents/concepts/tool-catalog
* Microsoft Learn: What is Microsoft Foundry Agent Service?
	* https://learn.microsoft.com/azure/foundry/agents/overview
* Microsoft Learn: Create a private tool catalog in Foundry Agent Service
	* https://learn.microsoft.com/azure/foundry/agents/how-to/private-tool-catalog
* Microsoft Learn: Connect agents to Model Context Protocol servers
	* https://learn.microsoft.com/azure/foundry/agents/how-to/tools/model-context-protocol
* Microsoft Learn: Set up authentication for Model Context Protocol tools
	* https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication
* Microsoft Learn: Agent identity concepts in Microsoft Foundry
	* https://learn.microsoft.com/azure/foundry/agents/concepts/agent-identity
* Microsoft Learn: Role-based access control for Microsoft Foundry
	* https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry
* Microsoft Learn: Microsoft Foundry SDKs and Endpoints
	* https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview
* Microsoft Learn: Connect an Azure AI Search index to Foundry agents
	* https://learn.microsoft.com/azure/foundry/agents/how-to/tools/ai-search
* Microsoft Learn: Connect agents to OpenAPI tools
	* https://learn.microsoft.com/azure/foundry/agents/how-to/tools/openapi
* Microsoft Learn: Connect to an A2A agent endpoint from Foundry Agent Service
	* https://learn.microsoft.com/azure/foundry/agents/how-to/tools/agent-to-agent
* Microsoft Learn: Govern MCP tools by using an AI gateway
	* https://learn.microsoft.com/azure/foundry/agents/how-to/tools/governance
* Microsoft Learn: Get started with Foundry MCP Server using Visual Studio Code
	* https://learn.microsoft.com/azure/foundry/mcp/get-started
* Microsoft Learn: Explore available tools and example prompts for Foundry MCP Server
	* https://learn.microsoft.com/azure/foundry/mcp/available-tools
* Azure SDK for Python README: Azure AI Projects client library for Python
	* https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-projects/README.md
* Azure REST API specs: Foundry data-plane agent routes
	* https://github.com/Azure/azure-rest-api-specs/blob/main/specification/ai-foundry/data-plane/Foundry/src/agents/routes.tsp
* Azure REST API specs: Foundry data-plane connection routes
	* https://github.com/Azure/azure-rest-api-specs/blob/main/specification/ai-foundry/data-plane/Foundry/src/connections/routes.tsp
* Azure REST API specs: Foundry data-plane tool models
	* https://github.com/Azure/azure-rest-api-specs/blob/main/specification/ai-foundry/data-plane/Foundry/src/tools/models.tsp

## Open questions

* The public docs do not yet expose a clear first-class Foundry API for CRUD over standalone tool catalog entries. If engineering needs non-portal automation for catalog population, the next question is whether Azure API Center APIs are sufficient for the private catalog scenario, or whether the requirement is specifically for public catalog-style integration.