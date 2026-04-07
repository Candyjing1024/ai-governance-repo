---
id: APIM-12
title: Set up APIM with Redis cache semantic caching
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, caching, redis]
dependencies: [APIM-3, APIM-4]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Configure Azure API Management semantic caching using an Azure Cache for Redis Enterprise instance. Deploy the Redis Enterprise resource via Bicep with RediSearch module enabled, then add the APIM `azure-openai-semantic-cache-lookup` and `azure-openai-semantic-cache-store` policies to the LLM proxy API operation. The semantic cache should compare prompt embeddings and return cached completions when similarity exceeds the configured threshold, reducing latency and Azure OpenAI token spend for repeated or near-duplicate requests. Verify: (1) Redis Enterprise is provisioned with the RediSearch module; (2) APIM external cache resource is linked to the Redis instance; (3) a repeated prompt returns a cached response with the `x-cache: HIT` header; (4) a semantically similar prompt (above the similarity threshold) also returns a cache hit; (5) a distinct prompt results in a cache miss and fresh backend call; (6) cache TTL is configurable via APIM named value.
<!-- SECTION:DESCRIPTION:END -->
