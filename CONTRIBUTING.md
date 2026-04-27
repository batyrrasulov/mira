# Contributing

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Validation Checklist

```bash
pytest -q
python -m py_compile src/mira/*.py training/scripts/*.py evaluation/*.py scripts/*.py
```

## Pull Request Expectations

- Explain infra and model-impacting changes clearly.
- Include updated docs for new runtime or training behaviors.
- For promotion logic changes, include a sample gate report.
- Do not commit secrets, tokens, or local environment files.
