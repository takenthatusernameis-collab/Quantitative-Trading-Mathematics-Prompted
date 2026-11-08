# HANDOFF_CURRENT — Cycle 66 complete (H152 REJECT 4/8); prepare Cycle 67 discovery/H153

## State
- H85–H152 all rejected/recorded. H152 (NF-20261108-19, SLV-vs-GLD precious-metals relative-momentum SPY timing) executed **REJECT 4/8** (REAL). Next unused H-ID **H153** (H24/H68–H73/H76–H79 unassigned, not recycled).
- New/uncommitted (this cycle): `run_nf_20261108_19_slv_gld_relmom_spy.py`, `tests/test_nf_20261108_19_slv_gld_relmom_spy.py` (6 passed), artifact `.experiments/nf_runs/nf_20261108_19_slv_gld_relmom_spy/summary.json` (+ `grid.csv`, `data_meta.json`). Docs updated: `HYPOTHESIS_SPEC.md` (§H152), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 66 discovery/scoring/deferred reassessment + H152 outcome), `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT.md`.
- `src/qtr` unchanged. No secrets. No published/certified artifact, gate threshold, or prior verdict modified except adding H152 records.

## What changed
- **Cycle 66 discovery (directive §4):** >=3 candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and NF-root verification before selection:
  - NF-20261108-19 SLV-vs-GLD precious-metals relative-momentum SPY timing (cross-commodity risk-appetite transmission) — 3.65, **selected/executed H152**; repo-new executed SPY-timing pair/observable (honest adjacency to H88 GLD/SLV/DXY RV REJECT 1/9 — different observable/mechanism — and H145 GLD-vs-SPY relmom REJECT 4/8 — different signal pair).
  - NF-20261108-16 Halloween semi-annual seasonal SPY timing (calendar seasonality) — 3.90 raw but **held** (calendar-class adjacency H91/H140/H142 rejects; decayed recent evidence).
  - NF-20261108-21 UNG-vs-USO natgas/oil relative-momentum SPY timing (energy cross-commodity) — 3.30, **deferred** (ETF roll/flow confounds; lower mechanism cleanliness).
- **Deferred reassessment (no silent drops):** NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred (NF-20 executed H110); NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 deferred (NF-06-28 legacy runner/test but no artifact, credit adjacency H94/H108); NF-07-05 deferred (data blocker); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 held (3.90); NF-08-17 short-rate level deferred/incomplete (tracked stub, unverified mapping); NF-08-19 executed H152; NF-08-20 IEF RV stress deferred (adj H151/TLT RV); NF-08-21 UNG-USO relmom deferred (3.30); NF-08-22 EFA-EEM relmom deferred (adj H144).
- **H152 executed (REAL):** artifact `.experiments/nf_runs/nf_20261108_19_slv_gld_relmom_spy/summary.json`. Selected `mom_window=63, z_window=126, entry_scale=2.0, vol_target=0.15` (train-only 4-fold WF mean Sharpe 0.970). OOS Val+Test (3536 trades, n=1259): Sharpe **0.780** (fail), PF **1.158** (fail), max DD **-3.27%** (pass), trades **3536** (pass), WF stability **0.804** (pass), worst-regime rolling-252 **-1.226** (fail), benchmark p **0.949** / IR **-0.720** (fail), perturbation **0.920** (pass) → **REJECT 4/8**. Ablations: buy-hold SPY 0.750, random-exposure-matched 0.572 (weaker; not pure noise, no benchmark edge), inverse 0.761 (near base; direction not validated).

## What was actually verified
- `python -m ruff check run_nf_20261108_19_slv_gld_relmom_spy.py tests/test_nf_20261108_19_slv_gld_relmom_spy.py` → **All checks passed**.
- `python -m ruff format --check run_nf_20261108_19_slv_gld_relmom_spy.py tests/test_nf_20261108_19_slv_gld_relmom_spy.py` → **clean** (after formatting).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_19_slv_gld_relmom_spy.py` → **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_19_slv_gld_relmom_spy.py` → completed (21.38s), artifact written, verdict **REJECT 4/8**. Data: 3776 aligned rows, 0 non-positive.
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 67 discovery/H153:** per `NEXT_TASK.md`. Held/deferred candidates require concrete reassessment (no silent drops).
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H152 all REJECTED. H152: benchmark/IR fail decisively (p 0.949, IR -0.720) with worst-regime collapse (-1.226); random-exposure weaker but no benchmark edge; inverse near base (direction not validated). H88/H145/H152 precious-metals/GLD relmom/RV constructions tested in distinct forms — do not rerun same SLV-GLD relative-momentum concept without clearly distinct mechanism/design and explicit separation.
- NF-20261108-17 short-rate level tracked stub is incomplete/unverified (signal-direction mapping not verified) — do not execute as-is.
- NF-06-28 has legacy runner/test but no NF-06-28 artifact and credit adjacency to H94/H108 — verify root/artifact lineage before any use.

## One precise next task
**Execute Cycle 67 discovery and implement+run H153** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H152, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops), pre-register H153 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published/certified artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
