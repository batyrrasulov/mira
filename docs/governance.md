# Governance and Safety

## Purpose

This project is intended for learning support, concept clarification, and
study guidance. It is not intended to bypass coursework requirements or
assessment integrity.

## Core Principles

1. Learning-first responses
- Encourage reasoning steps and reflection.
- Avoid answer-only behavior where possible.

2. Data minimization
- Avoid storing raw student-identifiable data by default.
- Use anonymized or synthetic data for public demonstrations.

3. Contract reliability
- Return strict JSON where configured so LMS behavior is predictable.

4. Observability without over-collection
- Track technical quality signals (latency, pass rate), not sensitive
  personal content by default.

## Recommended Institutional Controls

- Formal policy review for acceptable use in coursework
- Course-level opt-in and instructor visibility
- Human escalation path for harmful or ambiguous outputs
- Periodic model and prompt audits

## Public Repository Boundaries

- No production credentials
- No proprietary business data
- No institution-specific confidential datasets
- No personal identifiers in release narratives

## Evaluation Policy

Each release candidate should be evaluated on:

- API contract pass rate
- Response usefulness against curated prompts
- Failure/empty response rate
- Latency SLO compliance
- Regression against prior approved version
