---
id: FOUNDRY-1
title: Create Azure AI Foundry projects with management SDK or REST
status: To Do
assignee: []
created_date: '2026-04-09 00:00'
updated_date: '2026-04-09 00:00'
labels: [foundry, infra, sdk, rest]
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement project provisioning for Azure AI Foundry by using the control-plane management surface, not the data-plane `azure-ai-projects` client. Support the official Python management SDK (`azure-mgmt-cognitiveservices`, `CognitiveServicesManagementClient.projects.begin_create`) and document or expose the equivalent ARM REST call for `/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.CognitiveServices/accounts/{accountName}/projects/{projectName}`. Verify: (1) a project can be created under an existing Foundry account by using the stable management API version selected by the platform; (2) the implementation is explicit that `azure-ai-projects` is only for working inside an existing project and is not used for provisioning; (3) the request payload, API version, and long-running operation handling are documented for operators; (4) the created project is visible in Azure AI Foundry and through ARM `get` or `list` operations; (5) the automation is parameterized so different environments can create different project names under the correct parent account.
<!-- SECTION:DESCRIPTION:END -->