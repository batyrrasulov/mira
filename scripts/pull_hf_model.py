#!/usr/bin/env python3
"""Download a model snapshot from Hugging Face Hub for local serving or training."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Hugging Face model weights")
    parser.add_argument("--repo-id", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--local-dir", default="models/base/qwen2.5-7b-instruct")
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--allow-pattern", action="append", default=[])
    parser.add_argument("--ignore-pattern", action="append", default=[])
    parser.add_argument("--report-json", default="training/outputs/hf_pull_report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    token = os.getenv(args.token_env, "").strip() or None

    snapshot_path = snapshot_download(
        repo_id=args.repo_id,
        revision=args.revision,
        local_dir=str(local_dir),
        token=token,
        allow_patterns=args.allow_pattern or None,
        ignore_patterns=args.ignore_pattern or None,
        resume_download=True,
    )

    report = {
        "repo_id": args.repo_id,
        "revision": args.revision,
        "local_dir": str(local_dir),
        "snapshot_path": snapshot_path,
        "allow_patterns": args.allow_pattern,
        "ignore_patterns": args.ignore_pattern,
    }

    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
