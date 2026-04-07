---
id: APIM-6
title: Implement per-user rate limiting policy (60 req/5 min)
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, security, rate-limiting]
dependencies: [APIM-3]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate and test the `rate-limit-by-key` policy configured in `infra/modules/apim.bicep` — 60 requests per 5-minute window, keyed on the JWT `oid` claim (user object ID). Confirm 429 responses are returned once a user breaches the threshold, and that limits are scoped per-user (one user's rate limit does not affect others). Verify the Retry-After header is present in 429 responses.
<!-- SECTION:DESCRIPTION:END -->
