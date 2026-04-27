#!/usr/bin/env python3
"""Compare base and canary served models and enforce promotion gates."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run model promotion gate")
    parser.add_argument("--base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--endpoint", default="/v1/chat/completions")
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--canary-model", required=True)
    parser.add_argument("--prompts-file", default="evaluation/prompts/sample_prompts.jsonl")
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--required-keyword-gain", type=float, default=0.02)
    parser.add_argument("--max-latency-ratio", type=float, default=1.25)
    parser.add_argument("--output-json", default="evaluation/results/adapter_gate_report.json")
    return parser.parse_args()


def load_prompts(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    if not rows:
        raise SystemExit("No prompts found")
    return rows


def keyword_hit_ratio(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    lowered = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in lowered)
    return hits / float(len(keywords))


def request_completion(
    url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout_s: float,
    route: str,
) -> tuple[str, float, int]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Canary-Route": route,
        },
    )

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            latency_s = time.time() - start
            content = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return str(content), latency_s, int(resp.status)
    except urllib.error.HTTPError as exc:
        latency_s = time.time() - start
        return f"HTTP {exc.code}", latency_s, int(exc.code)


def score_model(
    url: str,
    model: str,
    prompts: list[dict[str, Any]],
    max_tokens: int,
    timeout_s: float,
    route: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    hits: list[float] = []
    status_200 = 0

    for row in prompts:
        prompt = str(row.get("prompt", "")).strip()
        keywords = row.get("expected_keywords") or row.get("required_keywords") or []
        if not isinstance(keywords, list):
            keywords = []

        answer, latency_s, status = request_completion(url, model, prompt, max_tokens, timeout_s, route)
        hit = keyword_hit_ratio(answer, [str(x) for x in keywords])

        latencies.append(latency_s)
        hits.append(hit)
        if status == 200:
            status_200 += 1

        rows.append(
            {
                "id": row.get("id"),
                "status": status,
                "latency_s": latency_s,
                "keyword_hit": hit,
            }
        )

    total = len(rows)
    return {
        "model": model,
        "route": route,
        "prompts_evaluated": total,
        "status_200_rate": status_200 / total if total else 0.0,
        "keyword_hit_avg": sum(hits) / total if total else 0.0,
        "latency_avg_s": sum(latencies) / total if total else 0.0,
        "rows": rows,
    }


def main() -> int:
    args = parse_args()
    prompts = load_prompts(args.prompts_file)
    url = f"{args.base_url.rstrip('/')}{args.endpoint}"

    base = score_model(url, args.base_model, prompts, args.max_tokens, args.timeout_s, route="base")
    canary = score_model(url, args.canary_model, prompts, args.max_tokens, args.timeout_s, route="canary")

    keyword_gain = canary["keyword_hit_avg"] - base["keyword_hit_avg"]
    latency_ratio = canary["latency_avg_s"] / base["latency_avg_s"] if base["latency_avg_s"] > 0 else 999.0

    passed = (
        base["status_200_rate"] >= 0.95
        and canary["status_200_rate"] >= 0.95
        and keyword_gain >= args.required_keyword_gain
        and latency_ratio <= args.max_latency_ratio
    )

    report = {
        "status": "pass" if passed else "fail",
        "base_model": args.base_model,
        "canary_model": args.canary_model,
        "keyword_gain": keyword_gain,
        "latency_ratio": latency_ratio,
        "required_keyword_gain": args.required_keyword_gain,
        "max_latency_ratio": args.max_latency_ratio,
        "base": base,
        "canary": canary,
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
