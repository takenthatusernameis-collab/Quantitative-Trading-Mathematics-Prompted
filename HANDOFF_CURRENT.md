# HANDOFF_CURRENT.md — H88 (NF-20261105-06 gold–oil RV mean reversion) pre-registered & implemented

## State
- Working tree has **uncommitted** changes from this session (no commit made; no user request): modified `HYPOTHESIS_SPEC.md`, modified `NEW_FAMILY_RESEARCH_REGISTER.md`; untracked `run_nf_20261105_06_gold_oil_rv.py`, `tests/test_nf_20261105_06_gold_oil_rv.py`. `src/qtr` **not modified**.
- H1–H30 exhausted; hypotheses documented through H88 (H88 pre-registered). H85/H86/H87 REJECTED. Next unused H-ID after H88 is H89.
- STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md followed: cycle 3 mechanism search completed across 3 distinct categories; 3 repo-new candidates ranked; H88 selected as highest expected-information candidate (relative value/convergence, 3.95).

## What changed (this session)
- `NEW_FAMILY_RESEARCH_REGISTER.md`: appended §10 cycle-3 discovery/ranking (NF-20261105-04 commodity carry/roll proxy — deferred, data/roll feasibility; NF-20261105-05 short-term CS reversal — deferred, net-of-cost/turnover; NF-20261105-06 gold–oil RV mean reversion — selected) and §11 H88 pre-registration.
- `HYPOTHESIS_SPEC.md`: appended §H88 (NF-20261105-06) pre-registration — mechanism, distinction (vs H85 lead-lag), construction, data/splits, grid, gates/rejection, falsification; status PRE-REGISTERED/IMPLEMENTED, execution pending.
- `run_nf_20261105_06_gold_oil_rv.py` (new): H88 runner — GC=F/CL=F log-spread z-score mean reversion, 1-bar delay, dollar-neutral legs, vol target, futures config, 18-combo grid (train-only WF selection), OOS Val+Test gates, direction-aware benchmark gate, OAT ±20% perturbation, stationarity diagnostic, isolated cache, tracker/artifacts. Patterned after NF-01/H86/H87 runners.
- `tests/test_nf_20261105_06_gold_oil_rv.py` (new): 13 focused tests pinning gates/grid/splits, log-spread construction, non-positive handling, trailing-only z-score, 1-bar delay, dollar neutrality/bounds, future-data non-leakage, determinism, metrics/diagnostic shape.
- `NEXT_TASK.md`: replaced with H88 execution instructions and constraints.

## What was actually verified
- `python -m ruff check src tests run_nf_20261105_06_gold_oil_rv.py tests/test_nf_20261105_06_gold_oil_rv.py` → **All checks passed!**
- `python -m ruff format run_nf_20261105_06_gold_oil_rv.py tests/test_nf_20261105_06_gold_oil_rv.py` applied; `python -m ruff format --check src tests run_*.py` → **113 files already formatted**.
- `PYTHONPATH=src python -m pytest tests/test_nf_20261105_06_gold_oil_rv.py -q` → **13 passed in 1.47s**.
- `git status --short` confirms only the expected H88 files changed/untracked.

## Not verified / not run (by design)
- **H88 experiment execution not run.** Runner requires yfinance network access to fetch GC=F/CL=F daily 2010-01-01→2026-10-31 (isolated cache) and produces protected-holdout metrics; execution is the next bounded task. No holdout feedback used.
- **Full pinned `src/qtr` gate suite not re-run** because `src/qtr` was not modified (`--cov=qtr --cov-branch -W error`, 100% required). H87 baseline was previously green per handoffs; touched files are runners/tests/docs only.
- No published artifacts, gate thresholds, verdicts, or certified numbers modified.

## What remains unresolved
- H88 execution and outcome recording (spec result, register §12, lineage update, verdict).
- NF-20261105-04 (commodity carry, roll-proxy feasibility) and NF-20261105-05 (short-term CS reversal, turnover/net-of-cost) deferred with documented reasons; revisit after H88 outcome or if H88 execution is data-blocked.
- FINAL_REPORT.md §H53–§H61 disclosed-not-quantified items remain (no gate impact).

## Approaches already tried / failed (this cycle)
- None failed in implementation. Cycle 3 followed directive: searched 3 mechanism categories, proposed/ranked 3 candidates, selected NF-06 (relative value/convergence). NF-04 deferred for yfinance roll-proxy construction/point-in-time risk; NF-05 deferred for high-turnover net-of-cost feasibility (execution score 2).

## Precise next task (one task), with evidence and constraints
**Execute H88 and record the outcome.** See `NEXT_TASK.md`.

```bash
cd /home/runner/work/Quantitative-Trading-Mathematics-Prompted/Quantitative-Trading-Mathematics-Prompted
PYTHONPATH=src python run_nf_20261105_06_gold_oil_rv.py
```

Then update HYPOTHESIS_SPEC §H88 and NEW_FAMILY_RESEARCH_REGISTER §12 with experiment ID/gates/OOS metrics/selected config/verdict/lineage row; re-run focused tests + lint/format; if `src/qtr` changes, run pinned full gates (100% coverage, `-W error`). If data/network blocks execution, preserve traceback, mark blocked (not rejected), and document the blocker before selecting NF-04/NF-05.

Constraints: protect holdout; do not modify published artifacts/thresholds/prior verdicts; keep `src/qtr` 100% stmt+branch if touched; no paid data/compute; never commit without explicit user request.
