#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="${ROOT_DIR}/training/configs/qlora_h100.yaml"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Missing config: ${CONFIG_FILE}" >&2
  exit 1
fi

cd "${ROOT_DIR}"

echo "[pipeline] step 1/5: pull base model"
python scripts/pull_hf_model.py \
  --repo-id "Qwen/Qwen2.5-7B-Instruct" \
  --local-dir models/base/qwen2.5-7b-instruct

echo "[pipeline] step 2/5: prepare HF dataset"
python training/scripts/prepare_hf_dataset.py \
  --dataset-id "TIGER-Lab/MathInstruct" \
  --split train \
  --max-samples 20000 \
  --train-output training/data/edu_train.jsonl \
  --eval-output training/data/edu_eval.jsonl \
  --report-json training/outputs/edu_dataset_report.json

echo "[pipeline] step 3/5: train QLoRA adapter"
python training/scripts/train_lora_adapter.py --config-yaml "${CONFIG_FILE}"

echo "[pipeline] step 4/5: merge adapter"
python training/scripts/merge_lora_adapter.py \
  --base-model-id "Qwen/Qwen2.5-7B-Instruct" \
  --adapter-path training/outputs/qwen25_edu_qlora_adapter \
  --output-dir models/merged/qwen25_edu_merged \
  --report-json training/outputs/qwen25_edu_merge_report.json

echo "[pipeline] step 5/5: optional serving/evaluation"
if [[ "${RUN_SERVING_GATE:-false}" == "true" ]]; then
  scripts/start_backend_stack.sh
  python evaluation/run_adapter_gate.py \
    --base-url "http://127.0.0.1:8003" \
    --base-model "qwen2.5-7b-instruct" \
    --canary-model "qwen2.5-7b-instruct-edu-lora" \
    --prompts-file evaluation/prompts/sample_prompts.jsonl \
    --output-json evaluation/results/adapter_gate_report.json
else
  echo "[pipeline] skipping RUN_SERVING_GATE. Set RUN_SERVING_GATE=true to run promotion gate."
fi

echo "[pipeline] complete"
