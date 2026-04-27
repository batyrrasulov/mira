# Training Workflow

This directory contains a reproducible structured-baseline workflow.

## Contents

- Sample data: training/data/sample_outcomes.csv
- Dataset builder: training/scripts/build_dataset.py
- Model trainer: training/scripts/train_structured_model.py
- Outcome scorer: training/scripts/score_outcomes.py
- Generated artifacts: training/outputs/

## Run Sequence

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

## Expected Outputs

- sft_bootstrap.jsonl
- sft_build_report.json
- structured_model.joblib
- structured_holdout_scored.csv
- structured_training_report.json
- outcome_metrics.json
