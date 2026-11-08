# HANDOFF_CURRENT — Cycle 67 complete (H153 REJECT 4/8); prepare Cycle 68 discovery/H154

## State
- H85–H153 all rejected/recorded. H153 (NF-20261108-25, TLT-to-SPY flight-to-quality lead-lag SPY timing) executed **REJECT 4/8** (REAL). Next unused H-ID **H154** (H24/H68–H73/H76–H79 unassigned, not recycled).
- New/uncommitted (this cycle): `run_nf_20261108_25_tlt_spy_flight_quality_spy.py`, `tests/test_nf_20261108_25_tlt_spy_flight_quality_spy.py` (6 passed), artifact `.experiments/nf_runs/nf_20261108_25_tlt_spy_flight_quality_spy/summary.json` (+ `grid.csv`, `data_meta.json`). Docs updated: `HYPOTHESIS_SPEC.md` (§H153), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 67 discovery/scoring/deferred reassessment + H153 outcome), `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT.md`.
- `src/qtr` unchanged. No secrets. No published/certified artifact, gate threshold, or prior verdict modified except adding H153 records.

## What changed
- **Cycle 67 discovery (directive §4):** >=3 candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and NF-root verification before selection:
  - NF-20261108-23 USO crude-oil price→SPY lead-lag (input-cost/supply-shock transmission) — 3.25, **deferred** (ambiguous oil→equity direction; USO ETF roll/flow confounds).
  - NF-20261108-24 ^TNX 10-year Treasury yield level→SPY timing (long-rate financial-conditions regime) — 3.70, **deferred** (same-root risk vs NF-17 short-rate level stub; interest-rate-level domain).
  - NF-20261108-25 TTL Treasury→SPY flight-to-quality lead-lag (bond safe-haven flow → equity risk-off) — 3.70, **selected/executed H153** (tie-break: clearest separation from executed observables); repo-new executed directional TTL-to-SPY lead-lag (honest adjacency to H85/H141/H151/H92).
- **H153 executed (REAL):** artifact `.experiments/nf_runs/nf_20261108_25_tlt_spy_flight_quality_spy/summary.json`. Selected `mom_window=21, z_window=126, entry_scale=2.0, vol_target=0.15` (train-only 4-fold WF mean Sharpe 0.603). OOS Val+Test (3698 trades, n=1259): Sharpe **0.792** (fail), PF **1.149** (fail), max DD **-2.45%** (pass), trades **3698** (pass), WF stability **1.315** (pass), worst-regime rolling-252 **-0.671** (fail), benchmark p **0.948** / IR **-0.725** (fail), perturbation **0.997** (pass) → **REJECT 4/8**. Ablations: buy-hold SPY 0.750, random-exposure-matched **0.546** (weaker — not pure noise — but no benchmark edge), **inverse regime** **0.891** (outperforms base 0.792; pre-registered flight-to-quality direction falsified; no validated directional edge).

## What was actually verified
- `python -m ruff check run_nf_20261108_25_tlt_spy_flight_quality_spy.py tests/test_nf_20261108_25_tlt_spy_flight_quality_spy.py` → **All checks passed**.
- `python -m ruff format --check run_nf_20261108_25_tlt_spy_flight_quality_spy.py tests/test_nf_20261108_25_tlt_spy_flight_quality_spy.py` → **clean**.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_25_tlt_spy_flight_quality_spy.py` → **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_25_tlt_spy_flight_quality_spy.py` → completed (23.32s), artifact written, verdict **REJECT 4/8**. Data: 3776 aligned rows, 0 non-positive.
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 68 discovery/H154:** per `NEXT_TASK.md`. Held/deferred candidates require concrete reassessment (no silent drops): NF-20261108-23 deferred (3.25); NF-20261108-24 deferred (3.70); NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-08-17 short-rate level deferred/incomplete; NF-08-21 UNG-USO relmom deferred; NF-08-22 EFA-EEM relmom deferred.
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H153 all REJECTED. H153: benchmark/IR fail decisively (p 0.948, IR -0.725) with worst-regime collapse (-0.671); random-exposure weaker but no benchmark edge; **inverse outperforms base (0.891 vs 0.792)**, falsifying the pre-registered flight-to-quality direction. H85/H141/H151/H92 TLT/bond/lead-lag constructions tested in distinct forms — do not rerun same TLT directional-lead-lag concept without clearly distinct mechanism/design and explicit separation.
- NF-20261108-17 short-rate level tracked stub is incomplete/unverified (signal-direction mapping not verified) — do not execute as-is.
- NF-06-28 has legacy runner/test but no NF-06-28 artifact and credit adjacency to H94/H108 — verify root/artifact lineage before any use.

## One precise next task
**Execute Cycle 68 discovery and implement+run H154** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H153, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops), pre-register H154 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published/certified artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
