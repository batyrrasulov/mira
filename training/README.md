# Training Workflow

This directory supports two complementary training tracks.

## Track A: Structured Baseline (tabular)

Use this track for deterministic baseline modeling and score calibration.

### Structured Scripts

- `training/scripts/build_dataset.py`
- `training/scripts/train_structured_model.py`
- `training/scripts/score_outcomes.py`

### Structured Commands

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

## Track B: LoRA/QLoRA Adapter (H100 profile)

Use this track for LLM adaptation against education-oriented instruction data.

### LLM Adaptation Scripts

- `training/scripts/prepare_hf_dataset.py`
- `training/scripts/train_lora_adapter.py`
- `training/scripts/merge_lora_adapter.py`
- `training/scripts/run_full_pipeline.sh`

### Config

- `training/configs/qlora_h100.yaml`

### LLM Adaptation Commands

```bash
python training/scripts/prepare_hf_dataset.py \
  --dataset-id TIGER-Lab/MathInstruct \
  --split train \
  --max-samples 20000 \
  --train-output training/data/edu_train.jsonl \
  --eval-output training/data/edu_eval.jsonl

python training/scripts/train_lora_adapter.py \
  --config-yaml training/configs/qlora_h100.yaml

python training/scripts/merge_lora_adapter.py \
  --base-model-id Qwen/Qwen2.5-7B-Instruct \
  --adapter-path training/outputs/qwen25_edu_qlora_adapter \
  --output-dir models/merged/qwen25_edu_merged
```

### Optional one-shot run

```bash
training/scripts/run_full_pipeline.sh
```

Set `RUN_SERVING_GATE=true` to include serving startup and promotion gate evaluation.
