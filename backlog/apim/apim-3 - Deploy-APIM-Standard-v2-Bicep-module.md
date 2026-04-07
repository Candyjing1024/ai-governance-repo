---
id: APIM-3
title: Deploy APIM Standard v2 Bicep module to dev environment
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, infra]
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Deploy the existing `infra/modules/apim.bicep` (Standard v2 SKU, user-assigned managed identity, App Insights logger) to the dev environment via `azd up` / `azd provision`. Verify the APIM resource is created in Azure, the managed identity is assigned, and the service is accessible at its gateway URL. This is the foundation for all other APIM stories (APIM-4 through APIM-10).
<!-- SECTION:DESCRIPTION:END -->
