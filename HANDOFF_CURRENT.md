# HANDOFF_CURRENT.md — NF-20261105-10/H92 completed (runner fix) + pre-registered; execution pending

## What changed
- `run_nf_20261105_10_equity_bond_relmom.py` was committed incomplete in `0c0cabe` (ended at `perturbation_eval`; missing `main()`/CLI). Completed the runner in working tree with full pipeline: isolated cache fetch (SPY+TLT), train/val/test split, 16-combo grid (lookback×vol_target×allow_short) with train-only WF selection, OOS Val+Test gate evaluation, perturbation (OAT ±20% lookback/vol_target), ablations (SPY benchmark, random-direction, opposite `allow_short`), artifact/summary logging, tracker finish. Causal: relmom uses prices through close t; engine `shift(1)` earns t→t+1. **Not committed** (no explicit user request).
- Added `tests/test_nf_20261105_10_equity_bond_relmom.py` (10 tests): pre-registration constants/gates/grid/config, relmom shape/bounds, warmup flat, deterministic direction (up-SPY→long, down-SPY+short→short), missing-symbol flat. **Not committed**.
- Pre-registered H92/NF-20261105-10 in `HYPOTHESIS_SPEC.md` §H92 and added cycle 6 entry to `NEW_FAMILY_RESEARCH_REGISTER.md` (3 candidates scored; NF-10 selected 4.05; NF-11/12 deferred). **Not committed**.
- `src/qtr` unchanged. No published artifacts, gate thresholds, verdicts, or certified numbers modified.

## What was actually verified
- `run_nf_20261105_10_equity_bond_relmom.py` parses (`ast.parse`/`py_compile`) and includes `main()`/`__main__` after fix.
- `python3 -m ruff check run_nf_20261105_10_equity_bond_relmom.py tests/test_nf_20261105_10_equity_bond_relmom.py` → All checks passed.
- `python3 -m ruff format --check run_nf_20261105_10_equity_bond_relmom.py tests/test_nf_20261105_10_equity_bond_relmom.py` → clean (formatted).
- `python3 -m ruff check src tests run_*.py` → All checks passed.
- `python3 -m ruff format --check src tests run_*.py` → 121 files already formatted.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261105_10_equity_bond_relmom.py tests/test_nf_20261105_09_turn_of_month.py` → **18 passed** (1.34s).
- Pinned `src/qtr` 100% coverage / `-W error` suite **not re-run** (no `src/qtr` change). Last known green per prior handoffs/committed state; run if `src/qtr`/tests/runners affecting gates change.

## What remains unresolved
- **H92/NF-20261105-10 not executed.** No experiment ID/artifact/verdict. Execution requires yfinance SPY+TLT fetch + 16-combo grid backtests; not run in this bounded session. Non-execution is not a verdict.
- NF-20261105-04 (commodity carry, point-in-time term-structure/roll proxy unavailable in free pipeline; CL=F non-positive history risk) and NF-20261105-05 (short-term CS reversal, decisive daily turnover/net-of-cost risk) remain deferred with documented decisive risks. NF-20261105-11/12 deferred (cycle 6).
- H1–H30 exhausted; H85–H91 rejected; H92 pre-registered/pending.
- Working tree has uncommitted changes (NF-10 runner completion, NF-10 tests, HYPOTHESIS_SPEC.md §H92, NEW_FAMILY_RESEARCH_REGISTER.md cycle 6, handoffs).

## Failed/blocked approaches (evidence)
- **Committed incomplete NF-10 runner (0c0cabe):** file ended at `perturbation_eval` (298 lines) with no `main()`/execution/summary. Evidence: `grep def main run_nf_20261105_10_equity_bond_relmom.py` returned nothing before fix; `wc -l` 298; `git show --name-only HEAD` shows only the runner added. Fixed in working tree by appending complete `main()`.
- No experiment failures this session (H92 not executed).

## One precise next task
Execute H92/NF-20261105-10 and record the verdict:
1. Run `cd /home/runner/work/Quantitative-Trading-Mathematics-Prompted/Quantitative-Trading-Mathematics-Prompted && PYTHONPATH=src python run_nf_20261105_10_equity_bond_relmom.py` (uses isolated cache under `.cache/nf_20261105_10_h92/...`, train-only WF selection, protected Test, OOS Val+Test gates). Capture experiment ID and `summary.json`.
2. Update `HYPOTHESIS_SPEC.md` §H92 “Execution” with exp ID, selected config, OOS metrics/gates/verdict (PASS/REJECT), ablations, artifact path.
3. Update `NEW_FAMILY_RESEARCH_REGISTER.md` cycle 6 H92 status/lineage row from PENDING to actual verdict; include failure modes if rejected.
4. Re-run focused checks: `ruff check/format --check` on touched files and `PYTHONPATH=src pytest -q tests/test_nf_20261105_10_equity_bond_relmom.py`. If verdict affects documentation only and `src/qtr` remains untouched, pinned 100% coverage suite can be skipped with that evidence stated.
5. If REJECT, perform next new-family discovery cycle (≥3 repo-new mechanism candidates, ≥3 categories, NF scoring), resolve/reassess NF-04/05/11/12 decisive risks with evidence, pre-register highest-information feasible candidate as H93. Do not re-optimize H92 without a materially different pre-registered mechanism. Never weaken gates or modify published/certified artifacts.
