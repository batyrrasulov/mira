# Reference Audit Summary (Anonymized)

This summary captures engineering lessons learned from a production-style
self-hosted LLM stack audit. It excludes proprietary internals and sensitive
values.

## Key Findings

1. Secret hygiene risk in local environment files
- Local env snapshots contained API keys and CRM credentials.
- Public-repo publishing must enforce strict secret boundaries.

2. Boolean request parsing bug risk
- String booleans can be misinterpreted when cast with bool("false") style logic.

3. Parameter drift in evaluation scripts
- A declared CLI argument was ignored and replaced by a hardcoded value.

4. Auth mismatch in smoke tests
- Scripts that enable API-key auth must include the same auth in validation calls.

5. Inconsistent report naming between producer/consumer scripts
- One checker expected timestamped filenames while producer default used
  non-timestamped naming.

6. Startup failure cleanup gap
- Runtime start scripts should terminate spawned processes when startup health
  checks fail.

7. Brittle threshold equality checks
- Exact float equality for historical threshold matching is fragile; tolerant
  comparisons are safer.

## Applied Design Decisions in This Repo

- Secrets are excluded from version control.
- Guardrails enforce explicit limits on input and output.
- Runtime contract is deterministic and testable.
- Training/evaluation scripts are separated and documented.
- Public claims are methodology-based, not sensitive metric disclosures.
