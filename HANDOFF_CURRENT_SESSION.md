# Handoff — Current Session (Cycle 65 complete, H151 REJECT)

## What changed
- **Cycle 65 discovery (directive §4):** Reconciled lineage to H150 (H85–H150 all rejected/recorded). Proposed/scored >=3 repo-new mechanism candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops). **NF root integrity check:** NF-20261108-17 (short-rate level, ^IRX/SHY proxy) listed deferred in Cycle 64 but a tracked docstring-only stub `run_nf_20261108_17_short_rate_level.py` exists (HEAD 2f9c68e, not decision-ready/executed, no tests/artifacts, unverified signal-direction mapping) — NF-17 remains **deferred/incomplete**, not reused. NF-20261108-16 held (no runner/artifact). NF-20261108-18 verified unused. NF-20261108-19 (SLV-GLD relmom, repo-new SPY-timing observable; SLV only in H88 RV context) verified unused. NF-20261108-20 (IEF RV) verified unused. No H99/H149-style collisions.
- **Candidates:** NF-20261108-18 TLT realized-volatility stress SPY timing (bond-market vol transmission, 3.65) — **selected/executed as H151**; NF-20261108-19 SLV-vs-GLD precious-metals relmom SPY timing (3.65, deferred; adjacency H88/H145/GLD families); NF-20261108-16 Halloween semi-annual seasonal (3.90 raw, **held** — calendar adjacency H91/H140/H142 rejects). Selection justified: NF-16 held due calendar-class adjacency despite higher raw score; NF-18 chosen over tied NF-19 for smallest decisive test and clearer separation from executed observables.
- **H151 pre-registered & executed (NF-20261108-18):** Added `run_nf_20261108_18_tlt_rv_stress_spy.py` and `tests/test_nf_20261108_18_tlt_rv_stress_spy.py` (6 tests). `src/qtr` unchanged. `ruff check/format` clean; focused pytest **6 passed**. Executed REAL → **REJECT 5/8**. Updated `HYPOTHESIS_SPEC.md` §H151, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 65, `NEXT_TASK.md` (Cycle 66 / H152), `HANDOFF_NEXT.md`, this handoff.

## H151 result (REAL, pre-registered gates)
- Mechanism (repo-new observable): TLT realized-volatility z-score regime (bond-market vol transmission). **Distinct from** H141 (TLT-SHY term-spread momentum, REJECT 5/8), H96/H127 (TLT correlations), H100 (^MOVE implied rates vol, REJECT 5/9).
- Data: SPY+TLT 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755). Free/public yfinance auto-adjust, 0 non-positive.
- Selected (train-only 4-fold WF): `rv_window=63, z_window=252, entry_scale=1.0, vol_target=0.15` (WF mean 0.935).
- OOS Val+Test (2705 trades, n=1259): Sharpe **1.060** pass, PF **1.251** fail, maxDD **-1.94%** pass, trades **2705** pass, WF stability **1.133** pass, worst-regime rolling-252 Sharpe **-1.193** fail, benchmark p **0.937** / IR **-0.684** fail, perturbation **0.957** pass → **5/8 REJECT**.
- Ablations (OOS): buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.273**/1.062/-7.10%/1258 (much weaker — signal not noise — but no benchmark edge); **inverse regime** (de-risk when TLT RV abnormally LOW / negative z) **0.532**/1.114/-3.15%/2769 — materially weaker; direction supported, no benchmark edge.
- Verdict: **REJECT (5/8)**. Passes Sharpe but fails PF/worst-regime/benchmark; no benchmark-significant edge (p=0.937, IR=−0.684), worst-regime collapses. No gate weakened.

## Actually verified
- `python -m ruff check run_nf_20261108_18_tlt_rv_stress_spy.py tests/test_nf_20261108_18_tlt_rv_stress_spy.py` — All checks passed.
- `python -m ruff format --check run_nf_20261108_18_tlt_rv_stress_spy.py tests/test_nf_20261108_18_tlt_rv_stress_spy.py` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_18_tlt_rv_stress_spy.py` — **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_18_tlt_rv_stress_spy.py` — completed; artifact `.experiments/nf_runs/nf_20261108_18_tlt_rv_stress_spy/summary.json` written (+ `grid.csv`, `data_meta.json`, 14.09s). Verdict **REJECT 5/8**.

## Unresolved / constraints
- H85–H151 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed. Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. H151 runner/tests/docs and experiment artifacts are uncommitted local changes. Tracked stub `run_nf_20261108_17_short_rate_level.py` remains incomplete/deferred (not executed).
- `src/qtr` pinned full gates were **not rerun** (no `src/qtr` change). If `src/qtr` is touched, run: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## Approaches that failed / evidence (do not blindly repeat)
- H151 (TLT RV stress, this cycle) failed PF/worst-regime/benchmark; random-exposure much weaker (not noise) but no benchmark edge; inverse weaker (direction supported). Do not rerun same construction.
- NF-20261108-17 ^IRX/SHY short-rate *level* is **deferred/incomplete** (tracked stub, unverified signal-direction mapping, no tests/artifacts). Do not execute NF-17 as-is; make decision-ready first and verify mechanism-to-signal mapping.
- NF-04 blocked (no free point-in-time term-structure/roll proxy). NF-11r is NF-11 resolution path (SAME root), not repo-new. NF-06-11 CBOE PC ratio infeasible. NF-20261108-13 ES-SPY futures basis stub only (not decision-ready).

## One precise next task
**Execute Cycle 66 discovery and implement+run H152** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H151, propose >=3 repo-new candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops) — **verify NF roots against executed H-IDs/artifacts before selection**. Pre-register H152 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/`HANDOFF_NEXT.md`. Justify independence from rejected classes including TLT realized-vol stress H151 and all prior listed classes. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless evidenced defect requires it (then rerun pinned full gates).
