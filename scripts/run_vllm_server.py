#!/usr/bin/env python3
"""Launch vLLM OpenAI server with env-driven configuration."""

from __future__ import annotations

import os
import shlex
import sys
from typing import Any


def env_str(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value if value else default


def env_float(name: str, default: float) -> str:
    raw = os.getenv(name, str(default)).strip()
    try:
        return str(float(raw))
    except ValueError as exc:
        raise SystemExit(f"Invalid float for {name}: {raw}") from exc


def env_int(name: str, default: int) -> str:
    raw = os.getenv(name, str(default)).strip()
    try:
        return str(int(raw))
    except ValueError as exc:
        raise SystemExit(f"Invalid int for {name}: {raw}") from exc


def append_arg(cmd: list[str], flag: str, value: str) -> None:
    if value:
        cmd.extend([flag, value])


def main() -> int:
    model_id = env_str("BASE_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
    served_name = env_str("BASE_MODEL_NAME", "qwen2.5-7b-instruct")
    host = env_str("VLLM_HOST", "0.0.0.0")
    port = env_int("VLLM_PORT", 8000)
    dtype = env_str("VLLM_DTYPE", "bfloat16")
    max_model_len = env_int("VLLM_MAX_MODEL_LEN", 8192)
    gpu_mem = env_float("VLLM_GPU_MEMORY_UTILIZATION", 0.92)
    max_num_seqs = env_int("VLLM_MAX_NUM_SEQS", 64)
    max_num_batched_tokens = env_int("VLLM_MAX_NUM_BATCHED_TOKENS", 8192)
    api_key = os.getenv("VLLM_API_KEY", "").strip()
    extra_args = os.getenv("VLLM_EXTRA_ARGS", "").strip()

    cmd = [
        "vllm",
        "serve",
        model_id,
        "--served-model-name",
        served_name,
        "--host",
        host,
        "--port",
        port,
        "--dtype",
        dtype,
        "--max-model-len",
        max_model_len,
        "--gpu-memory-utilization",
        gpu_mem,
        "--max-num-seqs",
        max_num_seqs,
        "--max-num-batched-tokens",
        max_num_batched_tokens,
    ]

    append_arg(cmd, "--api-key", api_key)

    if extra_args:
        cmd.extend(shlex.split(extra_args))

    preview: list[str] = []
    skip_next = False
    for i, token in enumerate(cmd):
        if skip_next:
            skip_next = False
            continue
        if token == "--api-key" and i + 1 < len(cmd):
            preview.extend(["--api-key", "***"])
            skip_next = True
        else:
            preview.append(token)

    print("Launching vLLM:")
    print(" ".join(shlex.quote(part) for part in preview), flush=True)

    os.execvp(cmd[0], cmd)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Fatal launcher error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
