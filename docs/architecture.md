# Architecture

Mira is organized as a model-lifecycle backend system with separate planes for serving, gating, and training.

## Control Plane

- `deploy/compose/docker-compose.backend.yml` defines runtime topology.
- `scripts/start_backend_stack.sh` and `scripts/stop_backend_stack.sh` provide stack lifecycle control.
- `scripts/rollout_canary.sh` and `scripts/rollback_canary.sh` control traffic promotion.

## Runtime Plane

### 1) Mira API (`src/mira/api.py`)

- Exposes OpenAI-compatible endpoints (`/v1/chat/completions`, `/v1/completions`).
- Applies auth checks, schema validation, and guardrails.
- Normalizes generated output into a stable educational JSON contract.

### 2) Canary Proxy (`scripts/llm_canary_proxy.py`)

- Routes each request to base or canary model.
- Uses deterministic hashing for reproducible traffic split.
- Exposes route metadata headers for observability.

### 3) vLLM Inference (`scripts/run_vllm_server.py`)

- Serves base and merged model weights through OpenAI-compatible APIs.
- Uses environment-driven performance and memory controls.

## Training Plane

### Dataset and Adaptation

- `training/scripts/prepare_hf_dataset.py`: converts HF dataset records to chat training JSONL.
- `training/scripts/train_lora_adapter.py`: runs LoRA/QLoRA fine-tuning.
- `training/scripts/merge_lora_adapter.py`: merges adapter into full model weights.

### Evaluation and Promotion

- `evaluation/run_adapter_gate.py` compares base vs canary quality/latency.
- Promotion gates block rollout on quality regression or latency spikes.

## Request Lifecycle

1. Client calls Mira API.
2. Guardrails and auth checks execute.
3. API calls configured upstream endpoint (proxy or provider).
4. Canary proxy chooses base or canary model.
5. vLLM generates completion.
6. API normalizes response to LMS-safe contract.
7. Client receives OpenAI-compatible response payload.

## Diagram

See [docs/reference/technical_diagram.md](docs/reference/technical_diagram.md) for a full flow diagram.
