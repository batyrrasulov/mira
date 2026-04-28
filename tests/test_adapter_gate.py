from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_adapter_gate_writes_failure_report_when_endpoint_unreachable(tmp_path: Path) -> None:
    report_path = tmp_path / "adapter_gate_report.json"
    cmd = [
        sys.executable,
        "evaluation/run_adapter_gate.py",
        "--base-url",
        "http://127.0.0.1:9",
        "--base-model",
        "base-model",
        "--canary-model",
        "canary-model",
        "--prompts-file",
        "evaluation/prompts/sample_prompts.jsonl",
        "--timeout-s",
        "0.5",
        "--output-json",
        str(report_path),
    ]

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "fail"
    assert report["base"]["rows"][0]["status"] == 0
    assert report["base"]["rows"][0]["error"].startswith("network_error")
