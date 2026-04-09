---
id: FOUNDRY-3
title: Validate Foundry project resource group constraints
status: To Do
assignee: []
created_date: '2026-04-09 00:00'
updated_date: '2026-04-09 00:00'
labels: [foundry, infra, governance]
dependencies: [FOUNDRY-1]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a guardrail that enforces Azure AI Foundry project placement rules during provisioning. Current Microsoft documentation describes projects as child ARM resources of `Microsoft.CognitiveServices/accounts`, with both parent account and child project under the same resource group path. Verify: (1) the provisioning workflow fails fast if a request attempts to create a project in a different resource group than the parent Foundry account; (2) the validation error explains the documented child-resource constraint and required deployment shape; (3) the allowed resource ID pattern for the parent account and project is captured in implementation or design notes; (4) tests or dry-run validation cover both a valid same-resource-group request and an invalid cross-resource-group request; (5) the story documents this as a platform constraint unless Microsoft publishes a different supported model later.
<!-- SECTION:DESCRIPTION:END -->