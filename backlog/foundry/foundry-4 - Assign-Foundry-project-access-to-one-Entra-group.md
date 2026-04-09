---
id: FOUNDRY-4
title: Assign Foundry project access to one Entra group
status: To Do
assignee: []
created_date: '2026-04-09 00:00'
updated_date: '2026-04-09 00:00'
labels: [foundry, security, rbac]
dependencies: [FOUNDRY-1]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Automate Azure AI Foundry project access assignment through one Microsoft Entra security group instead of per-user role assignments. Use Azure RBAC at project scope so the selected group receives the minimum role needed for builders, typically `Azure AI User`, and document any parent-account scope requirements such as `Reader` when they are needed. Verify: (1) a single Entra group can be assigned to the project through IAM without assigning each user separately; (2) members of that group can open and use the target project according to the selected role; (3) a user outside the group is denied the same project access; (4) role assignment scope is limited to the project unless a broader scope is intentionally required; (5) the automation and runbook document how new team members gain access by joining the group rather than by changing the project configuration.
<!-- SECTION:DESCRIPTION:END -->