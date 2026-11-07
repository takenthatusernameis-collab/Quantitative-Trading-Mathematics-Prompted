# HANDOFF_CURRENT_SESSION — 2026-11-06 (Kilo, Cycle 26 complete)

## What changed
- **Discovery (directive §4):** Reconciled lineage to H111 (H85–H111 REJECTED). Proposed/scored 3 candidates across >=3 broad categories: NF-20261106-25 cross-sectional MAX/lottery-demand regime timing SPY (investor attention/higher-moment cross-sectional, 3.80, selected/executed as H112), NF-20261106-23 XHB/XLU housing-rate-sensitivity (3.55, deferred — rates/financial-conditions channel adjacency), NF-20261106-24 XBI/XLV biotech funding-risk-appetite (3.35, deferred — weak separation from risk-on/rates-duration beta). Reassessed deferred NFs with concrete evidence (no silent drops): NF-04 blocked (no free point-in-time term-structure/roll proxy), NF-05/07/08/10/11/13/15/17/20/21 deferred (turnover/cost/weak/adjacency/event-construction), NF-11r/NF-06-18 data-resolved but NF-11 resolution path (SAME root, not repo-new), NF-06-11 CBOE PC ratio infeasible (no free yfinance), NF-20261106-03 VVIX deferred (VIX-complex adjacency to H104/H89/H17), NF-20261106-21 RSP/SPY deferred (breadth adjacency/exploratory weakness), NF-20261106-23/24 reassessed/deferred.
- **H112 pre-registered/executed (NF-20261106-25):** Added `run_nf_20261106_25_max_lottery.py`, `tests/test_nf_20261106_25_max_lottery.py` (10 tests), updated `HYPOTHESIS_SPEC.md` §H112 from TBD to recorded outcome, appended `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 26. `src/qtr` unchanged.

## Verified
- `python -m ruff check run_nf_20261106_25_max_lottery.py tests/test_nf_20261106_25_max_lottery.py` — All checks passed.
- `python -m ruff format --check ...` — 2 files already formatted (after `ruff format`).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261106_25_max_lottery.py` — **10 passed**.
- `python run_nf_20261106_25_max_lottery.py` — **REJECT 3/8**, `exp_2026-11-06T16-36-24-805357Z`, 1.26s, artifact `.experiments/nf_runs/nf_20261106_25_max_lottery/summary.json`.
- Data feasibility: SPY + 15 signal ETFs (QQQ/IWM/EFA/EEM/XLE/XLF/XLV/XLI/XLB/XLP/XLU/XLY/XLK/GLD/TLT) 4233 rows, 0 non-positive, 2010-01-04–2026-10-30 (verified via cached yfinance).

## H112 result (REAL, pre-registered gates)
- Selected (train-only 4-fold WF): `lookback=21, z_window=252, entry_scale=2.0, vol_target=0.15` (selection WF mean 1.430, train Sharpe 0.740).
- OOS Val+Test (145 trades): Sharpe **0.800** fail, PF **1.152** fail, DD **-13.67%** pass, trades **145** fail (<200), WF **1.081** pass, worst-regime rolling-252 min **-0.928** fail (worst quartile -0.207), benchmark-p **1.0**/IR **-0.116** fail, perturbation **0.950** pass.
- Ablations (OOS): buy-hold SPY 0.720/1.148/DD -18.21%; random-exposure-matched 0.549/1.129/DD -7.24%; inverse-stress-long 0.112/1.103/DD -10.58%.
- Verdict rationale: perturbation-stable, beats random/inverse, but no validated risk-adjusted edge vs buy-hold; low trade count (145). Specific pre-registered elevated-MAX risk-reduction mapping tested; does not test all MAX/lottery-demand constructions. No gate weakened.

## Unresolved / constraints
- H85–H112 all REJECTED. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed (not requested). Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. `.experiments/experiments.jsonl` and new NF-25 files are uncommitted local changes.

## Approaches that failed / evidence
- H112 (cross-sectional MAX/lottery-demand, NF-20261106-25) REJECT 3/8 — see artifact/spec/register above. Do not re-run without a materially different, pre-registered mechanism.

## One precise next task
Cycle 27 discovery per `HANDOFF_NEXT.md`/`NEXT_TASK.md` intent: reconcile lineage to H112 (next H113), propose >=3 repo-new mechanism candidates across >=3 broad categories, reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18, NF-20261106-03/21/23/24 with concrete evidence (no silent drops; NF-11r is NF-11 resolution path, not new root family; NF-06-11 infeasible), score honestly (25/25/20/15/10/5), pre-register H113 smallest decisive test, implement runner+tests, run ruff + focused pytest, execute, record verdict. Free/public data only; no gate weakening; no published artifact changes; no commit/push; `src/qtr` unchanged unless evidenced defect.


---
## Cycle 28 (2026-11-06) — Discovery / Pre-registration & Execution of H114 (NF-20261106-27)

### What changed
- **Discovery (directive §4):** Reconciled lineage to H113 (H85–H113 REJECTED). Proposed/scored 3 candidates across >=3 broad categories: NF-20261106-27 SPHB/SPLV high-beta vs low-vol style-preference leadership timing SPY (style/volatility-preference transmission, 3.70, selected/executed as H114), NF-20261106-28 JNK/LQD HY vs IG credit leadership (3.55, deferred — credit adjacency to H94/H108), NF-20261106-29 RSP/SPY breadth/participation (3.35, deferred — adjacency/exploratory). Reassessed deferred NFs with concrete evidence (no silent drops): NF-04 blocked (no free point-in-time term-structure/roll proxy), NF-05/07/08/10/11/13/15/17/20/21 deferred, NF-11r/NF-06-18 TNX-FVX data-resolved but NF-11 resolution path (SAME root, not repo-new), NF-06-11 CBOE PC ratio infeasible, NF-20261106-03/21/23/24/28 deferred (adjacency/weak separation).
- **H114 pre-registered/executed (NF-20261106-27):** Added `run_nf_20261106_27_sphb_splv_style.py`, `tests/test_nf_20261106_27_sphb_splv_style.py` (10 tests), updated `HYPOTHESIS_SPEC.md` §H114 from pre-registered to recorded outcome, appended `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 28. `src/qtr` unchanged.

### Verified
- `python -m ruff check run_nf_20261106_27_sphb_splv_style.py tests/test_nf_20261106_27_sphb_splv_style.py` — All checks passed.
- `python -m ruff format --check ...` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261106_27_sphb_splv_style.py` — **10 passed**.
- `PYTHONPATH=src python run_nf_20261106_27_sphb_splv_style.py` — **REJECT 2/8**, `exp_2026-11-06T23-06-21-278809Z`, 2.75s, artifact `.experiments/nf_runs/nf_20261106_27_sphb_splv_style/summary.json`.
- Data: SPHB/SPLV/SPY aligned 3896 rows (2011-05-05–2026-10-30, SPHB/SPLV start later than SPY; cached yfinance).

### H114 result (REAL, pre-registered gates)
- Selected (train-only 4-fold WF): `lookback=63, z_window=126, entry_scale=2.0, vol_target=0.15` (train Sharpe 0.917).
- OOS Val+Test (412 trades): Sharpe **0.684** fail, PF **1.130** fail, DD **-17.00%** fail, trades **412** pass, WF **0.746** pass, worst-regime rolling-252 min **-0.723** fail, benchmark-p **0.351**/IR **-0.153** fail, perturbation **0.906** pass.
- Ablations (OOS): buy-hold SPY 0.720/1.148/DD -18.21%; random-exposure-matched 0.549/1.129/DD -7.24%; inverse-stress-long 0.346/1.126/DD -10.86%.
- Verdict: REJECT (2/8). Perturbation-stable and beats random/inverse ablations, but no validated risk-adjusted edge vs buy-hold. Specific pre-registered defensive-rotation mapping tested. No gate weakened.

### Unresolved / constraints
- H85–H114 all REJECTED. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed (not requested). Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. New NF-27 files and uncommitted experiment artifacts remain local.

---
## Cycle 32 (2026-11-07) — Execution of H118 (NF-20261107-01)

### What changed
- **Execution (directive §4):** Lineage reconciled to H117 (H85–H117 REJECTED). H118 / NF-20261107-01 cross-sectional sector return dispersion regime timing for SPY was pre-registered (prior session) and executed this cycle. `src/qtr` unchanged. No new `src/qtr` change.
- **H118 executed:** Runner `run_nf_20261107_01_sector_dispersion_regime.py` and tests `tests/test_nf_20261107_01_sector_dispersion_regime.py` (11 tests) pre-existed, lint/format clean, focused pytest 11 passed. Experiment `exp_2026-11-07T01-16-32-274332Z`, 1.748s, artifact `.experiments/nf_runs/nf_20261107_01_sector_dispersion_regime/summary.json`. Updated `HYPOTHESIS_SPEC.md` §H118 from pre-registered to recorded outcome; appended `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 32 + H118 outcome; updated `NEXT_TASK.md` for Cycle 33.

### Verified
- `python -m ruff check run_nf_20261107_01_sector_dispersion_regime.py tests/test_nf_20261107_01_sector_dispersion_regime.py` — All checks passed.
- `python -m ruff format --check ...` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261107_01_sector_dispersion_regime.py` — **11 passed**.
- `PYTHONPATH=src python run_nf_20261107_01_sector_dispersion_regime.py` — **REJECT 4/8**, `exp_2026-11-07T01-16-32-274332Z`, 1.748s.

### H118 result (REAL, pre-registered gates)
- Selected (train-only 4-fold WF): `lookback=63, z_window=126, entry_scale=2.0, vol_target=0.15` (WF mean 1.379, train Sharpe 0.980).
- OOS Val+Test (779 trades): Sharpe **0.868** fail, PF **1.164** fail, DD **-10.19%** pass, trades **779** pass, WF **0.885** pass, worst-regime rolling-252 min **-1.215** fail, benchmark-p **1.0**/IR **-0.369** fail, perturbation **0.940** pass.
- Ablations (OOS): buy-hold SPY 0.791/1.164/DD -17.97%; random-exposure-matched **1.391/1.289/DD -14.45%**/778 (outperforms strategy — falsifies dispersion-timing information); inverse-stress-long 0.359/1.158/DD -11.37%.
- Verdict: REJECT (4/8). Perturbation-stable with ample trades/WF stability and DD improvement vs buy-hold, but no validated risk-adjusted edge. Random-exposure ablation outperforms the signal. Specific pre-registered dispersion-z mapping tested; not all dispersion-regime constructions. No gate weakened.

### Unresolved / constraints
- H85–H119 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed (not requested). Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. New H119 experiment artifact and runner/test bug fixes are uncommitted local changes.
- Next session: Cycle 34 discovery/H120 per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`.


---
## Cycle 33 (2026-11-07) — Execution of H119 (NF-20261107-02)

### What changed
- **Execution (directive §4):** Lineage reconciled to H118 (H85–H118 all rejected/recorded). H119 / NF-20261107-02 short-term cross-sectional return reversal among sector ETFs was pre-registered (prior session) and executed this cycle. `src/qtr` unchanged. No new `src/qtr` change.
- **H119 executed:** Runner `run_nf_20261107_02_cs_reversal.py` and tests `tests/test_nf_20261107_02_cs_reversal.py` (16 tests) pre-existed; four test-harness bugs fixed (row-sum gross cap MAX_LEVERAGE not MAX_POS; signal hold via ffill not fillna(0); read-only bool array `.copy()`; SPY added to test prices) and one runner bug fixed (`_inverse_signal` double `oos_mask` indexing). Lint/format clean, focused pytest 16 passed. Experiment `exp_2026-11-07T02-28-32-224963Z`, artifact `.experiments/nf_runs/nf_20261107_02_cs_reversal/summary.json`. Updated `HYPOTHESIS_SPEC.md` §H119 from pre-registered to recorded outcome; appended `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 33 + H119 outcome/lineage; updated `NEXT_TASK.md` for Cycle 34.

### Verified
- `python -m ruff check run_nf_20261107_02_cs_reversal.py tests/test_nf_20261107_02_cs_reversal.py` — All checks passed.
- `python -m ruff format --check ...` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261107_02_cs_reversal.py` — **16 passed**.
- `PYTHONPATH=src python run_nf_20261107_02_cs_reversal.py` — **REJECT 3/8**, `exp_2026-11-07T02-28-32-224963Z`.

### H119 result (REAL, pre-registered gates)
- Selected (train-only 4-fold WF): `lookback=10, vol_target=0.10` (WF mean 1.1807, train Sharpe 0.7403).
- OOS Val+Test (1494 trades): Sharpe **0.669** fail, PF **1.123** fail, DD **-18.84%** fail, trades **1494** pass, WF **0.904** pass, worst-regime rolling-252 min **-0.436** fail, benchmark-p **1.0**/IR **-0.255** fail, perturbation **0.725** pass.
- Ablations (OOS): buy-hold SPY 0.791/1.164/DD -17.97%; equal-weight sectors 0.767/1.165/DD -36.91%; random-side -0.107/0.957/DD -9.69%/686; inverse-momentum-long 0.573/1.109/DD -14.36%/1500.
- Verdict rationale: perturbation-stable, trade-rich, WF stability and random-side below strategy, but no validated cost-robust edge vs buy-hold SPY on pre-registered OOS gates (fails Sharpe/PF/DD/worst-regime/benchmark-p/IR). Specific pre-registered weakest-tercile reversal mapping tested; not all reversal constructions. No gate weakened.

### Unresolved / constraints
- H85–H119 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed (not requested). Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. New H119 experiment artifact is uncommitted local change.
- Next session: Cycle 34 discovery/H120 per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`.
