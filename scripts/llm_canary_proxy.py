#!/usr/bin/env python3
"""OpenAI-compatible canary proxy for base vs adapter model routing."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mira.guardrails import GuardrailConfig, validate_payload  # noqa: E402


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError:
        return default


def bounded_percent(value: float) -> float:
    return max(0.0, min(100.0, value))


@dataclass(frozen=True)
class ProxyConfig:
    listen_host: str
    listen_port: int
    upstream_base_url: str
    base_model_name: str
    canary_model_name: str
    canary_percent: float
    hash_header: str
    upstream_timeout_s: int
    enable_guardrails: bool
    guardrails: GuardrailConfig


CONFIG = ProxyConfig(
    listen_host=os.getenv("LISTEN_HOST", "0.0.0.0").strip() or "0.0.0.0",
    listen_port=env_int("LISTEN_PORT", 8003),
    upstream_base_url=os.getenv("UPSTREAM_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/"),
    base_model_name=os.getenv("BASE_MODEL_NAME", "qwen2.5-7b-instruct").strip() or "qwen2.5-7b-instruct",
    canary_model_name=os.getenv("CANARY_MODEL_NAME", "qwen2.5-7b-instruct-edu-lora").strip()
    or "qwen2.5-7b-instruct-edu-lora",
    canary_percent=bounded_percent(env_float("CANARY_PERCENT", 10.0)),
    hash_header=os.getenv("CANARY_HASH_HEADER", "x-canary-key").strip().lower() or "x-canary-key",
    upstream_timeout_s=env_int("PROXY_TIMEOUT_S", 60),
    enable_guardrails=env_bool("ENABLE_GUARDRAILS", True),
    guardrails=GuardrailConfig(
        max_input_chars=env_int("LLM_MAX_INPUT_CHARS", 24000),
        max_output_tokens=env_int("LLM_MAX_OUTPUT_TOKENS", 1024),
        min_output_tokens=env_int("LLM_MIN_OUTPUT_TOKENS", 1),
    ),
)

COUNTERS: dict[str, int] = {
    "requests_total": 0,
    "routed_base": 0,
    "routed_canary": 0,
    "errors_upstream": 0,
    "errors_bad_request": 0,
}
START_TS = time.time()


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def error_payload(message: str, code: str = "invalid_request_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code}}


def deterministic_bucket(key: str) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) % 10000
    return value / 100.0


def canary_key(payload: dict[str, Any], headers: BaseHTTPRequestHandler.headers.__class__) -> str:
    forced = headers.get(CONFIG.hash_header, "").strip()
    if forced:
        return forced

    request_id = headers.get("x-request-id", "").strip()
    if request_id:
        return request_id

    user = payload.get("user")
    if isinstance(user, str) and user.strip():
        return user.strip()

    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict):
            content = first.get("content")
            if isinstance(content, str) and content.strip():
                return content[:512]

    prompt = payload.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt[:512]

    return json.dumps(payload, ensure_ascii=True, sort_keys=True)[:1024]


def select_route(payload: dict[str, Any], headers: BaseHTTPRequestHandler.headers.__class__) -> tuple[str, str]:
    forced = headers.get("x-canary-route", "").strip().lower()
    if forced in {"base", "canary", "adapter"}:
        route = "canary" if forced in {"canary", "adapter"} else "base"
        return route, "forced_header"

    key = canary_key(payload, headers)
    bucket = deterministic_bucket(key)
    if bucket < CONFIG.canary_percent:
        return "canary", f"hash_bucket={bucket:.2f}"
    return "base", f"hash_bucket={bucket:.2f}"


def forward_request(path: str, payload: dict[str, Any], incoming_headers: BaseHTTPRequestHandler.headers.__class__) -> tuple[int, bytes, dict[str, str]]:
    url = f"{CONFIG.upstream_base_url}{path}"
    headers = {
        "Accept": incoming_headers.get("accept", "application/json"),
        "Content-Type": incoming_headers.get("content-type", "application/json"),
    }

    auth = incoming_headers.get("authorization", "")
    if auth:
        headers["Authorization"] = auth

    request_id = incoming_headers.get("x-request-id", "").strip()
    if request_id:
        headers["X-Request-Id"] = request_id

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=CONFIG.upstream_timeout_s) as resp:
            out_headers = {"Content-Type": resp.headers.get("Content-Type", "application/json")}
            return int(resp.status), resp.read(), out_headers
    except urllib.error.HTTPError as exc:
        out_headers = {"Content-Type": exc.headers.get("Content-Type", "application/json")}
        return int(exc.code), exc.read(), out_headers
    except Exception:
        COUNTERS["errors_upstream"] += 1
        body = json.dumps(error_payload("upstream unavailable", code="server_error"), ensure_ascii=True).encode("utf-8")
        return 502, body, {"Content-Type": "application/json"}


class CanaryProxyHandler(BaseHTTPRequestHandler):
    server_version = "mira-canary-proxy/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path != "/health":
            json_response(self, 404, error_payload("not found", code="not_found_error"))
            return

        upstream_ok = False
        try:
            with urllib.request.urlopen(f"{CONFIG.upstream_base_url}/health", timeout=3) as resp:
                upstream_ok = int(resp.status) == 200
        except Exception:
            upstream_ok = False

        payload = {
            "status": "ok" if upstream_ok else "degraded",
            "uptime_s": round(time.time() - START_TS, 2),
            "upstream_base_url": CONFIG.upstream_base_url,
            "base_model_name": CONFIG.base_model_name,
            "canary_model_name": CONFIG.canary_model_name,
            "canary_percent": CONFIG.canary_percent,
            "guardrails_enabled": CONFIG.enable_guardrails,
            "counters": COUNTERS,
        }
        json_response(self, 200 if upstream_ok else 503, payload)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in {"/v1/chat/completions", "/v1/completions"}:
            json_response(self, 404, error_payload("unsupported endpoint", code="not_found_error"))
            return

        content_length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            COUNTERS["errors_bad_request"] += 1
            json_response(self, 400, error_payload("invalid JSON payload"))
            return

        if not isinstance(payload, dict):
            COUNTERS["errors_bad_request"] += 1
            json_response(self, 400, error_payload("payload must be an object"))
            return

        if payload.get("stream") is True:
            COUNTERS["errors_bad_request"] += 1
            json_response(self, 400, error_payload("stream=true is not supported by canary proxy"))
            return

        endpoint = "chat" if path.endswith("/chat/completions") else "completion"
        if CONFIG.enable_guardrails:
            valid, errors = validate_payload(payload, endpoint, CONFIG.guardrails)
            if not valid:
                COUNTERS["errors_bad_request"] += 1
                json_response(self, 400, error_payload("; ".join(errors)))
                return

        route, reason = select_route(payload, self.headers)
        target_model = CONFIG.canary_model_name if route == "canary" else CONFIG.base_model_name
        payload["model"] = target_model

        COUNTERS["requests_total"] += 1
        if route == "canary":
            COUNTERS["routed_canary"] += 1
        else:
            COUNTERS["routed_base"] += 1

        status, resp_body, resp_headers = forward_request(path, payload, self.headers)
        self.send_response(status)
        self.send_header("Content-Type", resp_headers.get("Content-Type", "application/json"))
        self.send_header("Content-Length", str(len(resp_body)))
        self.send_header("X-Canary-Route", route)
        self.send_header("X-Target-Model", target_model)
        self.send_header("X-Canary-Reason", reason)
        self.end_headers()
        self.wfile.write(resp_body)


def main() -> int:
    server = ThreadingHTTPServer((CONFIG.listen_host, CONFIG.listen_port), CanaryProxyHandler)
    print(
        json.dumps(
            {
                "message": "starting llm canary proxy",
                "listen": f"{CONFIG.listen_host}:{CONFIG.listen_port}",
                "upstream": CONFIG.upstream_base_url,
                "base_model": CONFIG.base_model_name,
                "canary_model": CONFIG.canary_model_name,
                "canary_percent": CONFIG.canary_percent,
                "guardrails_enabled": CONFIG.enable_guardrails,
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
