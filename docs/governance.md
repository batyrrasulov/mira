# Governance and Safety

## Intended Use

Mira is designed for educational assistance and concept mastery workflows.
It is not intended for policy-violating academic misuse.

## Data Governance

- Use only datasets with approved licensing and redistribution terms.
- Keep training data lineage in run reports.
- Do not log or commit secrets, private student records, or provider credentials.

## Promotion Governance

Every adapter promotion should satisfy all gates below:

1. `pytest -q` passes.
2. `python -m py_compile` passes for touched source files.
3. `evaluation/run_adapter_gate.py` returns `status=pass`.
4. Canary route is deployed with bounded percentage (for example, 10-25%) before full promotion.

## Operational Ownership

- Assign explicit owners for model weights, runtime configuration, and deployment scripts.
- Keep rollback procedures (`scripts/rollback_canary.sh`) tested and documented.
- Record each promotion decision with report artifacts in `evaluation/results/`.

## Security Controls

- Require API authentication (`MIRA_API_KEY`) for production endpoints.
- Restrict access to vLLM and canary proxy ports to private networks.
- Rotate access tokens and validate container provenance regularly.
