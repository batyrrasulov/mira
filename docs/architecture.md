# Architecture

## Runtime Architecture

Mira exposes an OpenAI-compatible API and can run in two modes:

1. Provider mode

- Requests are forwarded to an upstream OpenAI-compatible model endpoint.
- Output is normalized into a strict LMS-safe JSON contract.

1. Fallback mode

- Used when provider configuration is missing, disabled, or upstream fails.
- Returns deterministic structured guidance so downstream integrations do not break.

## Components

- API service: src/mira/api.py
- Request schemas: src/mira/schema.py
- Guardrails: src/mira/guardrails.py
- Provider client: src/mira/llm_client.py
- Contract normalization: src/mira/contract.py
- Environment config: src/mira/settings.py

## Request Path

1. Client sends POST /v1/chat/completions or POST /v1/completions.
2. Guardrails validate token limits and input size.
3. Optional API-key auth is enforced if configured.
4. Runtime generates content from provider or fallback.
5. Output is normalized to the required JSON schema.
6. Response is returned using OpenAI-compatible response shape.

## Operational Endpoints

- GET /health: static service metadata and current configuration summary.
- GET /ready: readiness check, including provider reachability when provider mode is configured.

## Contract Guarantees

The response payload always includes:

- learning_goal
- explanation
- guided_steps
- check_for_understanding
- policy_note

This contract is designed for stable LMS-side rendering.
