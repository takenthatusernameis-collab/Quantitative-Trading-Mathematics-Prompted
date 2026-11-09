# HANDOFF.md — Cycle 73: H159 pre-registered, implementation created, REAL execution pending (env dependency blocker)

**State timestamp (UTC):** 2026-11-08T23:49:27Z (session end)
**Branch:** `main`
**Working tree at start:** clean (`7d73997` / "H156"). **Session changed files (uncommitted):** `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `HANDOFF.md`, `NEXT_TASK.md` (if updated), `run_nf_20261108_32_vvix_vix_spread_spy.py` (replaced docstring-only draft with full runner), `tests/test_nf_20261108_32_vvix_vix_spread_spy.py` (new). `src/qtr` **unchanged**.
**Research mode:** NEW-FAMILY DISCOVERY MODE (STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md mandatory).

## What changed

- **Cycle 73 discovery performed** (directive §4): lineage reconciled to H158; H85–H158 all rejected/recorded. Assessed >=3 candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and NF-root collision checks: **NF-20261108-32 VVIX-VIX implied-vol-of-vol spread** (volatility & convexity premia / vol-of-vol, **4.15, selected**); **NF-20261108-29 cross-asset return dispersion** (information transmission / cross-asset risk appetite, **4.10, deferred**); **NF-20261108-31 cross-sectional IVOL dispersion** (relative value / cross-section risk, **3.85, deferred**). NF-20261108-32 verified no executed NF/H/runner/artifact root; adjacency to H158 (VIX-RV VRP, different observable) and VIX term/implied-spread families disclosed honestly.
- **H159 pre-registered** as NF-20261108-32 in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md` *before* validation/protected-test outcomes. Bounded 8-combo grid, train-only 4-fold WF selection, Test protected, 1-bar delay, equity costs, pre-registered inverse falsifier, 8 OOS gates. No gate weakening.
- **Implementation created (not executed to REAL verdict):**
  - `run_nf_20261108_32_vvix_vix_spread_spy.py` — full runner (replaced prior 59-line docstring-only draft). PIT z-score of trailing `(VVIX-VIX)`; stress on positive z (tail-protection premium elevated); SPY timing via `run_backtest`/engine `signals.shift(1)`; buy-hold/random-exposure/inverse/perturbation/worst-regime/benchmark bootstrap; writes `.experiments/nf_runs/nf_20261108_32_vvix_vix_spread_spy/{summary.json,grid.csv,data_meta.json}`.
  - `tests/test_nf_20261108_32_vvix_vix_spread_spy.py` — 7 focused tests (signal columns/bounds, positive-z stress mapping, inverse differs, z-shape, splits, buy-hold, VVIX jump -> positive z).

## What was actually verified

- `python3 -m py_compile` passed for `run_nf_20261108_32_vvix_vix_spread_spy.py` and `tests/test_nf_20261108_32_vvix_vix_spread_spy.py` (and H158 runner/test still compile).
- `ast.parse` passed for both new H159 files.
- NF-root checks: `NF-20261108-32`/`nf_20261108_32` absent from key docs/artifacts except the new registration/runner; H159 absent from `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`FINAL_REPORT.md` before append.
- `git diff --name-only` clean at session start; `src/qtr` not modified.

## NOT verified / blocked (honest)

- **REAL H159 execution not run.** Environment missing `numpy`, `pandas`, `pytest`, `ruff`, `yfinance` (verified: `python3 -c "import numpy/pandas/..."` -> `ModuleNotFoundError`; `pip show pytest ruff` not found; `unittest` run of NF-30 test failed at `import numpy`). Therefore focused `pytest`, `ruff check/format`, runner execution, and REAL `.experiments/.../summary.json` verdict **were not produced**. **No verdict fabricated.**
- Full pinned core suite (`python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`, ruff/format over `src tests run_*.py`) not run this session (deps missing; `src/qtr` unchanged so pinned-suite rerun not triggered by code change, but environment also cannot run it). Prior historical baseline remains H92-era handoff claim (**2,295 passed, 16 skipped, 100% statement/branch coverage** for `src/qtr` at `1c3fd75`) — **not reverified here**.
- ^VVIX yfinance PIT coverage/alignment not verified by live fetch in this environment (yfinance missing). Runner handles dropna/alignment; REAL run must record `data_meta.json` rows/splits and any NaN/data blocker.

## Unresolved / risks

- H159 has **no REAL verdict/artifact** yet; cycle 73 execution is incomplete until dependency-complete run. This is a deterministic environment blocker, not a strategy result.
- NF-20261108-31 stub `run_nf_20261108_31_spy_parkinson_rv_spy.py` is pre-existing and still only a docstring (not modified). Empty/stub files like `run_nf_20261107_53_etr`, `run_nf_20261108_13_spy_futures_basis.py` pre-exist (not modified).
- NF-06-26/H105 already tested VIX9D-VIX contango (REJECT 5/9); avoid selecting VIX9D-VIX as a “new” NF root without explicit separation.

## Approaches tried / do not repeat blindly

- Did **not** fabricate H159 results. Did **not** weaken gates. Did **not** modify `src/qtr`, published artifacts, frozen thresholds, or certified numbers.
- Attempted to locate pytest/numpy/pandas/ruff/yfinance in system paths and `/home/runner/work/_temp/*site-packages*`; none found. `pip show pytest ruff` reported not found. This is a recurring deterministic environment constraint for this session; do not claim verification without deps.

## Precise next task (highest value, bounded)

**Execute pre-registered H159 (NF-20261108-32) in a dependency-complete environment and record the REAL verdict — or record a concrete ^VVIX data blocker.**

1. Install/activate deps so `numpy,pandas,scipy,pytest,ruff,yfinance,qtr` imports work (use project venv/CI image; `pip install -r requirements.txt` and any missing `yfinance`/pytest/ruff as per pyproject extras if needed). Do **not** change `src/qtr`.
2. Run (from repo root): `PYTHONPATH=src python -m ruff check run_nf_20261108_32_vvix_vix_spread_spy.py tests/test_nf_20261108_32_vvix_vix_spread_spy.py && PYTHONPATH=src python -m ruff format --check run_nf_20261108_32_vvix_vix_spread_spy.py tests/test_nf_20261108_32_vvix_vix_spread_spy.py && PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_32_vvix_vix_spread_spy.py`.
3. Run `python run_nf_20261108_32_vvix_vix_spread_spy.py`. Inspect `.experiments/nf_runs/nf_20261108_32_vvix_vix_spread_spy/summary.json` (+ `grid.csv`,`data_meta.json`): rows, train/val/test, verdict/gates, OOS metrics, ablations, benchmark/inverse. **Record REAL numbers only.**
4. Update `HYPOTHESIS_SPEC.md` §H159 outcome/lineage, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 73 execution outcome, and `HANDOFF.md`/`NEXT_TASK.md`. If verdict is REJECT, preserve it and plan Cycle 74 discovery (>=3 repo-new candidates, >=3 categories; NF-20261108-29 at 4.10 and NF-20261108-31 at 3.85 remain deferred candidates but must be rechecked for roots/adjacency). If PASS_CANDIDATE, do **not** declare validation complete; follow all protected-holdout/multiple-testing gates before any broader claim.
5. **If ^VVIX is infeasible** (missing history, non-positive data, severe misalignment): document concrete evidence (symbol, date range, NaN counts/rows dropped, error) in spec/register/handoff, mark H159 as infeasible/blocked with evidence (do not fake pass/reject), and pre-register+execute next highest-information candidate (NF-20261108-29 cross-asset return dispersion, 4.10) only after NF-root/adjacency recheck.
6. Hard constraints: no paid data/compute, no live/paper trading, no gate weakening, no protected-test feedback in selection, no modification of published artifacts/frozen thresholds/certified numbers, no commit/push without explicit authorization. If `src/qtr` changes, rerun full pinned suite with 100% branch coverage and `-W error`.
