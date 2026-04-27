# mira

Anonymous, education-focused LLM assistant scaffold designed for LMS integration,
concept mastery support, and reproducible model evaluation.

This repository is intentionally public-safe:

- No personal identifiers
- No institution-private data
- No production credentials
- No proprietary business implementation details

It is inspired by real-world self-hosted LLM engineering patterns (training,
runtime guardrails, monitoring, and quality gates), adapted into a clean
academic project structure suitable for portfolio review and capstone-style work.

## Table of Contents

1. Project Context
2. Goals and Non-Goals
3. System Architecture
4. Repository Layout
5. Quickstart
6. API Contract
7. Training Workflow
8. Evaluation Workflow
9. LMS Integration Pattern
10. Governance and Safety
11. Reference Audit Learnings
12. Roadmap

## 1) Project Context

Many students already use AI tools, but institutions often need a controlled,
reviewable, and policy-aligned assistant for learning support.

Mira is built around that premise:

- Support understanding, reasoning, and guided study
- Preserve academic integrity boundaries
- Keep deployment flexible (self-hosted or provider-backed)
- Keep interfaces predictable for LMS plug-ins and middleware

## 2) Goals and Non-Goals

### Goals

- Provide an OpenAI-compatible API surface for easy integration.
- Enforce request guardrails (input and output limits).
- Return deterministic JSON for LMS-side rendering logic.
- Offer a starter structured-model training + evaluation flow.
- Document architecture and governance for review committees.

### Non-Goals

- This repository does not ship a proprietary production model.
- This repository does not include private datasets.
- This repository does not claim autonomous grading or proctoring.

## 3) System Architecture

High-level flow:

1. LMS component sends a prompt to /v1/chat/completions.
2. Guardrails validate payload size and token limits.
3. Runtime returns structured guidance JSON.
4. LMS renders the response sections in student-facing UI.

Current runtime in this public scaffold is deterministic and contract-first.
You can later plug in a real LLM provider via environment configuration.

More detail: see docs/architecture.md.

## 4) Repository Layout

```text
mira/
├── configs/
│   └── app.env.example
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   ├── governance.md
│   └── reference_audit_llm_stack.md
├── evaluation/
│   ├── prompts/
│   │   └── sample_prompts.jsonl
│   ├── results/
│   │   └── .gitkeep
│   └── run_quality_suite.py
├── scripts/
│   └── run_local_api.sh
├── src/
│   └── mira/
│       ├── __init__.py
│       ├── api.py
│       ├── guardrails.py
│       ├── schema.py
│       └── settings.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   └── test_guardrails.py
├── training/
│   ├── data/
│   │   └── sample_outcomes.csv
│   ├── outputs/
│   │   └── .gitkeep
│   ├── scripts/
│   │   ├── build_dataset.py
│   │   ├── score_outcomes.py
│   │   └── train_structured_model.py
│   └── README.md
├── .gitignore
├── LICENSE
├── pyproject.toml
└── requirements.txt
```

## 5) Quickstart

### Prerequisites

- Python 3.11+
- pip

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp configs/app.env.example configs/app.env
```

### Run API

```bash
bash scripts/run_local_api.sh
```

### Check health

```bash
curl -sS http://127.0.0.1:8080/health
```

Expected: JSON with status=ok and guardrail settings.

## 6) API Contract

### Endpoint: POST /v1/chat/completions

Input (OpenAI-compatible subset):

- model
- messages
- max_tokens
- temperature

Output:

- object: chat.completion
- choices[0].message.content: strict JSON string with fields:
  - learning_goal
  - explanation
  - guided_steps
  - check_for_understanding
  - policy_note

### Endpoint: POST /v1/completions

Input:

- model
- prompt
- max_tokens
- temperature

Output:

- object: text_completion
- choices[0].text with same structured guidance content

### Guardrails

Current guardrails include:

- max input characters
- max output tokens
- minimum output tokens
- endpoint-specific payload validation

## 7) Training Workflow

The training folder demonstrates a structured modeling track inspired by
production patterns:

1. Build SFT-style JSONL from structured data:

```bash
python training/scripts/build_dataset.py \
  --input-csv training/data/sample_outcomes.csv \
  --output-jsonl training/outputs/sft_bootstrap.jsonl \
  --report-json training/outputs/sft_build_report.json
```

2. Train structured baseline with temporal holdout:

```bash
python training/scripts/train_structured_model.py \
  --input-csv training/data/sample_outcomes.csv \
  --output-model training/outputs/structured_model.joblib \
  --output-scored-csv training/outputs/structured_holdout_scored.csv \
  --output-report training/outputs/structured_training_report.json
```

3. Score outcomes:

```bash
python training/scripts/score_outcomes.py \
  --input-csv training/outputs/structured_holdout_scored.csv \
  --score-col ModelScore \
  --output-json training/outputs/outcome_metrics.json
```

## 8) Evaluation Workflow

Run contract + quality checks against the local API:

```bash
python evaluation/run_quality_suite.py \
  --base-url http://127.0.0.1:8080 \
  --prompts-file evaluation/prompts/sample_prompts.jsonl \
  --output-json evaluation/results/quality_suite_report.json
```

The report includes:

- status_200_rate
- contract_pass_rate
- keyword_hit_avg
- latency_avg_s

## 9) LMS Integration Pattern

Recommended integration approach:

1. LMS plugin sends requests to Mira API.
2. Parse strict JSON output keys.
3. Render sections in pedagogical format (goal, steps, checks).
4. Log only policy-approved metadata.

This allows institution-controlled deployment while preserving compatibility
with existing OpenAI-oriented tooling.

## 10) Governance and Safety

- Learning support, not cheating automation
- Policy-aligned response framing
- Public-safe defaults for data handling
- No confidential dataset publication

See docs/governance.md for the full policy stance.

## 11) Reference Audit Learnings

This repo includes an anonymized engineering audit summary of a larger
self-hosted LLM stack to capture practical lessons without disclosing
sensitive implementation details.

See docs/reference_audit_llm_stack.md.

## 12) Roadmap

Near-term

- Add provider adapter layer (OpenAI-compatible upstream or local model)
- Add retrieval hooks for course-approved materials
- Add batch evaluation runner with rubric scoring
- Add release checklist and regression gate

Mid-term

- Add role-aware responses by course level
- Add instructor-facing analytics dashboard
- Add robust monitoring and alerting policy hooks

Long-term

- Controlled pilot deployment in LMS
- Formal outcome study with ethics and governance review

---

If you are evaluating this repository for academic or portfolio purposes, start
with docs/architecture.md and docs/governance.md, then run the Quickstart and
quality suite to validate end-to-end behavior.
