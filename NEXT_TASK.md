# NEXT_TASK.md — Cycle 74 complete (H160 executed)

## Status: Cycle 74 complete — H160 RESOLVED: REAL executed 2026-11-09, **REJECT 4/8**

**Mechanism (repo-new observable):** Cross-sectional IVOL-dispersion regime SPY timing — z-score of trailing cross-sectional std of residual (vs SPY) IVOL across 16 liquid ETFs; de-risk vol-targeted long SPY when dispersion abnormally positive (idiosyncratic-risk stress). `signals.shift(1)` 1-bar delay, long-only, Equity CostModel defaults.

**Data:** SPY + 16 ETFs, yfinance daily auto-adjust Close 2010-01-04→2026-10-30, 4233 rows (train n=2515 ≤2019-12-31; val 2020–2022 n=756; test protected 2023–2026 n=961; OOS Val+Test n=1716).

**Selected (train-only 4-fold WF mean Sharpe 0.827):** `ivol_lookback=63, z_window=252, entry_scale=2.0, vol_target=0.15`.

**OOS Val+Test (3675 trades, n=1716):** Sharpe **0.847** (fail ≥1.0), PF **1.167** (fail ≥1.3), max DD **-2.35%** (pass), trades **3675** (pass), WF stability **1.046** (pass), worst-regime rolling-252 Sharpe **-1.064** (fail ≥0.3), benchmark p **0.978** / IR **-0.748** (fail), perturbation min ratio **0.945** (pass). Train Sharpe 0.810.

**Ablations (OOS):** buy-hold SPY **0.792**/1.164/-33.72%/1; random-exposure-matched **0.286**/1.104/-2.75%/1736 (weaker — structure, no edge); **inverse regime** **0.858**/1.169/-2.66%/4037 (≈/slightly stronger than base — direction falsified); return-dispersion control **0.754**/1.152/-2.91%/3662 (≈ base — IVOL dispersion adds no info beyond return dispersion).

**Verdict rationale:** Passes trades/maxDD/WF/perturbation; fails Sharpe/PF/worst-regime/benchmark. No benchmark-significant edge (p=0.978, IR=−0.748); worst-regime collapses (−1.064); inverse ≈ base (direction not supported). **No validated edge under pre-registered H160.**

**Artifact:** `.experiments/nf_runs/nf_20261109_01_ivol_dispersion_spy/summary.json` (+ `grid.csv`, `data_meta.json`, ~74s). Recorded in `HYPOTHESIS_SPEC.md` §H160 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 74. `src/qtr` unchanged; no commit/push.

**Lineage:** H85–H160 all rejected/recorded. Next unused H-ID: **H161** (H24/H68–H73/H76–H79 unassigned, not recycled). Deferred candidates carried forward: NF-20261108-29 cross-asset return dispersion (4.10). NF-20261108-31 cross-sectional IVOL dispersion **executed as H160 (REJECT 4/8)**.

## Files added (Cycle 74)
- `run_nf_20261109_01_ivol_dispersion_spy.py` — H160 runner (pre-registered statement, 48-combo grid, train-only WF selection, 8 OOS gates, ablations, falsifiers)
- `tests/test_nf_20261109_01_ivol_dispersion_spy.py` — 10 focused tests (all pass)
- `HYPOTHESIS_SPEC.md` — §H160 appended (statement, null, gates, data/splits, costs, falsifiers, result, lineage)
- `NEW_FAMILY_RESEARCH_REGISTER.md` — Cycle 74 entry appended (discovery, scoring, root-integrity check, pre-registration, result, lineage)

## Verification (all green)
- `python -m ruff check run_nf_20261109_01_ivol_dispersion_spy.py tests/test_nf_20261109_01_ivol_dispersion_spy.py` — All checks passed.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_01_ivol_dispersion_spy.py` — **10 passed**.
- `PYTHONPATH=src python run_nf_20261109_01_ivol_dispersion_spy.py` — completed; REAL verdict **REJECT 4/8**, artifact written.
- Global `ruff check src tests run_*.py` clean (H160 files included).

## No outstanding Cycle-74 work
`src/qtr` unchanged; pinned full gates not rerun (no `src/qtr` change). No commit/push (not authorized). If `src/qtr` is touched later, run: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## If a new cycle is requested (Cycle 75 / H161)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H160, propose >=3 repo-new candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), verify NF roots against executed H-IDs/artifacts before selection, pre-register H161 (next unused after H160) before validation outcomes, add runner+focused tests, `ruff check/format`, focused pytest, execute, record verdict. Do not recycle H24/H68–H73/H76–H79. Free/public data only; no gate weakening.
