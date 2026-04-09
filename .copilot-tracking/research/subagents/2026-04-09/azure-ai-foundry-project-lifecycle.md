---
title: Azure AI Foundry Project Lifecycle Research
description: Research findings on Azure AI Foundry project management SDKs, REST APIs, resource constraints, and RBAC as of 2026-04-09
author: GitHub Copilot
ms.date: 2026-04-09
ms.topic: reference
keywords:
  - azure ai foundry
  - microsoft foundry
  - project lifecycle
  - control plane
  - rbac
---

## Research scope

Status: Complete

Questions under investigation:

1. What is the current new SDK for Azure AI Foundry project management or control-plane operations?
2. Is there an official Python SDK or management SDK for creating and deleting Azure AI Foundry projects, and what package or API version is relevant?
3. Is there an official REST API to create Azure AI Foundry projects and to delete them?
4. Can an Azure AI Foundry project be created in a different resource group than its parent hub or resource?
5. Can access be granted via a single Microsoft Entra group rather than individual users?
6. What important preview caveats, constraints, or unclear areas should backlog authoring call out?

## Working notes

## Findings

### 1. Current SDK position

* The current Microsoft Foundry "new SDK" for working inside an existing project is the Azure AI Projects client library for Python, package `azure-ai-projects`. The Learn page currently shows version `2.0.1` and states that it uses Microsoft Foundry data plane REST API `v1`.
* That SDK is not the control-plane SDK for creating or deleting Foundry projects. Its prerequisites explicitly assume you already have "a project in Microsoft Foundry" and a project endpoint URL.
* For control-plane project lifecycle operations, Microsoft exposes an official Azure Resource Manager management client in Python: `azure-mgmt-cognitiveservices`, via `CognitiveServicesManagementClient.projects` and `ProjectsOperations`.
* The generated management client documentation shows a default ARM API version of `2025-09-01`. The ARM template reference also documents the child resource type `Microsoft.CognitiveServices/accounts/projects`, including a newer preview schema at `2026-01-15-preview`.

Conclusion: treat `azure-ai-projects` as the project data-plane SDK, and `azure-mgmt-cognitiveservices` as the official Python control-plane SDK for create, update, get, list, and delete of Foundry projects.

### 2. Official REST API for create and delete

* Yes. Microsoft documents the Foundry project as an ARM child resource of `Microsoft.CognitiveServices/accounts` with resource type `Microsoft.CognitiveServices/accounts/projects`.
* The official ARM path shape is:

  `/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.CognitiveServices/accounts/{accountName}/projects/{projectName}`

* In the Cognitive Services management TypeSpec and generated SDK, the operation group is `Projects`.
* The management surface includes these lifecycle operations:
  * `Projects.create` in the TypeSpec, surfaced in Python as `ProjectsOperations.begin_create(...)`
  * `Projects.update` in the TypeSpec, surfaced in Python as `ProjectsOperations.begin_update(...)`
  * `Projects.delete` in the TypeSpec, surfaced in Python as `ProjectsOperations.begin_delete(...)`
  * `Projects.get` and `Projects.list`
* The Python docs describe `begin_create` as "Create Cognitive Services Account's Project" and `begin_delete` as "Deletes a Cognitive Services project from the resource group."
* The ARM template reference shows the resource payload shape as `location`, `name`, optional `identity`, optional `tags`, and `properties` with at least `description` and `displayName`.

Conclusion: there is an official ARM REST surface for create and delete. The project is a child ARM resource under a Cognitive Services account, not a standalone top-level resource.

### 3. Resource-group constraints relative to parent hub or resource

* Current Microsoft documentation uses `Foundry resource` and ARM `account` terminology rather than emphasizing older `hub` wording.
* The current docs state that Foundry projects are Azure child resources and that multiple projects can be created "on an existing Foundry resource."
* The ARM template reference defines `Microsoft.CognitiveServices/accounts/projects` as a child resource with `parent: account` and says it is deployed at resource-group scope.
* The ARM resource ID shape contains one `resourceGroups/{resourceGroupName}` segment above both the parent account and child project.
* I did not find any Microsoft documentation that supports creating a Foundry project in a different resource group than its parent Foundry resource or account.
* The portal guidance also lines up with same-resource-group behavior:
  * When creating a new Foundry resource plus its first project, you choose one resource group for that environment.
  * When adding another project, you select the parent resource and add the child project under it. The docs do not expose a separate resource-group selection for the child project.

Conclusion: based on the documented ARM resource shape and portal flow, a Foundry project should be treated as required to live in the same resource group as its parent Foundry resource or account. I found no documented cross-resource-group child-project support.

### 4. Granting access through one Microsoft Entra group

* Yes. Microsoft documents group-based assignment explicitly.
* The Foundry RBAC doc says to create a role assignment in Azure portal IAM and set `Members` to `User, group, or service principal`.
* The same doc has an appendix section "Use Microsoft Entra groups with Foundry" that explicitly recommends assigning the required role to a security group so all members inherit access.
* The RBAC doc also defines project scope as a supported scope: subscription, resource group, Foundry resource, or Foundry project.
* Documented role patterns relevant to group-based access include:
  * `Azure AI User` on Foundry project scope for developers building in a project
  * `Reader` on the parent Foundry resource scope when developers need read-only visibility there
  * `Azure AI Project Manager` on the Foundry resource scope for leads who create projects and can conditionally assign `Azure AI User`
* The RBAC appendix also gives a concrete example: to build agents, run traces, and use core Foundry capabilities, assign `Azure AI User` to the Microsoft Entra group.

Conclusion: a single Microsoft Entra security group can be used for project access. Assign the group an appropriate Foundry role at the intended scope, commonly project scope for builders.

### 5. Important constraints, preview caveats, and unclear areas

* Naming caveat: `azure-ai-projects` sounds like it might manage project resources, but the docs position it as a project endpoint client that assumes the project already exists.
* Capability caveat: the Foundry project creation doc says "not all Foundry capabilities support organizing work in projects yet" and that the first `default` project is more powerful than additional projects.
* Shared-boundary caveat: child projects can have their own access controls, but they share network security, deployments, and Azure tool integration from the parent resource.
* Default-project caveat: if you delete the default project, the next created project becomes the default project.
* RBAC automation caveat: the RBAC doc says automatic `Azure AI User` assignment for the creator applies when deploying from Azure portal or Foundry portal UI, but "doesn't apply when deploying Foundry from SDK or CLI."
* Versioning caveat: the management SDK docs default to stable API version `2025-09-01`, while the ARM template reference already documents `2026-01-15-preview`. Backlog items should decide deliberately whether to stay on stable ARM or consume preview schema features.
* Discoverability caveat: the Learn how-to page for creating projects is portal-oriented. In my research session, the tabbed page did not expose concrete Python SDK or CLI command snippets even though the management SDK and ARM resource model clearly exist.

Conclusion: backlog items should separate data-plane SDK work from control-plane lifecycle automation, and they should explicitly account for default-project differences, shared parent-resource boundaries, and stable-versus-preview API decisions.

## Recommended backlog implications

* Treat project provisioning as ARM control-plane automation, not as `azure-ai-projects` SDK work.
* Model a project as a child resource of the parent Foundry resource or Cognitive Services account, with the same resource-group boundary.
* Design access onboarding around Microsoft Entra security groups and project-scope `Azure AI User` assignments, not per-user grants.
* Capture a product decision on whether the workload must support non-default child projects, because some Foundry capabilities still differ between default and additional projects.
* Decide whether to target stable ARM API version `2025-09-01` or accept preview dependency on `2026-01-15-preview` only if required by a specific missing property.

## Sources

* [Azure AI Projects client library for Python - version 2.0.1](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme?view=azure-python)
* [Create a project for Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/how-to/create-projects)
* [Quickstart: Deploy a Microsoft Foundry resource by using a Bicep file](https://learn.microsoft.com/en-us/azure/foundry/how-to/create-resource-template)
* [Microsoft.CognitiveServices accounts/projects](https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/accounts/projects)
* [CognitiveServicesManagementClient Class](https://learn.microsoft.com/en-us/python/api/azure-mgmt-cognitiveservices/azure.mgmt.cognitiveservices.cognitiveservicesmanagementclient?view=azure-python)
* [ProjectsOperations Class](https://learn.microsoft.com/en-us/python/api/azure-mgmt-cognitiveservices/azure.mgmt.cognitiveservices.operations.projectsoperations?view=azure-python)
* [Role-based access control for Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry)
* [Azure REST API Specs: Cognitive Services management Project.tsp](https://github.com/Azure/azure-rest-api-specs/blob/main/specification/cognitiveservices/CognitiveServices.Management/Project.tsp)
* [Azure REST API Specs: Cognitive Services resource-manager readme](https://github.com/Azure/azure-rest-api-specs/blob/main/specification/cognitiveservices/resource-manager/readme.md)