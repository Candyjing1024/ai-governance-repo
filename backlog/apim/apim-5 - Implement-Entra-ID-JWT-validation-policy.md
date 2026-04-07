---
id: APIM-5
title: Implement Entra ID JWT validation policy in APIM
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, security, auth]
dependencies: [APIM-3]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Configure the `audience` named value in APIM with the Entra ID client ID. Validate the inbound JWT policy correctly rejects unauthenticated requests (401) and passes valid Entra ID bearer tokens through to the orchestrator. Test with both valid and expired/invalid tokens. Per ADR-002, APIM is responsible for all external authentication; the orchestrator trusts requests that have passed APIM validation.
<!-- SECTION:DESCRIPTION:END -->
