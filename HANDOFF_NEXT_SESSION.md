# HANDOFF_NEXT — After Cycle 56 / H142 (2026-11-08)

## Completed this cycle
- **H142 / NF-20261108-03 — SPY timing from turn-of-quarter window-dressing/rebalancing flows (calendar/auction): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_03_spy_toq_window/summary.json` (+ `grid.csv`, `data_meta.json`, 31.45s)
  - Runner: `run_nf_20261108_03_spy_toq_window.py`
  - Tests: `tests/test_nf_20261108_03_spy_toq_window.py` (5 passed)
  - Data (free/public yfinance, PIT): SPY daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Selected (train-only 4-fold WF mean Sharpe 0.8543): `end_days=1, start_days=1, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3353 engine trades, n=1260): Sharpe **0.894** fail, PF **1.163** fail, max DD **-3.41%** pass, trades **3353** pass, WF stability **1.047** pass, worst-regime rolling-252 **-1.220** fail, benchmark p **0.953** / IR **-0.722** fail, perturbation **0.996** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.111**/1.053/-10.17%/972 (much weaker — not pure noise); **inverse TOQ regime** 0.914/1.166/-2.93%/3353 (comparable, no clear directional falsifier; not a validated edge under pre-registered de-risking mapping).
  - **Integrity note:** the untracked runner had numpy/pandas mask handling bugs, duplicate definitions, wrong NF/H IDs/output path, and an incorrect inverse ablation; it was repaired (pandas 3.x-safe metrics, Series masks) and re-executed. Artifact numbers are from the corrected **REAL** run (train/val/test metrics differ).
  - Repo-new turn-of-quarter calendar observable; distinct institutional cycle from H91 turn-of-month (REJECT 3/9). No validated edge under pre-registered design.
  - `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified; `ruff check/format` clean. No commit/push.

## Discovery (Cycle 56)
- Lineage reconciled to H141: H85–H141 all rejected/recorded. Directive §4 discovery performed: >=3 repo-new candidates across >=3 broad mechanism categories scored (NF-20261108-03 TOQ calendar 4.38, NF-20261108-04 triple witching 4.00 subclass of H140, NF-20261108-05 overnight/intraday flow 3.68). NF-20261108-03 selected/pre-registered as **H142** and executed this session.
- Next unused H-ID after H142 (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261108_03_spy_toq_window.py tests/test_nf_20261108_03_spy_toq_window.py` — clean.
- `python3 -m ruff format --check ...` — clean.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261108_03_spy_toq_window.py` — **5 passed**.
- H142 artifact verified REAL (re-executed): `.experiments/nf_runs/nf_20261108_03_spy_toq_window/summary.json` = **REJECT 4/8** (Sharpe 0.894 / PF 1.163 / maxDD -3.41% / trades 3353 / WF 1.047 / worst-regime -1.220 / benchmark p 0.953 / IR -0.722 / perturbation 0.996).

## Unresolved / risks
- H142 is a low-vol near-full-exposure overlay (maxDD -3.41%) but has no benchmark edge and worst-regime collapses; inverse (0.914) is comparable, giving no clean directional falsifier for the de-risking mapping.
- Calendar/flow classes adjacent to H91 (turn-of-month REJECT 3/9), H140 (monthly OPX REJECT 4/8), H142 (TOQ REJECT 4/8) are now tested; NF-20261108-04 triple witching is a subclass of H140 and needs a **materially different** construction to avoid redundancy.
- Correlation class (H96/H127/H134/H137) and RV-divergence class (H138/H139) heavily rejected; held NF-49/NF-52 need clearly distinct designs.
- All H85–H142 rejected: no validated edge found across ~58 hypotheses; continuation requires genuinely new mechanism categories with explicit independence from rejected construction classes.
- **Pandas 3.x engine incompatibility:** `BacktestResult.trades` is a DataFrame; any runner using `if bt.trades:` / `if trade_dates:` truthiness on it will crash. New runners must use `.empty`/`len()` guards.

## Precise next task (Cycle 57, directive §4)
1. Reconcile lineage to H142 (H85–H142 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held NF-20261107-49/52/11/14(48)/31, NF-20261108-04/05 and deferred pool with concrete evidence (no silent drops). Explicitly justify independence from rejected construction classes (correlation H96/H127/H134/H137, RV-divergence H138/H139, OPX proximity H140, TOQ/calendar H142/H91, IV spread H125/H126).
3. Pre-register highest expected-information feasible candidate as **next H-ID after H142** in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 57 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Implement runner + focused tests (pandas-3 safe), run ruff, run focused pytest, execute, record verdict/artifacts; update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
