# Contributing to Healthcare AI Guardrails

Thank you for your interest in contributing! This document covers how to set up your development environment, add new validators, run tests, and submit pull requests.

## Development setup

Requires Python 3.9+. We recommend [uv](https://docs.astral.sh/uv/) for fast installs, but standard `pip` works fine too.

```bash
git clone https://github.com/SamPIngram/healthcare-ai-guardrails.git
cd healthcare-ai-guardrails

# With uv
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
pre-commit install

# With pip
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pre-commit install
```

## Running tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=healthcare_ai_guardrails --cov-report=term-missing
```

## Code style

We use [black](https://black.readthedocs.io/) for formatting and [ruff](https://docs.astral.sh/ruff/) for linting. Both run automatically via pre-commit. To run them manually:

```bash
black .
ruff check . --fix
```

Type checking with mypy:

```bash
mypy src
```

## Adding a new validator

1. Add your validator class to the appropriate module under `src/healthcare_ai_guardrails/validators/`.
2. Export it from `src/healthcare_ai_guardrails/__init__.py` and add it to `__all__`.
3. Register a YAML `type` key for it in `src/healthcare_ai_guardrails/config.py` (`_build_validator`).
4. Add at least one passing and one failing test in `tests/`.
5. Add an example entry to `examples/spec.example.yaml` if it is a broadly applicable check.
6. Update `README.md` (YAML Spec schema section) and `CHANGELOG.md`.

### Synthetic DICOM in tests

Use the `create_test_dicom` helper to generate in-memory DICOM datasets without needing real files:

```python
from healthcare_ai_guardrails.testing.dicom_factory import create_test_dicom

ds = create_test_dicom(Modality="CT", PatientAge="045Y")
```

## Pull request checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Code is formatted (`black .`) and lint-clean (`ruff check .`)
- [ ] New public API is exported from `__init__.py`
- [ ] New YAML spec type is documented in `README.md`
- [ ] `CHANGELOG.md` has an entry under the upcoming version

## Reporting issues

Please use the GitHub issue templates — bug reports and feature requests each have a template to help provide the right information.

## License

By contributing you agree that your work will be licensed under the [MIT License](./LICENSE).
