#!/usr/bin/env python3
"""Merge LoRA adapter with base model and export weights for vLLM serving."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge LoRA adapter into base model")
    parser.add_argument("--base-model-id", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--adapter-path", default="training/outputs/qwen25_edu_qlora_adapter")
    parser.add_argument("--output-dir", default="models/merged/qwen25_edu_merged")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--report-json", default="training/outputs/qwen25_edu_merge_report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    base = AutoModelForCausalLM.from_pretrained(
        args.base_model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=args.trust_remote_code,
    )

    merged = PeftModel.from_pretrained(base, args.adapter_path)
    merged = merged.merge_and_unload()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(output_dir, safe_serialization=True, max_shard_size="4GB")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model_id, trust_remote_code=args.trust_remote_code)
    tokenizer.save_pretrained(output_dir)

    report = {
        "base_model_id": args.base_model_id,
        "adapter_path": args.adapter_path,
        "output_dir": str(output_dir),
        "safe_serialization": True,
        "max_shard_size": "4GB",
    }

    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
