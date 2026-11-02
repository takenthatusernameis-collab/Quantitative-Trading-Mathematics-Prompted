# Next task — Baseline maintenance (verified on HEAD 253a83b)

## Status (this session)
Baseline verified green on HEAD `253a83b`. One bounded fix applied and verified:
deleted the orphan zero-test placeholder `tests/test_h59_ablation_rederivation.py`.
Working tree has that single uncommitted deletion.

## What changed
- `tests/test_h59_ablation_rederivation.py` — **deleted**. It was a 1-line
  placeholder committed at `228b5cc` that carried **zero tests** and was
  referenced by **nothing** in the tree. Its name collided with the real H59
  contract test (`tests/test_h59_contamination_gate_blast_radius.py`, 93
  tests), and the "ablation re-derivation contract" it claimed to be already
  exists as `tests/h55_rederivation.py` +
  `tests/test_h55_nested_metrics_disclosure.py` (915 lines). It was the H82
  class of defect (a committed file that promises a contract and delivers
  nothing) and was invisible to every gate.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md` updated to
  record the deletion and the re-verified baseline.

## What was actually verified (this session, on HEAD 253a83b)
- `git log --oneline -1` → `253a83b`
- `git status --short` → only `D tests/test_h59_ablation_rederivation.py`
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already formatted**
- `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing` → **2274 passed, 16 skipped**; `src/qtr`
  **1191 stmts / 388 branches / 0 missed / 0 partial / 100.00%** (identical to
  the pre-change baseline).
- `pytest --collect-only -q` → **2290 tests collected**, unchanged.

## What remains unresolved
- The deletion is uncommitted; committing requires explicit user approval.
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified); no gate
  impact. H1–H30 exhausted; certified families frozen.

## Approaches already failed
- **No defect of the established class (H58/H61/H62) found in `src/qtr`.**
  Re-inspected `statistics.py`, `engine.py` (`_calculate_metrics`, empty-series
  guard at engine.py:461), `fetcher.py` (all three fetch branches apply
  `_reject_non_positive_prices`; CCXT cache-hit at fetcher.py:357 and live path
  at fetcher.py:435), `config.py` (finite-check at config.py:84) and
  `baselines.py`. Every guard the class requires is already present and covered
  at 100%. The two functions previously flagged (`validate_strategy`,
  `_calculate_metrics`) were tested and **rejected as false positives** — their
  `profit_factor == np.inf` on a flat/zero series is the pinned boundary
  convention asserted at `tests/test_engine_metric_agreement.py:271`.

## One precise next task
**Maintain baseline health.** No further code change needed now. On any future
change under `src/qtr`, `tests/`, `run_*.py`, `requirements.txt`, or
`pyproject.toml`, run the pinned gates and confirm they stay green:

```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```

Constraints:
- Preserve `src/qtr` at 100% statement + branch coverage (`fail_under = 100`).
- Do not relax `fail_under`, drop `-W error`, or remove the format check.
- Do not modify published artifacts, gate thresholds, verdicts, or certified
  numbers.
- H1–H30 exhausted; hypotheses up to H82 documented.
- Keep package behavior consistent with src layout; do not commit build
  artifacts/secrets/caches.
- Never commit without explicit user request.

(End of file - total 73 lines)