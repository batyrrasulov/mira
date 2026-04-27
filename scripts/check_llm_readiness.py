#!/usr/bin/env python3
"""Readiness probe for OpenAI-compatible vLLM endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def request_json(url: str, payload: dict[str, Any] | None, timeout_s: float, api_key: str) -> tuple[int, str]:
    headers: dict[str, str] = {}
    data: bytes | None = None

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")

    req = urllib.request.Request(url=url, headers=headers, data=data)
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return int(resp.status), resp.read().decode("utf-8")


def probe_health(base_url: str, timeout_s: float, api_key: str) -> tuple[bool, str]:
    try:
        status, body = request_json(f"{base_url}/health", None, timeout_s, api_key)
        if status != 200:
            return False, f"/health returned {status}"
        return True, body
    except Exception as exc:  # noqa: BLE001
        return False, f"health probe failed: {type(exc).__name__}: {exc}"


def probe_generation(base_url: str, model: str, timeout_s: float, api_key: str) -> tuple[bool, str]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "reply with: ok"}],
        "max_tokens": 8,
        "temperature": 0.0,
    }
    try:
        status, body = request_json(f"{base_url}/v1/chat/completions", payload, timeout_s, api_key)
        if status != 200:
            return False, f"generation returned {status}"
        parsed = json.loads(body)
        if not isinstance(parsed, dict) or "choices" not in parsed:
            return False, "generation response missing choices"
        return True, "ok"
    except urllib.error.HTTPError as exc:
        return False, f"generation HTTP error {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"generation probe failed: {type(exc).__name__}: {exc}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="vLLM readiness probe")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default=os.getenv("BASE_MODEL_NAME", "qwen2.5-7b-instruct"))
    parser.add_argument("--api-key", default=os.getenv("VLLM_API_KEY", ""))
    parser.add_argument("--timeout-s", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=20)
    parser.add_argument("--retry-delay-s", type=float, default=3.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    for attempt in range(1, args.retries + 1):
        start = time.time()

        ok_health, health_msg = probe_health(base_url, args.timeout_s, args.api_key)
        if not ok_health:
            elapsed = time.time() - start
            print(f"[readiness] attempt={attempt} health=fail elapsed_s={elapsed:.3f} msg={health_msg}")
            if attempt < args.retries:
                time.sleep(args.retry_delay_s)
            continue

        ok_gen, gen_msg = probe_generation(base_url, args.model, args.timeout_s, args.api_key)
        elapsed = time.time() - start
        if ok_gen:
            print(f"[readiness] attempt={attempt} status=ready elapsed_s={elapsed:.3f}")
            return 0

        print(f"[readiness] attempt={attempt} generation=fail elapsed_s={elapsed:.3f} msg={gen_msg}")
        if attempt < args.retries:
            time.sleep(args.retry_delay_s)

    print("[readiness] status=not_ready")
    return 1


if __name__ == "__main__":
    sys.exit(main())
