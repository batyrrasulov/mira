# Troubleshooting

## vLLM does not become ready

- Confirm GPU visibility: `nvidia-smi`
- Reduce memory pressure in `configs/stack.env`:
  - `VLLM_MAX_NUM_SEQS`
  - `VLLM_MAX_NUM_BATCHED_TOKENS`
  - `VLLM_GPU_MEMORY_UTILIZATION`
- Check container logs:

```bash
docker compose --env-file configs/stack.env -f deploy/compose/docker-compose.backend.yml logs -f vllm-main
```

## Canary proxy returns 502

- Verify upstream URL in `configs/stack.env` maps to the active vLLM service.
- Confirm vLLM `/health` endpoint responds with HTTP 200.
- Inspect proxy logs:

```bash
docker compose --env-file configs/stack.env -f deploy/compose/docker-compose.backend.yml logs -f llm-canary-proxy
```

## Adapter training crashes on startup

- Ensure required packages are installed (`transformers`, `peft`, `datasets`, `bitsandbytes`).
- Confirm GPU architecture supports the selected quantization mode.
- Lower `per_device_train_batch_size` in `training/configs/qlora_h100.yaml`.

## Promotion gate fails

- Compare base and canary report metrics in `evaluation/results/adapter_gate_report.json`.
- Re-run evaluation with more prompts to reduce variance.
- Check if the adapter increased latency beyond the ratio threshold.

## API returns auth errors

- If `MIRA_API_KEY` is set, include header:

```text
Authorization: Bearer <MIRA_API_KEY>
```
