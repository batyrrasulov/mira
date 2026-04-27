#!/usr/bin/env python3
"""Train a lightweight structured predictor with temporal holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DEFAULT_CATEGORICAL = ["StageName", "ForecastCategory", "Type", "LeadSource", "Primary_Competitor__c"]
DEFAULT_NUMERIC = ["Probability", "Amount", "OpportunityAgeDays", "HorizonDays", "HistoryRowsUpToSnapshot"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train structured model")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--label-col", default="IsWon")
    parser.add_argument("--snapshot-col", default="SnapshotDate")
    parser.add_argument("--holdout-fraction", type=float, default=0.3)
    parser.add_argument("--categorical-cols", default=",".join(DEFAULT_CATEGORICAL))
    parser.add_argument("--numeric-cols", default=",".join(DEFAULT_NUMERIC))
    parser.add_argument("--output-model", default="training/outputs/structured_model.joblib")
    parser.add_argument("--output-scored-csv", default="training/outputs/structured_holdout_scored.csv")
    parser.add_argument("--output-report", default="training/outputs/structured_training_report.json")
    return parser.parse_args()


def parse_label(value: Any) -> int | None:
    raw = "" if value is None else str(value).strip().lower()
    if raw in {"1", "true", "yes", "won", "closed won"}:
        return 1
    if raw in {"0", "false", "no", "lost", "closed lost"}:
        return 0
    return None


def parse_score(value: Any) -> float | None:
    raw = "" if value is None else str(value).strip().replace(",", "")
    if not raw:
        return None
    try:
        score = float(raw)
    except ValueError:
        return None
    if score > 1.0:
        score /= 100.0
    return max(0.0, min(1.0, score))


def main() -> int:
    args = parse_args()
    cat_cols = [c.strip() for c in args.categorical_cols.split(",") if c.strip()]
    num_cols = [c.strip() for c in args.numeric_cols.split(",") if c.strip()]
    feature_cols = cat_cols + num_cols

    df = pd.read_csv(args.input_csv)
    rows_read = len(df)
    if rows_read < 6:
        raise SystemExit("need at least 6 rows to run temporal split")

    for col in feature_cols:
        if col not in df.columns:
            df[col] = np.nan

    df["_snapshot_dt"] = pd.to_datetime(df[args.snapshot_col], errors="coerce", utc=True)
    df["_label"] = df[args.label_col].map(parse_label)
    df["_baseline"] = df.get("Probability", pd.Series([None] * len(df))).map(parse_score)

    for col in num_cols:
        cleaned = df[col].astype(str).str.replace(",", "", regex=False).str.strip()
        cleaned = cleaned.replace({"": np.nan, "None": np.nan, "nan": np.nan})
        df[col] = pd.to_numeric(cleaned, errors="coerce")

    df = df.dropna(subset=["_snapshot_dt", "_label"]).sort_values("_snapshot_dt").reset_index(drop=True)
    if len(df) < 6:
        raise SystemExit("not enough usable rows after cleaning")

    holdout_fraction = float(np.clip(args.holdout_fraction, 0.2, 0.5))
    holdout_start = max(1, min(len(df) - 1, int(len(df) * (1.0 - holdout_fraction))))

    train_df = df.iloc[:holdout_start].copy()
    holdout_df = df.iloc[holdout_start:].copy()

    if train_df["_label"].nunique() < 2:
        raise SystemExit("training split has a single class")

    preprocess = ColumnTransformer(
        transformers=[
            ("num", Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler(with_mean=False))]), num_cols),
            ("cat", Pipeline(steps=[("imputer", SimpleImputer(strategy="most_frequent")), ("encoder", OneHotEncoder(handle_unknown="ignore"))]), cat_cols),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocess", preprocess),
            ("logreg", LogisticRegression(solver="liblinear", class_weight="balanced", max_iter=2000)),
        ]
    )

    x_train = train_df[feature_cols]
    y_train = train_df["_label"].astype(int).to_numpy()
    x_holdout = holdout_df[feature_cols]
    y_holdout = holdout_df["_label"].astype(int).to_numpy()

    model.fit(x_train, y_train)
    holdout_scores = model.predict_proba(x_holdout)[:, 1]
    holdout_df["ModelScore"] = holdout_scores

    baseline_mask = holdout_df["_baseline"].notna().to_numpy()
    baseline_y = y_holdout[baseline_mask]
    baseline_scores = holdout_df.loc[baseline_mask, "_baseline"].to_numpy(dtype=float)

    report = {
        "input_csv": args.input_csv,
        "rows_read": rows_read,
        "rows_used": len(df),
        "train_rows": len(train_df),
        "holdout_rows": len(holdout_df),
        "categorical_cols": cat_cols,
        "numeric_cols": num_cols,
        "metrics": {
            "model": {
                "roc_auc": float(roc_auc_score(y_holdout, holdout_scores)) if len(np.unique(y_holdout)) > 1 else None,
                "pr_auc": float(average_precision_score(y_holdout, holdout_scores)) if len(np.unique(y_holdout)) > 1 else None,
                "brier": float(brier_score_loss(y_holdout, holdout_scores)),
            },
            "baseline_probability": {
                "rows": int(len(baseline_y)),
                "roc_auc": float(roc_auc_score(baseline_y, baseline_scores)) if len(baseline_y) > 1 and len(np.unique(baseline_y)) > 1 else None,
                "pr_auc": float(average_precision_score(baseline_y, baseline_scores)) if len(baseline_y) > 1 and len(np.unique(baseline_y)) > 1 else None,
                "brier": float(brier_score_loss(baseline_y, baseline_scores)) if len(baseline_y) > 0 else None,
            },
        },
    }

    model_path = Path(args.output_model)
    scored_path = Path(args.output_scored_csv)
    report_path = Path(args.output_report)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    scored_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump({"pipeline": model, "feature_columns": feature_cols, "metadata": report}, model_path)
    holdout_df.to_csv(scored_path, index=False)
    report_path.write_text(json.dumps(report, indent=2))

    print(json.dumps(report, indent=2))
    print(f"model_artifact={model_path}")
    print(f"scored_holdout={scored_path}")
    print(f"report_json={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
