#!/usr/bin/env python3
"""Run a lightweight quality suite against the local Mira API."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REQUIRED_KEYS = {
    "learning_goal",
    "explanation",
    "guided_steps",
    "check_for_understanding",
    "policy_note",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run quality suite")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="mira-edu-assistant")
    parser.add_argument("--prompts-file", default="evaluation/prompts/sample_prompts.jsonl")
    parser.add_argument("--max-prompts", type=int, default=0)
    parser.add_argument("--timeout-s", type=float, default=20.0)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--output-json", default="evaluation/results/quality_suite_report.json")
    return parser.parse_args()


def keyword_hit_ratio(text: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 0.0
    lower = text.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in lower)
    return hits / len(expected_keywords)


def post_chat(base_url: str, model: str, prompt: str, max_tokens: int, timeout_s: float) -> tuple[int, dict[str, Any], float, str]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
            latency_s = time.time() - start
            return int(resp.status), body, latency_s, ""
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        latency_s = time.time() - start
        return int(exc.code), {}, latency_s, raw[:240]
    except Exception as exc:  # noqa: BLE001
        latency_s = time.time() - start
        return 0, {}, latency_s, f"{type(exc).__name__}: {exc}"


def parse_prompts(path: Path, max_prompts: int) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if max_prompts > 0:
        return rows[:max_prompts]
    return rows


def main() -> int:
    args = parse_args()
    prompts = parse_prompts(Path(args.prompts_file), args.max_prompts)

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    keyword_scores: list[float] = []
    contract_pass = 0

    for item in prompts:
        prompt = str(item.get("prompt", ""))
        expected = list(item.get("expected_keywords", []))
        status, body, latency_s, error = post_chat(
            base_url=args.base_url,
            model=args.model,
            prompt=prompt,
            max_tokens=args.max_tokens,
            timeout_s=args.timeout_s,
        )

        row: dict[str, Any] = {
            "id": item.get("id", ""),
            "status": status,
            "latency_s": round(latency_s, 4),
            "error": error,
        }
        latencies.append(latency_s)

        content = ""
        choices = body.get("choices", []) if isinstance(body, dict) else []
        if choices:
            content = str(choices[0].get("message", {}).get("content", ""))

        row["response"] = content
        row["keyword_hit"] = round(keyword_hit_ratio(content, expected), 4)
        keyword_scores.append(row["keyword_hit"])

        contract_ok = False
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and REQUIRED_KEYS.issubset(parsed.keys()):
                contract_ok = True
        except Exception:
            contract_ok = False

        row["contract_ok"] = contract_ok
        if contract_ok:
            contract_pass += 1

        rows.append(row)

    total = len(rows)
    report = {
        "base_url": args.base_url,
        "model": args.model,
        "prompts_evaluated": total,
        "summary": {
            "status_200_rate": round(sum(1 for row in rows if row["status"] == 200) / total, 4) if total else 0.0,
            "contract_pass_rate": round(contract_pass / total, 4) if total else 0.0,
            "keyword_hit_avg": round(statistics.mean(keyword_scores), 4) if keyword_scores else 0.0,
            "latency_avg_s": round(statistics.mean(latencies), 4) if latencies else 0.0,
        },
        "rows": rows,
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))

    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    print(f"report_file={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
