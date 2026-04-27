# Architecture

## Overview

Mira is designed as an education-focused LLM assistant platform for LMS
integration without exposing student workflows to unapproved third-party tools.
The current repository provides a public-safe reference implementation with:

- OpenAI-compatible API surface for easy LMS plug-in wiring
- Strict request guardrails
- Deterministic JSON output contract for downstream parsing
- Structured model baseline workflow for outcome-oriented experimentation

## Logical Components

1. Runtime API (src/mira/api.py)
- Provides /health, /v1/chat/completions, and /v1/completions.
- Enforces payload guardrails and returns strict JSON guidance.

2. Guardrail Engine (src/mira/guardrails.py)
- Input character caps
- Output token bounds
- Endpoint-specific payload validation

3. Configuration Layer (src/mira/settings.py, configs/app.env.example)
- Environment-based runtime control
- No secrets committed

4. Training Workflow (training/scripts/*.py)
- Dataset shaping from structured snapshots
- Temporal holdout structured baseline model
- Post-holdout metrics scoring

5. Evaluation Suite (evaluation/run_quality_suite.py)
- Contract pass-rate tracking
- Keyword coverage approximation
- Latency and status checks

## Request Flow

1. LMS plugin sends a prompt to /v1/chat/completions.
2. Guardrails validate max_tokens and input size.
3. Runtime generates guidance JSON with pedagogical structure.
4. LMS consumes stable keys (learning_goal, guided_steps, etc.) for display.

## Why OpenAI-Compatible Endpoints

Many LMS middleware layers already support OpenAI schema conventions.
Maintaining this compatibility lowers integration friction and keeps swapping
between local and hosted inference providers simple.

## Extension Points

- Replace heuristic response generation with provider-backed inference.
- Add retrieval for course-approved content only.
- Add experiment flags for A/B model routing.
- Add institutional telemetry sinks with privacy controls.
