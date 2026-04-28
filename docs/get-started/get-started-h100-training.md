# Get Started: H100 Training Pipeline

## 1) Prepare Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Build dataset from Hugging Face

```bash
python training/scripts/prepare_hf_dataset.py \
  --dataset-id TIGER-Lab/MathInstruct \
  --split train \
  --max-samples 20000 \
  --train-output training/data/edu_train.jsonl \
  --eval-output training/data/edu_eval.jsonl
```

## 3) Train QLoRA adapter

```bash
python training/scripts/train_lora_adapter.py \
  --config-yaml training/configs/qlora_h100.yaml
```

## 4) Merge adapter into base model weights

```bash
python training/scripts/merge_lora_adapter.py \
  --base-model-id Qwen/Qwen2.5-7B-Instruct \
  --adapter-path training/outputs/qwen25_edu_qlora_adapter \
  --output-dir models/merged/qwen25_edu_merged
```

## 5) Evaluate and gate promotion

```bash
python evaluation/run_adapter_gate.py \
  --base-url http://127.0.0.1:8003 \
  --base-model qwen2.5-7b-instruct \
  --canary-model qwen2.5-7b-instruct-edu-lora \
  --prompts-file evaluation/prompts/sample_prompts.jsonl
```

A non-zero exit code means the adapter failed promotion thresholds.

## One-command pipeline

```bash
training/scripts/run_full_pipeline.sh
```

Set `RUN_SERVING_GATE=true` to include serving and gate checks in the same run.

When serving is requested from a host that starts in fallback mode (API only, no canary proxy), the gate step is skipped and reported explicitly.
