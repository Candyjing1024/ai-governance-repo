---
id: APIM-4
title: Configure APIM backend routing to Azure AI Foundry LLM models
status: To Do
assignee: []
created_date: '2026-04-07 00:00'
updated_date: '2026-04-07 00:00'
labels: [apim, infra, ai-foundry, llm]
dependencies: [APIM-3]
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Configure APIM backend pools and routing rules to proxy requests to three Azure AI Foundry model deployments: GPT-4o (primary chat completions), GPT-4o-mini (lightweight/low-latency tasks), and text-embedding-ada-002 (embedding generation). Each model is registered as a separate APIM backend pointing to its Foundry endpoint. A single `llm-api` API definition uses URL path-based routing (`/chat`, `/chat-mini`, `/embeddings`) to direct traffic to the correct backend. Verify: (1) each of the three backends resolves to the correct Foundry deployment; (2) requests to `/chat` route to GPT-4o, `/chat-mini` to GPT-4o-mini, and `/embeddings` to text-embedding-ada-002; (3) managed identity authentication is used for backend credentials (no API keys in policies); (4) a health check or test prompt returns a valid completion/embedding from each model; (5) backend URLs are parameterized in Bicep so deployments can target different Foundry projects per environment.
<!-- SECTION:DESCRIPTION:END -->
