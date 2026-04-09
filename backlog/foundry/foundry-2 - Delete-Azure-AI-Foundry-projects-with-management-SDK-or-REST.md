---
id: FOUNDRY-2
title: Delete Azure AI Foundry projects with management SDK or REST
status: To Do
assignee: []
created_date: '2026-04-09 00:00'
updated_date: '2026-04-09 00:00'
labels: [foundry, infra, sdk, rest]
dependencies: [FOUNDRY-1]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement safe deletion for Azure AI Foundry projects by using the control-plane management surface (`CognitiveServicesManagementClient.projects.begin_delete`) and document or expose the equivalent ARM REST delete operation for the project child resource. Verify: (1) deletion works for a previously created non-default project and the long-running operation completes successfully; (2) the workflow includes pre-delete checks so the platform does not accidentally target the wrong subscription, resource group, account, or project name; (3) the implementation handles not-found and already-deleted cases predictably; (4) post-delete validation confirms the project no longer appears in Azure AI Foundry or ARM `get` or `list` results; (5) the deletion path clearly documents any platform restrictions for default projects or shared parent resources before execution.
<!-- SECTION:DESCRIPTION:END -->