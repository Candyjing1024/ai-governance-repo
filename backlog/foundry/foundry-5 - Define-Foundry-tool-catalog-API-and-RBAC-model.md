---
id: FOUNDRY-5
title: Define Foundry tool catalog API and RBAC model
status: To Do
assignee: []
created_date: '2026-04-09 00:00'
updated_date: '2026-04-09 00:00'
labels: [foundry, agents, sdk, rest, rbac]
dependencies: [FOUNDRY-4]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Document and validate the supported Azure AI Foundry tool automation model before implementation. The design must distinguish portal tool catalog entries from project connections and agent tool definitions, identify the supported SDK and REST surfaces for listing connections and creating agents with tools, and capture how RBAC applies across Foundry project scope, private catalog discovery, and downstream resources. Verify: (1) the story explicitly states whether a standalone public CRUD API for tool catalog entries exists or whether automation must use agent definitions and project connections instead; (2) the supported SDK surface is identified for the target language, including the client and methods used to create agents with tools and to list or get project connections; (3) the REST API shape is documented for the supported public endpoints, including how tool definitions are represented in agent payloads and how connections are listed or retrieved; (4) the RBAC model is documented, including the minimum Foundry project role for builders, any Azure API Center role needed for private catalog discovery, and any downstream Azure permissions required by the tool itself; (5) preview limitations and unsupported assumptions are captured, especially for private tool catalog, MCP-based tools, and any scenario that cannot yet be automated through a first-class catalog API.
<!-- SECTION:DESCRIPTION:END -->