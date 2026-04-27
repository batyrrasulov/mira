# Security Policy

## Reporting a Vulnerability

Do not open public issues for security vulnerabilities.

Send a report with reproduction steps, affected files, and impact summary to the project maintainers through a private channel.

## Security Baseline

- Keep API endpoints behind authentication (`MIRA_API_KEY`).
- Restrict network exposure for ports 8000, 8003, and 8080.
- Rotate provider and Hugging Face tokens regularly.
- Keep container images and Python dependencies up to date.
- Treat prompts and completions in logs as potentially sensitive.

## Production Guidance

- Run containers with least privilege.
- Enable centralized logging and alerting.
- Apply per-client rate limits at ingress.
- Validate every model promotion with `evaluation/run_adapter_gate.py`.
