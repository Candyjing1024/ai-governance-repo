---
id: APIM-8
title: Implement kill-switch named value and 503 response policy
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, operations, kill-switch]
dependencies: [APIM-3]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate the `kill-switch-enabled` named value in APIM and the inbound policy that returns 503 when it is set to `true`. Test toggling the named value on and off and confirm requests are blocked/unblocked accordingly. This is the last line of defense in the 3-layer kill-switch model: (1) disable agent app, (2) revoke managed identity, (3) block at APIM. Document the operational runbook for toggling the kill-switch in an incident.
<!-- SECTION:DESCRIPTION:END -->
