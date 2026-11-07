# NEXT_TASK — Cycle 46 discovery done (H132 pre-registered, execution pending deps); run H132 in prepared env

Cycle 46 completed **discovery + pre-registration** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
- Reconciled lineage to H131 (H85–H131 all REJECTED/recorded).
- Proposed >=3 repo-new candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring:
  - NF-20261107-35 SPY trailing realized kurtosis (4th-moment) stress regime timing — 4.00, **selected/pre-registered H132** (repo-new realized 4th-moment observable; honest adjacency to H89/H122/H124/H128 acknowledged).
  - NF-20261107-36 SPY distance-to-trailing-252d-high drawdown-state timing — 3.85, held.
  - NF-20261107-37 EEM-vs-EFA cross-asset emerging/global risk-appetite relative-strength timing for SPY — 3.45, held.
- Pre-registered H132 in `HYPOTHESIS_SPEC.md` §H132; runner + focused tests added (`run_nf_20261107_35_spy_realized_kurtosis.py`, `tests/test_nf_20261107_35_spy_realized_kurtosis.py`); `py_compile` OK. `src/qtr` unchanged.
- **H132 NOT executed in this session:** environment lacks `yfinance/pandas/numpy/scipy/pytest/ruff` (verified). No OOS/validation outcomes examined.

**Precise next task (Cycle 46 execution / Cycle 47 handoff):** In a prepared environment with project deps + `src/qtr` available:
```bash
python -m ruff check run_nf_20261107_35_spy_realized_kurtosis.py tests/test_nf_20261107_35_spy_realized_kurtosis.py
python -m ruff format --check run_nf_20261107_35_spy_realized_kurtosis.py tests/test_nf_20261107_35_spy_realized_kurtosis.py
PYTHONPATH=src python -m pytest -q tests/test_nf_20261107_35_spy_realized_kurtosis.py
PYTHONPATH=src python run_nf_20261107_35_spy_realized_kurtosis.py
```
Record actual verdict in `HYPOTHESIS_SPEC.md` (H132 outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 46 execution outcome), `NEXT_TASK.md`, and handoff with artifact `.experiments/nf_runs/nf_20261107_35_spy_realized_kurtosis/summary.json`. If REJECT, perform Cycle 47 fresh discovery per directive §4 and pre-register/execute **H133** (next unused H-ID). If environment/deps still blocked, document concrete evidence and do not fabricate results.

Constraints: free/public data only; no gate weakening; no published/certified artifact modification; no commit/push; `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% coverage suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`).
