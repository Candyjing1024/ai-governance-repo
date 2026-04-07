---
id: APIM-10
title: Set up APIM diagnostic logging to App Insights and Log Analytics
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, observability, logging]
dependencies: [APIM-3]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate APIM diagnostic settings are logging request/response traffic to both the Log Analytics workspace and Application Insights instance (already configured in `infra/modules/apim.bicep`). Confirm that logs appear in App Insights within an acceptable delay, trace IDs correlate across APIM and orchestrator, and that the `GatewayLogs` table in Log Analytics is populated. Define alert thresholds for 5xx error rates and latency spikes.
<!-- SECTION:DESCRIPTION:END -->
