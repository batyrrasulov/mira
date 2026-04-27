#!/usr/bin/env python3
"""Prepare instruction-tuning JSONL from a Hugging Face dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from datasets import Dataset, load_dataset


SYSTEM_PROMPT = (
    "You are Mira, an educational assistant. Explain clearly, reason step-by-step, "
    "and check for understanding."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build training JSONL from HF dataset")
    parser.add_argument("--dataset-id", default="TIGER-Lab/MathInstruct")
    parser.add_argument("--split", default="train")
    parser.add_argument("--subset", default=None)
    parser.add_argument("--max-samples", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-output", default="training/data/edu_train.jsonl")
    parser.add_argument("--eval-output", default="training/data/edu_eval.jsonl")
    parser.add_argument("--eval-ratio", type=float, default=0.02)
    parser.add_argument("--report-json", default="training/outputs/edu_dataset_report.json")
    return parser.parse_args()


def first_non_empty(example: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = example.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def to_messages(example: dict[str, Any]) -> dict[str, Any] | None:
    prompt = first_non_empty(
        example,
        ["instruction", "question", "query", "prompt", "problem", "input", "user", "text"],
    )
    response = first_non_empty(
        example,
        ["output", "answer", "response", "completion", "assistant", "solution", "target"],
    )

    if not prompt or not response:
        return None

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ]
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def main() -> int:
    args = parse_args()

    ds: Dataset = load_dataset(args.dataset_id, args.subset, split=args.split)
    if args.max_samples > 0 and len(ds) > args.max_samples:
        ds = ds.shuffle(seed=args.seed).select(range(args.max_samples))

    rows: list[dict[str, Any]] = []
    dropped = 0
    for ex in ds:
        mapped = to_messages(ex)
        if mapped is None:
            dropped += 1
            continue
        rows.append(mapped)

    if not rows:
        raise SystemExit("No valid instruction rows were extracted from dataset")

    eval_size = max(1, int(len(rows) * args.eval_ratio))
    train_rows = rows[eval_size:]
    eval_rows = rows[:eval_size]

    write_jsonl(Path(args.train_output), train_rows)
    write_jsonl(Path(args.eval_output), eval_rows)

    report = {
        "dataset_id": args.dataset_id,
        "subset": args.subset,
        "split": args.split,
        "input_rows": len(ds),
        "rows_kept": len(rows),
        "rows_dropped": dropped,
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "train_output": args.train_output,
        "eval_output": args.eval_output,
    }

    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
