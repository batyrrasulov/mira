# Training Workflow

This folder contains a starter, research-friendly training workflow for an
education-focused assistant.

## Files

- training/data/sample_outcomes.csv: synthetic structured sample data
- training/scripts/build_dataset.py: CSV to SFT JSONL conversion
- training/scripts/train_structured_model.py: temporal holdout logistic baseline
- training/scripts/score_outcomes.py: post-train metric summary
- training/outputs/: generated artifacts (ignored except .gitkeep)

## Quickstart

1) Build SFT-ready records:

```bash
python training/scripts/build_dataset.py \
  --input-csv training/data/sample_outcomes.csv \
  --output-jsonl training/outputs/sft_bootstrap.jsonl \
  --report-json training/outputs/sft_build_report.json
```

2) Train structured baseline:

```bash
python training/scripts/train_structured_model.py \
  --input-csv training/data/sample_outcomes.csv \
  --output-model training/outputs/structured_model.joblib \
  --output-scored-csv training/outputs/structured_holdout_scored.csv \
  --output-report training/outputs/structured_training_report.json
```

3) Score holdout predictions:

```bash
python training/scripts/score_outcomes.py \
  --input-csv training/outputs/structured_holdout_scored.csv \
  --score-col ModelScore \
  --output-json training/outputs/outcome_metrics.json
```

## Notes

- The sample CSV is synthetic and intended for repository demonstration.
- Replace sample data with institution-approved anonymized datasets.
- Keep data governance controls in place before introducing real student data.
