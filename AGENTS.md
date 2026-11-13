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
python -m ruff check src tests run_*.py scripts
python -m ruff format --check src tests run_*.py scripts
```

## Coverage
```bash
python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing
```
Coverage is enforced at 100% for `src/qtr` (see `pyproject.toml`).

## Notes
- Source lives in `src/qtr/`; tests in `tests/`.
- Many experiment artifacts and reports are committed. Published numbers and gates are treated as frozen per handoff conventions.
- **Stale H-range claim (re-verified 2026-11-12):** the lines below read "H1–H30 is exhausted" and "hypotheses through H84 are documented". Both are stale by 97+ hypotheses: the current research record is **H1–H181 exhausted/rejected, H182 unassigned**, per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96 and `HANDOFF.md`. This is a trigger for NEW-FAMILY DISCOVERY MODE, not a reason to stop at maintenance-only work. Do not treat these two lines as the current inventory; they are preserved as historical lineage only.
- Do not treat parameter, timeframe, indicator, market, or universe variations as new strategy families. Build a mechanism-level lineage map and search for genuinely distinct return-generating mechanisms.
- Preserve all existing statistical gates, protected-holdout rules, free-data preference, and 100% source coverage requirement.
- **Workflow files are maintainer-managed and agent-unreachable.** `.github/workflows/**` is restored from `origin/main` after every session and excluded from staging (`.github/scripts/kilo-controller.sh`), and the repository GitHub App token has no `workflows` permission, so a committed workflow edit cannot reach `main`. Do not try to fix CI workflow content in a commit; capture it as an apply-ready patch under `patches/` and record the maintainer action in `NEXT_TASK.md`. Do not weaken the contract test that pins the workflow.
- **`tests/test_gates_workflow.py` is red on `origin/main` by design of this block.** As of 2026-11-13 it is the only failing test file; the fix is `patches/0001-gates-workflow-contract-fix.patch`.
