# HANDOFF_NEXT — After Cycle 68 / H154 (2026-11-08)

## Completed this cycle
- **H154 / NF-20261108-17 — SPY timing from short-rate level regime (SHY cumulative-return z-score, monetary-tightness/financial-conditions transmission): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_17_short_rate_level/summary.json` (+ `grid.csv`, `data_meta.json`, 20.51s, **REAL**).
  - Runner: `run_nf_20261108_17_short_rate_level.py` (rewritten; HEAD 53c9d87 stub used invalid `BacktestEngine`/`Settings`/`qtr.config` API — fixed to repo-standard `run_backtest`).
  - Tests: `tests/test_nf_20261108_17_short_rate_level.py` (**6 passed**, rewritten for verified mapping).
  - Data (free/public, PIT): SPY + SHY yfinance daily auto-adjust, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755), 0 non-positive. ^IRX avoided (yfinance non-positive values in 2020).
  - Signal (verified/pre-registered): z-score of trailing SHY cumulative return; continuous de-risking of vol-targeted long SPY when SHY weak (**negative** z = yields high/tight); 1-bar delay via engine `signals.shift(1)`, long-only, MAX_POS=0.5, 1bp+1bp equity costs.
  - Selected (train-only 4-fold WF mean Sharpe 1.234): `shy_window=21, z_window=126, entry_scale=1.0, vol_target=0.15`.
  - OOS Val+Test (3119 engine trades, n=1259): Sharpe **0.888** fail, PF **1.199** fail, max DD **-2.66%** pass, trades **3119** pass, WF stability **0.720** pass, worst-regime rolling-252 Sharpe **-0.894** fail, benchmark p **0.946** / IR **-0.715** fail, perturbation min ratio **0.684** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.788**/1.183/-5.70%/1258 (weaker, some structure, no benchmark edge); **inverse regime** (de-risk when SHY strong / positive z = loose) **0.673**/1.143/-3.94%/3102 — **weaker than base** (direction supported, no benchmark edge).
  - Honest adjacency: repo-new executed short-rate-*level* SHY observable; distinct from H141 (TLT-SHY term-spread *momentum*, a spread) and other bond/equity-bond families. No validated edge under pre-registered H154. No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

## Discovery (Cycle 68, directive §4)
- Reconciled lineage to H153; **H85–H154 all rejected/recorded**. Next unused H-ID: **H155** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **NF root integrity (honest):** NF-20261108-17 treated as same-root deferred stub (broken/unverified implementation, no artifact) and completed with verified mapping — not a new root collision. NF-20261108-22 (EFA-EEM DM/EM relmom, 3.55) and NF-20261108-21 (UNG-USO, 3.30) verified unused and deferred. NF-20261108-23 (3.25) and NF-20261108-24 (3.70, same-root risk vs NF-17 short-rate level) remain deferred. No H99/H149-style collisions.
- Candidates scored (25/25/20/15/10/5): NF-20261108-17 **3.70** selected/executed as H154; NF-20261108-22 **3.55** deferred; NF-20261108-21 **3.30** deferred.
- Deferred/held reassessed (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/20/21 deferred (NF-17 executed H154; NF-20 executed H110); NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 deferred (verify roots; NF-06-28 legacy runner/test but no artifact, credit adjacency H94/H108); NF-07-05 deferred (data blocker); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween seasonal held (3.90); NF-08-20 IEF realized-vol stress deferred (adj H151/TLT RV); NF-08-21 UNG-USO relmom deferred (3.30); NF-08-22 EFA-EEM relmom deferred (3.55); NF-20261108-23 deferred (3.25); NF-20261108-24 deferred (3.70, same-root risk vs NF-17 short-rate level).

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public data only (yfinance). No gate weakening. No commit/push.

## Verified this session
- `python -m ruff check run_nf_20261108_17_short_rate_level.py tests/test_nf_20261108_17_short_rate_level.py` — clean.
- `python -m ruff format --check run_nf_20261108_17_short_rate_level.py tests/test_nf_20261108_17_short_rate_level.py` — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_17_short_rate_level.py` — **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_17_short_rate_level.py` — **REAL** verdict **REJECT 4/8**; artifact written.

## Unresolved / risks
- H154 fails Sharpe/PF/worst-regime/benchmark; random exposure weaker (some structure) but no benchmark edge; inverse weaker than base (direction supported) — no validated timing edge. Do not promote.
- NF-20261108-24 (^TNX 10y yield level) deferred due to same-root risk vs NF-17 short-rate level — requires explicit root-separation justification before selection.
- NF-06-28 has legacy runner/test but no artifact; root/credit adjacency must be verified before any use.
- NF-08-13 ES-SPY basis stub not decision-ready (basis construction/roll-adj).
- Correlation, RV-divergence, relmom, IV/vol, rates/term/spread, short-rate level, breadth, IVOL, overnight/gap, FX-strength, institutional positioning, calendar seasonality, TLT RV, SLV-GLD relmom, and TLT flight-to-quality lead-lag classes have executed rejections — future candidates must demonstrate materially different mechanism/observable and justify independence.
- Search space heavily depleted (H85–H154 all rejected); Cycle 69 must complete the >=3-candidate, >=3-category discovery before selecting H155.

## Precise next task (Cycle 69, directive §4)
See `NEXT_TASK.md`. In summary: reconcile lineage to H154; propose >=3 repo-new candidates across >=3 broad categories with honest scoring; verify NF roots; pre-register highest-expected-information feasible candidate as **H155**; implement runner + focused tests; run ruff + focused pytest; execute; record verdict/artifacts; update docs. Free/public data only; no gate weakening; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
