#!/usr/bin/env python3
"""Build a leakage-aware SFT dataset from structured opportunity snapshots."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

LEAKAGE_KEYS = {
    "IsWon",
    "CloseDate",
    "LossReason",
    "WinReason",
    "NXT_Win_Strategy__c",
    "Loss_Reason__c",
    "NXT_Rejection_Reason__c",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SFT dataset from structured CSV")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--report-json", default="")
    parser.add_argument("--id-col", default="OpportunityId")
    parser.add_argument("--label-col", default="IsWon")
    parser.add_argument("--max-rows", type=int, default=0)
    return parser.parse_args()


def parse_label(value: str) -> bool | None:
    raw = "" if value is None else str(value).strip().lower()
    if raw in {"1", "true", "yes", "won", "closed won"}:
        return True
    if raw in {"0", "false", "no", "lost", "closed lost"}:
        return False
    return None


def compact_context(row: dict[str, str]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for key, value in row.items():
        if key in LEAKAGE_KEYS:
            continue
        text = (value or "").strip()
        if text:
            context[key] = text
    return context


def main() -> int:
    args = parse_args()
    in_path = Path(args.input_csv)
    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    report = {
        "input_csv": str(in_path),
        "output_jsonl": str(out_path),
        "rows_read": 0,
        "rows_written": 0,
        "rows_skipped_missing_id": 0,
        "rows_skipped_missing_label": 0,
    }

    with in_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            if args.max_rows > 0 and len(records) >= args.max_rows:
                break
            report["rows_read"] += 1

            opportunity_id = (row.get(args.id_col) or "").strip()
            if not opportunity_id:
                report["rows_skipped_missing_id"] += 1
                continue

            label = parse_label(row.get(args.label_col, ""))
            if label is None:
                report["rows_skipped_missing_label"] += 1
                continue

            context = compact_context(row)
            payload = {
                "win_probability_band": "high" if label else "low",
                "confidence": 0.75 if label else 0.35,
                "risk_narrative": "Signals suggest a strong path to close." if label else "Signals suggest unresolved blockers before close.",
                "top_drivers": [
                    f"StageName={context.get('StageName', '')}",
                    f"Probability={context.get('Probability', '')}",
                    f"ForecastCategory={context.get('ForecastCategory', '')}",
                ],
                "recommended_actions": [
                    "Verify core assumptions with course-approved methodology.",
                    "Document one improvement action with owner and date.",
                ],
            }

            records.append(
                {
                    "id": f"mira-{opportunity_id}-{idx}",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a learning assistant focused on guidance and concept mastery.",
                        },
                        {
                            "role": "user",
                            "content": (
                                "Analyze this learning snapshot and return strict JSON with keys "
                                "win_probability_band, confidence, risk_narrative, top_drivers, recommended_actions.\n"
                                f"snapshot={json.dumps(context, ensure_ascii=True)}"
                            ),
                        },
                        {"role": "assistant", "content": json.dumps(payload, ensure_ascii=True)},
                    ],
                    "metadata": {
                        "source": "structured_sample",
                        "snapshot_id": opportunity_id,
                        "label_is_won": label,
                    },
                }
            )

    with out_path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    report["rows_written"] = len(records)

    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
