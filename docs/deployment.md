# Deployment

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp configs/app.env.example configs/app.env
bash scripts/run_local_api.sh
```

## Minimum Environment

- MIRA_HOST
- MIRA_PORT
- MIRA_MAX_INPUT_CHARS
- MIRA_MAX_OUTPUT_TOKENS
- MIRA_MIN_OUTPUT_TOKENS

## Provider Mode Configuration

Set these in configs/app.env:

- MIRA_LLM_BASE_URL
- MIRA_LLM_MODEL
- MIRA_LLM_API_KEY (if needed)

Optional:

- MIRA_UPSTREAM_CHAT_ENDPOINT
- MIRA_PROVIDER_TEMPERATURE
- MIRA_FORCE_FALLBACK

## Security Controls

- Set MIRA_API_KEY to require Bearer auth on write endpoints.
- Keep provider keys out of git and local shell history where possible.
- Restrict network access to trusted clients only.

## Health and Readiness

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/ready
```

Use readiness in orchestration checks before promoting traffic.
