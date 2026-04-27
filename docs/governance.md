# Governance and Safety

## Intended Use

Mira is for concept mastery and study support.
It is not intended for policy-violating exam assistance.

## Data Handling

- Do not commit credentials or private datasets.
- Keep logs focused on technical diagnostics, not sensitive personal content.
- Use approved datasets for training and evaluation.

## Release Gates

A release should pass the following before deployment:

1. API contract and tests pass.
2. Quality suite meets agreed thresholds.
3. Readiness checks succeed in target environment.
4. Configuration review confirms no hardcoded secrets.

## Operational Responsibilities

- Define ownership for model/config changes.
- Keep rollback steps documented and tested.
- Track regressions with repeatable eval runs.
