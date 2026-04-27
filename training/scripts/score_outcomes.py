#!/usr/bin/env python3
"""Score model probabilities against outcomes from a scored holdout CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score outcome metrics")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--label-col", default="IsWon")
    parser.add_argument("--score-col", default="ModelScore")
    parser.add_argument("--output-json", default="training/outputs/outcome_metrics.json")
    return parser.parse_args()


def parse_label(value: Any) -> int | None:
    raw = "" if value is None else str(value).strip().lower()
    if raw in {"1", "true", "yes", "won", "closed won"}:
        return 1
    if raw in {"0", "false", "no", "lost", "closed lost"}:
        return 0
    return None


def main() -> int:
    args = parse_args()
    df = pd.read_csv(args.input_csv)
    df["_label"] = df[args.label_col].map(parse_label)
    df["_score"] = pd.to_numeric(df[args.score_col], errors="coerce")

    valid = df.dropna(subset=["_label", "_score"]).copy()
    if valid.empty:
        raise SystemExit("no valid rows for scoring")

    y_true = valid["_label"].astype(int).to_numpy()
    y_score = valid["_score"].astype(float).clip(0.0, 1.0).to_numpy()

    report = {
        "input_csv": args.input_csv,
        "rows_read": int(len(df)),
        "rows_scored": int(len(valid)),
        "label_col": args.label_col,
        "score_col": args.score_col,
        "metrics": {
            "roc_auc": float(roc_auc_score(y_true, y_score)) if len(set(y_true.tolist())) > 1 else None,
            "pr_auc": float(average_precision_score(y_true, y_score)) if len(set(y_true.tolist())) > 1 else None,
            "brier": float(brier_score_loss(y_true, y_score)),
            "win_rate": float(y_true.mean()),
        },
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))

    print(json.dumps(report, indent=2))
    print(f"report_json={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
