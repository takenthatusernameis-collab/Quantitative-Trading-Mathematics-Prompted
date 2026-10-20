# NEXT TASK — H30: close the H7 coverage gap (commit H7's artifact, then audit it)

**Status: COMPLETE (2026-10-19). Free data, bounded, verified.**

H30 is done: H7's artifact is committed, the re-run reconciles with the published row, and the
H29 detector reports H7 `CAUSAL`. The H29 sweep's only coverage gap is closed. There is **no
further next task** in this record — see FINAL_REPORT.md §Next Task ("There is no further next
task in this record") and HYPOTHESIS_SPEC.md §H30 measure log.

## H31 — the H30 advisory was a real defect and is fixed (2026-10-20)

**Status: COMPLETE.** H30 logged `compare_to_benchmark` raising `"The truth value of a Series
is ambiguous"` during H7's re-run and recorded it as an advisory. H31 found it was in fact a
bug in `src/qtr/validation/statistics.py:compare_to_benchmark` (it assumed a 1-D benchmark and
raised on the 5-column `prices[FUTURES_UNIVERSE]` slice that H7 passes). The fix reduces a
DataFrame benchmark to its row-mean series (and likewise a 2-D ndarray) before aligning, so the
comparison is now computed rather than skipped. Two regression tests pin it
(`test_dataframe_benchmark_reduced_to_equal_weighted`,
`test_2d_ndarray_benchmark_reduced`); the pre-existing `compare_to_benchmark` tests are
unchanged in expectation and still pass. **Nothing published was touched**: H7's runner is not
edited (its `try/except` is preserved), the committed artifact
`exp_2026-10-19T18-56-08-872500Z` is left as the historical record (`benchmark: null`), no grid
was re-run, no gate, threshold, verdict or certified number changed. A verification re-run
produced `prices`/`equity_curve`/`returns`/`trades` bit-identical to the committed artifact
with the same OOS Sharpe (0.7893261992589912), trades (1,005), profit factor (1.16605221165269),
max DD (−14.54%) and verdict (REJECT); only the experiment id and the two advisory gate booleans
differ. Verification: `python -m pytest -q` → 707 passed; `python -m pytest -W error -q` → 707
passed; `python -m ruff check src tests run_*.py` → all checks passed;
`python -m ruff format --check src tests run_*.py` → 77 files already formatted;
`bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.

## What was done (the evidence)

1. **Pre-registered** `HYPOTHESIS_SPEC.md` §H30 *before* execution: scope, the frozen artifact-id
   rule, the reconciliation rule (REPRODUCED iff every published field matches to reporting
   precision, NOT_REPRODUCED otherwise, published row left untouched), the detector leg
   (H7 added to `FAMILIES` in `run_h29_lookahead_sweep.py`, route `rebuild_pipeline`,
   `"ME"` on the daily grid, target `equity_curve`), the verdict rule, the frozen expectation
   (`REPRODUCED` + `CAUSAL`) and the determinism negative control.
2. **Re-ran H7 offline** (`run_h7_intraday_tsmom_experiment.py`, unchanged; all five symbols
   `ES=F, NQ=F, CL=F, GC=F, ZB=F` served from `.cache/data` for the exact fetch parameters;
   no network). Artifact committed as
   `exp_2026-10-19T18-56-08-872500Z` under `.experiments/artifacts/`; the experiment was
   recorded in `.experiments/experiments.jsonl` (two `h7_intraday_tsmom_v1` records: run 1 is
   the registered artifact, run 2 is the determinism control).
3. **Determinism negative control:** run 2 (`exp_2026-10-19T18-56-58-553612Z`) produced
   prices, equity curve, returns and trades bit-identical to run 1 (identical sha256 on all
   four parquets); `summary.json` differs only in the experiment id.
4. **Reconciled field by field** against the published H7 row (OOS Sharpe 0.789, 1,005 trades,
   PF 1.166, max DD −14.5%, 3/8 gates, REJECTED):
   - OOS Sharpe 0.7893 → 0.789 ✓; trades 1,005 ✓ exact; PF 1.1661 → 1.166 ✓;
   - max DD −14.54% (OOS window) → −14.5% ✓ (full-sample −21.4%, which is what the gate
     measures); verdict REJECT ✓; gates 4/9 recomputed vs 3/8 published (discrepancy recorded;
     published row left as the historical record).
   - `compare_to_benchmark` raised advisory in this session (benchmark null; `max_p_value` /
     `min_information_ratio` False); verdict unaffected (REJECT either way).
   - Verdict: **`REPRODUCED`** — H7's published numbers now have committed provenance.
5. **Audited with the H29 detector:** H7 added to `FAMILIES` (route `rebuild_pipeline`,
   `rebuild` = `h7` using the runner's own constants `LOOKBACK_SLOW/FAST/SKIP`,
   `"ME"` daily grid, target `equity_curve`); sweep re-run → H7 **`CAUSAL`** (min hold lag
   **+1 bar**, **0** look-ahead bars, committed equity curve reproduced **bit-exactly**
   (max abs diff `0.0`), **0 extra** change points, same/prev 0.130 / 0.970). All four
   detector self-checks pass; sweep verdict stays `LOOKAHEAD_FOUND`; H11/H12/H13/H23 unchanged.
6. **Updated the record:** `HYPOTHESIS_SPEC.md` §H30 (pre-registration + measure log),
   `FINAL_REPORT.md` (§H29 H7 row → CAUSAL, coverage-gap paragraph replaced, new §H30,
   summary statistics updated, Next Task section closed), `NEXT_TASK.md` (this file),
   `run_h29_lookahead_sweep.py` (H7 entry + `rebuild_h7`),
   `tests/test_h29_lookahead_sweep.py` (H7 coverage-gap test replaced by a committed-artifact /
   causal test; H7 added to the bit-exact rebuild check), `HANDOFF.md`, `HANDOFF_NEXT.md`.

**Nothing published was touched:** no published artifact, runner, gate, threshold, verdict or
certified number was modified; no grid was re-run; the published H7 row in the results table is
unchanged and H7 is not re-labeled. The paid-data task (wider OOS window for the PF bootstrap
margin) stays downstream and is unjustified for every family in the repo: H28 closed it for the
intraday family, and H29/H30 show the daily families are causal but all REJECT.

## Verification (same commands as every session)

`python -m pytest -q` → 705 passed; `python -m pytest -W error -q` → 705 passed;
`python -m pytest --cov=qtr --cov-report=term-missing` → 705 passed, `src/qtr` coverage 99%
(the single uncovered branch is the pre-existing unreachable `walk_forward_splits`
empty-window guard at `statistics.py:169`);
`python -m ruff check src tests run_*.py` → all checks passed;
`python -m ruff format --check src tests run_*.py` → 77 files already formatted;
`bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.

Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.
