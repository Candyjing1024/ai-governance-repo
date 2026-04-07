---
id: APIM-11
title: APIM end-to-end integration validation
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, testing, e2e]
dependencies: [APIM-4, APIM-5, APIM-6, APIM-8, APIM-9, APIM-10]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Full end-to-end smoke test of the APIM gateway layer. Verify: (1) an authenticated request from the UI flows through APIM to the orchestrator with correct headers; (2) an unauthenticated request is rejected with 401; (3) rate limiting triggers 429 after threshold; (4) kill-switch returns 503 when toggled on; (5) correlation ID and user ID headers are present in orchestrator logs; (6) all traffic is visible in App Insights. This story is the acceptance gate for the APIM epic — all prior APIM stories (APIM-3 through APIM-10) must be complete.
<!-- SECTION:DESCRIPTION:END -->
