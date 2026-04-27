# Get Started: Backend Stack

## 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Configure environment

```bash
cp configs/stack.env.example configs/stack.env
```

Update at least these values in `configs/stack.env`:

- `BASE_MODEL_ID`
- `BASE_MODEL_NAME`
- `CANARY_MODEL_NAME`
- `MIRA_API_KEY` (recommended)
- `VLLM_API_KEY` (optional)

## 3) Launch stack

```bash
scripts/start_backend_stack.sh
```

This brings up:

- NVIDIA host: vLLM (`8000`), canary proxy (`8003`), Mira API (`8080`)
- Non-NVIDIA host: Mira API only (`8080`) in forced fallback mode

Force startup mode explicitly:

```bash
MIRA_START_MODE=gpu scripts/start_backend_stack.sh
MIRA_START_MODE=fallback scripts/start_backend_stack.sh
```

## 4) Verify endpoints

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/ready
```

## 5) Stop stack

```bash
scripts/stop_backend_stack.sh
```
