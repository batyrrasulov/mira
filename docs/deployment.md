# Deployment Guide

## Local Development

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment:

```bash
cp configs/app.env.example configs/app.env
```

4. Run API:

```bash
bash scripts/run_local_api.sh
```

5. Health check:

```bash
curl -sS http://127.0.0.1:8080/health
```

## Containerization (Suggested)

A simple container can be built around uvicorn + src package.
Use environment variables for runtime limits and model provider details.

## LMS Integration Pattern

- LMS tool/plug-in calls /v1/chat/completions.
- Enforce strict_json_mode for deterministic response parsing.
- Render fields such as learning_goal and guided_steps in UI.

## Production Hardening Checklist

- Add auth (gateway token or mTLS)
- Add request ID tracing
- Add structured logs and alert hooks
- Add explicit rate limiting and abuse controls
- Add provider fallback strategy
