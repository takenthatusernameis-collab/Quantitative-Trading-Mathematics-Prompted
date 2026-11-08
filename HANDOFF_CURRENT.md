# HANDOFF_CURRENT — Cycle 68 complete (H154 REJECT 4/8); prepare Cycle 69 discovery/H155

## State
- H85–H154 all rejected/recorded. H154 (NF-20261108-17, SHY short-rate-level regime SPY timing) executed **REJECT 4/8** (REAL). Next unused H-ID **H155** (H24/H68–H73/H76–H79 unassigned, not recycled).
- Modified (this cycle, fixes broken HEAD stub): `run_nf_20261108_17_short_rate_level.py`, `tests/test_nf_20261108_17_short_rate_level.py` (6 passed). Artifact `.experiments/nf_runs/nf_20261108_17_short_rate_level/summary.json` (+ `grid.csv`, `data_meta.json`). Docs updated: `HYPOTHESIS_SPEC.md` (§H154), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 68 discovery/scoring/deferred reassessment + H154 outcome), `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT.md`.
- `src/qtr` unchanged. No secrets. No published/certified artifact, gate threshold, or prior verdict modified except adding H154 records and completing the NF-08-17 deferred stub (same root) with a verified mapping.

## What changed
- **Cycle 68 discovery (directive §4):** >=3 candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and NF-root verification before selection:
  - NF-20261108-17 SHY short-rate-level regime SPY timing (complete deferred stub with verified mapping; monetary-tightness/financial-conditions transmission) — 3.70, **selected/executed H154** (highest expected-information feasible decisive test; resolves unfinished implementation blocker per directive §3; repo-new short-rate *level* observable vs H141 TLT-SHY spread momentum).
  - NF-20261108-22 EFA-vs-EEM DM/EM relative-momentum SPY timing (international equity cross-asset risk appetite) — 3.55, **deferred** (adjacent to H144 EEM-SPY relmom REJECT 3/8 / relmom construction class).
  - NF-20261108-21 UNG-vs-USO natgas vs oil relative-momentum SPY timing (energy cross-commodity transmission) — 3.30, **deferred** (UNG/USO ETF roll/flow confounds).
- **H154 executed (REAL):** artifact `.experiments/nf_runs/nf_20261108_17_short_rate_level/summary.json`. Selected `shy_window=21, z_window=126, entry_scale=1.0, vol_target=0.15` (train-only 4-fold WF mean Sharpe 1.234). OOS Val+Test (3119 trades, n=1259): Sharpe **0.888** (fail), PF **1.199** (fail), max DD **-2.66%** (pass), trades **3119** (pass), WF stability **0.720** (pass), worst-regime rolling-252 **-0.894** (fail), benchmark p **0.946** / IR **-0.715** (fail), perturbation **0.684** (pass) → **REJECT 4/8**. Ablations: buy-hold SPY 0.750, random-exposure-matched **0.788** (weaker, some structure, no benchmark edge), **inverse regime** **0.673** (weaker than base — direction supported but no benchmark-significant edge). ^IRX avoided (yfinance non-positive values). Pre-registered verified mapping: stress on negative SHY cumulative-return z (tight/high-rate proxy).
- **Blocker resolved (evidenced):** HEAD NF-17 runner/tests were broken (`qtr.config` import / invalid `BacktestEngine`/`Settings` API); rewritten to repo-standard `run_backtest` API with focused tests (6 passed) and executed artifact produced. `src/qtr` not modified.

## What was actually verified
- `python -m ruff check run_nf_20261108_17_short_rate_level.py tests/test_nf_20261108_17_short_rate_level.py` → **All checks passed**.
- `python -m ruff format --check run_nf_20261108_17_short_rate_level.py tests/test_nf_20261108_17_short_rate_level.py` → **2 files already formatted**.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_17_short_rate_level.py` → **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_17_short_rate_level.py` → completed (20.51s), artifact written, verdict **REJECT 4/8**. Data: 3776 aligned rows, 0 non-positive.
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 69 discovery/H155:** per `NEXT_TASK.md`. Held/deferred candidates require concrete reassessment (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/20/21 deferred; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149; NF-06-03/23/24/28/30/32/33/35 deferred (verify roots; NF-06-28 legacy runner/test but no artifact, credit adjacency H94/H108); NF-07-05 deferred (data blocker); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween seasonal held (3.90); NF-08-20 IEF RV stress deferred (adj H151/TLT RV); NF-08-21 UNG-USO relmom deferred (3.30); NF-08-22 EFA-EEM relmom deferred (3.55); NF-20261108-23 deferred (3.25); NF-20261108-24 deferred (3.70, same-root risk vs NF-17 short-rate level).
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H154 all REJECTED. H154: benchmark/IR fail decisively (p 0.946, IR -0.715) with worst-regime collapse (-0.894); random-exposure weaker (some structure) but no benchmark edge; inverse weaker than base (direction supported) — no validated timing edge. H141 tested TLT-SHY term-spread momentum (different observable); do not rerun same short-rate-level construction without clearly distinct mechanism/design and explicit separation.
- NF-20261108-24 (^TNX 10y yield level) deferred due to same-root risk vs NF-17 short-rate *level* — do not select without explicit root-separation justification.
- NF-06-28 has legacy runner/test but no NF-06-28 artifact and credit adjacency to H94/H108 — verify root/artifact lineage before any use.
- NF-08-13 ES-SPY basis stub is not decision-ready (basis construction/roll-adj) — do not execute as-is.

## One precise next task
**Execute Cycle 69 discovery and implement+run H155** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H154, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops), pre-register H155 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published/certified artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
