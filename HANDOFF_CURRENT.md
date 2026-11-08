# Handoff — Current Session (Cycle 69 complete, H155 REJECT)

## What changed
- **Cycle 69 discovery (directive §4):** Reconciled lineage to H154 (H85–H154 all rejected/recorded). Proposed/scored 3 repo-new/decisive candidates across 3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). **NF root integrity:** NF-20261108-24 (^TNX 10Y yield level) was deferred Cycles 67-68 due to same-root risk vs NF-17/H154 short-rate *level* (broad rates-level domain). NF-17/H154 executed **REJECT 4/8** (Cycle 68), resolving the short-end root; NF-24 executed as H155 with explicit maturity/instrument/channel separation (10Y vs 1-3Y, ^TNX yield index level vs SHY ETF price return, long-end discount-rate/term-premium vs short-end policy-rate tightness). NF-20261108-26 (GLD realized-vol stress, 3.50; standalone GLD RV vs H149 RV-difference / H151 TLT RV adjacency) and NF-20261108-27 (EWJ-vs-SPY relmom, 3.55; relmom class adj, EWJ only in H2 universe spec) verified unused/deferred. NF-22 (3.55), NF-21 (3.30), NF-23 (3.25) remain deferred. No H99/H149-style collisions.
- **Candidates:** NF-20261108-24 ^TNX 10Y yield-level regime SPY timing (3.70, **selected/executed as H155**); NF-20261108-27 EWJ-vs-SPY relmom (3.55, deferred); NF-20261108-26 GLD RV stress (3.50, deferred). Selection justified: highest score and feasible decisive maturity-distinct test now that H154 closed the short-rate root.
- **H155 pre-registered & executed (NF-20261108-24):** Added `run_nf_20261108_24_tnx_10y_level_spy.py` and `tests/test_nf_20261108_24_tnx_10y_level_spy.py` (6 tests). `src/qtr` unchanged. `ruff check/format` clean; focused pytest **6 passed**. Executed REAL → **REJECT 5/8**. Updated `HYPOTHESIS_SPEC.md` §H155, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 69, `NEXT_TASK.md` (Cycle 70 / H156), `HANDOFF_NEXT.md`, this handoff.

## H155 result (REAL, pre-registered gates)
- Mechanism (maturity-distinct from H154): 10Y Treasury yield-level (^TNX) z-score regime (long-end discount-rate/financial-conditions). Stress on **positive** z (abnormally high 10Y yield) de-risks vol-targeted long SPY. Honest adjacency: same broad rates-level domain as H154 short-rate SHY level (REJECT 4/8) and H141 term-spread momentum (REJECT 5/8); different maturity/instrument/channel.
- Data: SPY+^TNX 3774 rows 2010-01-04→2025-01-03 (train 2514 / val 505 / test 755), 0 non-positive. Free/public yfinance auto-adjust.
- Selected (train-only 4-fold WF): `z_window=126, entry_scale=2.0, vol_target=0.15` (WF mean 1.006).
- OOS Val+Test (3413 trades, n=1259): Sharpe **1.091** pass, PF **1.250** fail, maxDD **-2.66%** pass, trades **3413** pass, WF stability **1.084** pass, worst-regime rolling-252 Sharpe **-0.289** fail, benchmark p **0.952** / IR **-0.696** fail, perturbation **0.990** pass → **5/8 REJECT**.
- Ablations (OOS): buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.247**/1.057/-4.98%/1258 (much weaker — not pure noise — but no benchmark edge); **inverse regime** (de-risk when ^TNX low / negative z) **0.837**/1.162/-3.20%/3438 — weaker than base (direction supported, no benchmark edge).
- Verdict: **REJECT (5/8)**. Passes Sharpe but fails PF (1.250, narrow miss)/worst-regime/benchmark; random/inverse support direction but no benchmark-significant edge (p=0.952, IR=−0.696). No gate weakened.

## Actually verified
- `python -m ruff check run_nf_20261108_24_tnx_10y_level_spy.py tests/test_nf_20261108_24_tnx_10y_level_spy.py` — All checks passed.
- `python -m ruff format --check run_nf_20261108_24_tnx_10y_level_spy.py tests/test_nf_20261108_24_tnx_10y_level_spy.py` — clean (after format).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_24_tnx_10y_level_spy.py` — **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_24_tnx_10y_level_spy.py` — completed; artifact `.experiments/nf_runs/nf_20261108_24_tnx_10y_level_spy/summary.json` written (+ `grid.csv`, `data_meta.json`, 8.53s). Verdict **REJECT 5/8**.

## Unresolved / constraints
- H85–H155 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed. Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. H155 runner/tests/docs and experiment artifacts are uncommitted local changes.
- `src/qtr` pinned full gates were **not rerun** (no `src/qtr` change). If `src/qtr` is touched, run: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## Approaches that failed / evidence (do not blindly repeat)
- H155 (10Y yield level, this cycle) failed PF/worst-regime/benchmark; Sharpe passed but no benchmark edge; random-exposure much weaker (not noise) and inverse weaker (direction supported). Do not rerun same construction.
- NF-24 deferred same-root risk is now resolved by H154 execution; do not re-defer NF-24/H155 root as "blocked by NF-17" — it is executed REJECT.
- NF-08-13 ES-SPY futures basis stub only (not decision-ready). NF-06-28 legacy runner/test but no artifact (credit adjacency H94/H108).
- NF-20261108-26 (GLD RV stress) adjacent to H151/H149 — must justify standalone-observable separation before execution. NF-20261108-27 (EWJ-vs-SPY relmom) is in relmom construction class (H144/H145/H152 rejects).

## One precise next task
**Execute Cycle 70 discovery and implement+run H156** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H155, propose >=3 repo-new candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops) — **verify NF roots against executed H-IDs/artifacts before selection**. Pre-register H156 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/`HANDOFF_NEXT.md`. Justify independence from rejected classes including 10Y yield-level H155 and all prior listed classes. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless evidenced defect requires it (then rerun pinned full gates).
