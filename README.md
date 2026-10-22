# Quantitative Trading Mathematics (Prompted)

This repository contains a quantitative trading research codebase with experiment runners, backtesting infrastructure, and a large set of audited hypothesis tests (H1–H57).

## Quickstart

- Install dependencies: `pip install -r requirements.txt`
- Run tests: `python -m pytest -q`
- Lint/format: `python -m ruff check . && python -m ruff format --check .`

## Key Directories

- `src/qtr/` — Core library (backtest, data, features, portfolio, validation, etc.)
- `run_*.py` — Experiment runners for hypotheses H1+
- `tests/` — Test suite with hypothesis contracts and audits
- `*.md` — Handoff reports, execution logs, and discovery reports

## Notes

- Coverage is enforced at 100% for `src/qtr` (see `pyproject.toml`).
- Many experiment artifacts are committed; published numbers and gates are treated as frozen per handoff conventions.
