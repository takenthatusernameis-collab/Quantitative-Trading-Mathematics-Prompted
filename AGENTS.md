# AGENTS.md

## Quick start
```bash
pip install -r requirements.txt
```

## Testing
```bash
python -m pytest -q
python -m pytest -q -W error  # as used in handoffs
```

## Lint and format
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
```

## Coverage
```bash
python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing
```
Coverage is enforced at 100% for `src/qtr` (see `pyproject.toml`).

## Notes
- Source lives in `src/qtr/`; tests in `tests/`.
- Many experiment artifacts and reports are committed. Published numbers and gates are treated as frozen per handoff conventions.
- The hypothesis space H1–H30 is exhausted per handoffs; changes under `src/qtr` require re-running pinned contracts.
