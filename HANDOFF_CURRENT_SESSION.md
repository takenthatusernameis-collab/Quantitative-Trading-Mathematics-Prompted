# Handoff — Current Session (Cycle 72 complete, H158 REJECT)

## What changed
- **Cycle 72 discovery (directive §4):** Reconciled lineage to H158 (H85–H158 all rejected/recorded). Proposed/scored >=3 repo-new mechanism candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops). **NF root integrity check:** NF-20261108-29 (sector breadth, deferred 3.45), NF-20261108-31 (AUD/USD risk-on, deferred 3.65) verified unused (no runner/artifact). NF-06-28 legacy runner/test no artifact (credit adj H94/H108). NF-08-16 Halloween held (3.90, calendar adjacency H91/H140/H142). No H99/H149-style collisions.
- **Candidates:** NF-20261108-30 yield curve slope (10Y-5Y, ^TNX-^FVX) level z-score regime SPY timing (carry & term structure, 3.75) — **selected/executed as H158**; NF-20261108-31 AUD/USD commodity-currency risk-on proxy SPY timing (FX risk-appetite, 3.65, deferred; adjacency H95/H103/H106/H156); NF-20261108-29 sector breadth (% of 9 sectors above 200-day MA) SPY timing (market participation, 3.45, deferred; adjacency H115/H147). Selection justified: NF-30 chosen as highest expected-information feasible test with explicit separation from H141 spread momentum, H154 short-rate level, H155 long-rate level; NF-31/NF-29 deferred with honest adjacency disclosed.
- **H158 pre-registered & executed (NF-20261108-30):** Added `run_nf_20261108_30_yield_curve_slope_spy.py` and `tests/test_nf_20261108_30_yield_curve_slope_spy.py` (7 tests). `src/qtr` unchanged. `ruff check/format` clean; focused pytest **7 passed**. Executed REAL → **REJECT 5/8**. Updated `HYPOTHESIS_SPEC.md` §H158, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 72, `NEXT_TASK.md` (Cycle 73 / H159), `HANDOFF_NEXT.md`, this handoff.

## H158 result (REAL, pre-registered gates)
- Mechanism (repo-new observable): Yield curve slope (10Y-5Y, ^TNX-^FVX) level z-score regime (carry & term structure / macro rate regime). **Distinct from** H141 (TLT-SHY term-spread momentum, REJECT 5/8), H154 (SHY short-rate level, REJECT 4/8), H155 (^TNX 10Y yield level, REJECT 5/8), H100 (^MOVE implied rates vol, REJECT 5/9).
- Data: SPY+^TNX+^FVX 3774 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755). Free/public yfinance auto-adjust, ^FVX 0 non-positive, spread handles inversion cleanly.
- Selected (train-only 4-fold WF): `z_window=126, entry_scale=2.0, vol_target=0.15` (WF mean 0.767).
- OOS Val+Test (3507 trades, n=1259): Sharpe **1.103** pass, PF **1.234** fail, maxDD **-2.18%** pass, trades **3507** pass, WF stability **1.631** pass, worst-regime rolling-252 Sharpe **-1.612** fail, benchmark p **0.941** / IR **-0.691** fail, perturbation **0.979** pass → **5/8 REJECT**.
- Ablations (OOS): buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.412**/1.195/-2.21%/1283 (much weaker — signal not noise — but no benchmark edge); **inverse regime** (de-risk when curve abnormally steep / positive z) **0.360**/1.073/-3.15%/3522 — materially weaker; direction supported, no benchmark edge.
- Verdict: **REJECT (5/8)**. Passes Sharpe but fails PF/worst-regime/benchmark; no benchmark-significant edge (p=0.941, IR=−0.691), worst-regime collapses. No gate weakened.

## Actually verified
- `python -m ruff check run_nf_20261108_30_yield_curve_slope_spy.py tests/test_nf_20261108_30_yield_curve_slope_spy.py` — All checks passed.
- `python -m ruff format --check run_nf_20261108_30_yield_curve_slope_spy.py tests/test_nf_20261108_30_yield_curve_slope_spy.py` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_30_yield_curve_slope_spy.py` — **7 passed**.
- `PYTHONPATH=src python run_nf_20261108_30_yield_curve_slope_spy.py` — completed; artifact `.experiments/nf_runs/nf_20261108_30_yield_curve_slope_spy/summary.json` written (+ `grid.csv`, `data_meta.json`, 9.72s). Verdict **REJECT 5/8**.

## Unresolved / constraints
- H85–H158 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed. Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. H158 runner/tests/docs and experiment artifacts are uncommitted local changes.
- `src/qtr` pinned full gates were **not rerun** (no `src/qtr` change). If `src/qtr` is touched, run: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## Approaches that failed / evidence (do not blindly repeat)
- H158 (yield curve slope 10Y-5Y level z-score, this cycle) failed PF/worst-regime/benchmark; random-exposure much weaker (not noise) but no benchmark edge; inverse weaker (direction supported). Do not rerun same construction.
- NF-20261108-31 AUD/USD risk-on **deferred** (3.65, FX-risk-appetite adjacency H95/H103/H106/H156). Do not execute as-is without decisive separation from FX direction/RV stress classes.
- NF-20261108-29 Sector breadth **deferred** (3.45, breadth adjacency H115/H147). Do not execute as-is without decisive separation from breadth construction class.
- NF-04 blocked (no free PIT term-structure/roll proxy). NF-11r/NF-06-18 same root as NF-11 (H141). NF-06-11 infeasible. NF-08-13 ES-SPY basis stub only (not decision-ready).

## One precise next task
**Execute Cycle 73 discovery and implement+run H159** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H158, propose >=3 repo-new candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops) — **verify NF roots against executed H-IDs/artifacts before selection**. Pre-register H159 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/`HANDOFF_NEXT.md`. Justify independence from rejected classes including yield curve slope H158 and all prior listed classes. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless evidenced defect requires it (then rerun pinned full gates).