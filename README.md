# Mira

Mira is a production-style learning assistant backend with an OpenAI-compatible API,
provider-backed generation, guardrails, and a reproducible training/evaluation workflow.

## What Works Today

- OpenAI-compatible endpoints:
  - POST /v1/chat/completions
  - POST /v1/completions
- Strict response contract for LMS parsing
- Optional inbound API key protection
- Provider mode (real upstream LLM) with automatic safe fallback
- Readiness and health endpoints
- Structured baseline training + scoring pipeline
- Quality suite for contract, keyword, and latency checks

## Quick Start

### 1) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure

```bash
cp configs/app.env.example configs/app.env
```

### 3) Run API

```bash
bash scripts/run_local_api.sh
```

### 4) Verify

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/ready
```

## Run With A Real Upstream Model

Set these values in configs/app.env:

- MIRA_LLM_BASE_URL
- MIRA_LLM_MODEL
- MIRA_LLM_API_KEY (if required by provider)

Optional:

- MIRA_UPSTREAM_CHAT_ENDPOINT (default: /v1/chat/completions)
- MIRA_PROVIDER_TEMPERATURE
- MIRA_FORCE_FALLBACK

Example request:

```bash
curl -sS http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mira-edu-assistant",
    "messages": [{"role": "user", "content": "Explain Bayes rule with an example."}],
    "max_tokens": 220,
    "temperature": 0
  }'
```

If MIRA_API_KEY is set, include:

```bash
-H "Authorization: Bearer <your-key>"
```

## End-to-End Workflow

### Train structured baseline

```bash
python training/scripts/build_dataset.py \
  --input-csv training/data/sample_outcomes.csv \
  --output-jsonl training/outputs/sft_bootstrap.jsonl \
  --report-json training/outputs/sft_build_report.json

python training/scripts/train_structured_model.py \
  --input-csv training/data/sample_outcomes.csv \
  --output-model training/outputs/structured_model.joblib \
  --output-scored-csv training/outputs/structured_holdout_scored.csv \
  --output-report training/outputs/structured_training_report.json

python training/scripts/score_outcomes.py \
  --input-csv training/outputs/structured_holdout_scored.csv \
  --score-col ModelScore \
  --output-json training/outputs/outcome_metrics.json
```

### Run API quality checks

```bash
python evaluation/run_quality_suite.py \
  --base-url http://127.0.0.1:8080 \
  --prompts-file evaluation/prompts/sample_prompts.jsonl \
  --output-json evaluation/results/quality_suite_report.json
```

## Repository Map

- Core API: [src/mira/api.py](src/mira/api.py)
- Provider client: [src/mira/llm_client.py](src/mira/llm_client.py)
- Contract normalization: [src/mira/contract.py](src/mira/contract.py)
- Guardrails: [src/mira/guardrails.py](src/mira/guardrails.py)
- Settings: [src/mira/settings.py](src/mira/settings.py)
- Training scripts: [training/scripts](training/scripts)
- Evaluation suite: [evaluation/run_quality_suite.py](evaluation/run_quality_suite.py)
- Deployment notes: [docs/deployment.md](docs/deployment.md)
- Architecture notes: [docs/architecture.md](docs/architecture.md)

## Commands

```bash
pytest -q
python -m py_compile src/mira/*.py training/scripts/*.py evaluation/*.py
```

## License

MIT. See [LICENSE](LICENSE).
