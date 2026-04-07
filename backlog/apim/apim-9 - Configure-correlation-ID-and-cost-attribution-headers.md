---
id: APIM-9
title: Configure correlation ID injection and cost attribution headers
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, observability, headers]
dependencies: [APIM-4]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate that APIM correctly injects `x-correlation-id` (generated if not present in the incoming request) and `x-user-id` (extracted from the JWT `oid` claim) into every forwarded request. Confirm these headers are visible in orchestrator logs and propagate through the full trace chain: APIM → orchestrator → agents → tools → evidence store. The correlation ID is the single thread linking all downstream logs for a given request.
<!-- SECTION:DESCRIPTION:END -->
