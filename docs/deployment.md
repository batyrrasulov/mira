# Deployment

## Deployment Options

### Option A: API-only mode

Use this mode when you already have a hosted OpenAI-compatible model endpoint.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp configs/app.env.example configs/app.env
bash scripts/run_local_api.sh
```

### Option B: Full backend stack (recommended)

Includes:

- vLLM model server
- Canary proxy
- Mira API

```bash
cp configs/stack.env.example configs/stack.env
scripts/start_backend_stack.sh
```

Compose file: `deploy/compose/docker-compose.backend.yml`

## Required Environment Values

In `configs/stack.env`:

- `BASE_MODEL_ID`
- `BASE_MODEL_NAME`
- `CANARY_MODEL_NAME`
- `CANARY_PERCENT`
- `MIRA_API_KEY` (recommended)

## Health and Readiness Checks

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/ready
curl -sS http://127.0.0.1:8003/health
```

Readiness gate script:

```bash
python scripts/check_llm_readiness.py --base-url http://127.0.0.1:8000 --model qwen2.5-7b-instruct
```

## Promotion Operations

### Roll out canary traffic

```bash
scripts/rollout_canary.sh --percent 25
```

### Roll back to base model

```bash
scripts/rollback_canary.sh
```

### Stop runtime stack

```bash
scripts/stop_backend_stack.sh
```

## Non-NVIDIA Hosts

If Docker does not provide an `nvidia` runtime, use fallback mode:

```bash
MIRA_START_MODE=fallback scripts/start_backend_stack.sh
```

Fallback mode runs Mira API only and enforces `MIRA_FORCE_FALLBACK=true` at startup.
