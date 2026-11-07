# HANDOFF_CURRENT — Cycle 41 complete (H127 REJECT 2/8); prepare Cycle 42 discovery/H128

## State
- H85–H127 all rejected/recorded. H127 (NF-20261107-15, GLD–TLT rolling return-correlation regime timing SPY) executed **REJECT 2/8**. Next unused H-ID **H128**.
- New/uncommitted (from this cycle): `run_nf_20261107_15_gld_tlt_corr.py`, `tests/test_nf_20261107_15_gld_tlt_corr.py` (8 passed), artifact `.experiments/nf_runs/nf_20261107_15_gld_tlt_corr/summary.json` (+ `grid.csv`, `data_meta.json`). Docs updated: `HYPOTHESIS_SPEC.md` (H127 pre-reg+outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 41 discovery/scoring/deferred reassessment + H127 outcome), `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT.md`.
- `src/qtr` unchanged. No secrets. No published/certified artifact, gate threshold, or prior verdict modified except adding H127 records.

## What changed
- **Cycle 41 discovery (directive §4):** >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5: NF-20261107-15 GLD–TLT rolling return-correlation regime timing SPY (3.85, **selected/executed H127**; repo-new GLD–TLT pair/channel — gold inflation-hedge vs real-rate/duration sensitivity — honest adjacency to H96 SPY–TLT correlation construction class), NF-20261107-16 IEF–TLT Treasury duration-preference / belly-vs-long-end relative-momentum timing SPY (3.75, held — adjacency to H92 SPY–TLT equity-vs-duration / H94 HYG–IEF credit; different Treasury-only pair/channel, not a wholly unrelated construction), NF-20261107-17 VVIX–VIX volatility-of-vol stress *spread* timing SPY (3.55, held — adjacency to H104 VVIX level REJECT 4/9 and VIX-complex; materially different spread construction vs level required). Data feasibility verified (yfinance): GLD/TLT/SPY 3776 aligned rows 2010-01-04→2025-01-03 (all positive); IEF/TLT feasible; ^VVIX/^VIX feasible.
- **Deferred reassessment (no silent drops):** NF-04 **blocked** (no free PIT term-structure/roll proxy). NF-05/07/08/10/11/13/15/17/20/21 **deferred** (turnover/weak mechanism/proxy/adjacency/calendar; reasons unchanged or concretely noted). NF-11r/NF-06-18 **SAME root as NF-11** (TNX–FVX slope, data feasible; not new root). NF-06-11 **infeasible** (no free PIT PC ratio). NF-20261106-03/23/24/28/30/32/33/35 **deferred** (VIX-complex/rates/credit/beta/roll/capital-flow/FXA adjacencies). NF-20261107-05 CPI drift **deferred** (macro event-calendar adjacent to H90). **Held with concrete separation:** NF-20261107-11 cross-sectional IVOL spread timing (PIT construction must separate from H93), NF-20261107-12 credit-vs-equity vol divergence (must separate from H94/H100/H125), NF-20261107-14 OVX−VIX energy-options spread (same construction class as H125/H126 — **materially different pre-registered design required**). NF-20261107-15/H127 executed/rejected — not rerun. Executed H115–H127 not rerun.
- **H127 executed (REAL):** artifact `.experiments/nf_runs/nf_20261107_15_gld_tlt_corr/summary.json`. Selected `corr_window=63, z_window=63, entry_z=1.5, exit_z=0.0, vol_target=0.10`. OOS Val+Test (16 trades, n=1260): Sharpe **0.661** (fail), PF **1.142** (fail), max DD **-17.97%** (fail), trades **16** (fail), WF stability **1.0** (pass), worst-regime yearly **-0.904** (fail), benchmark p **0.898** / IR **-0.627** (fail), perturbation **0.861** (pass) → **REJECT 2/8**. Ablations: buy-hold SPY 0.759, random-exposure 0.743 (outperforms), inverse 0.168.

## What was actually verified
- `python3 -m ruff check run_nf_20261107_15_gld_tlt_corr.py tests/test_nf_20261107_15_gld_tlt_corr.py` → **All checks passed**.
- `python3 -m ruff format --check run_nf_20261107_15_gld_tlt_corr.py tests/test_nf_20261107_15_gld_tlt_corr.py` → **clean** (after format).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_15_gld_tlt_corr.py` → **8 passed**.
- `python3 run_nf_20261107_15_gld_tlt_corr.py` → completed, artifact written, verdict **REJECT 2/8**. Data verified (3776 aligned rows, all positive).

## What remains unresolved
- **Cycle 42 discovery/H128:** per `NEXT_TASK.md`. Held/deferred candidates require concrete reassessment (no silent drops). NF-20261107-14 and VIX-complex variants require materially different pre-registered designs if selected.
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H127 REJECTED. H127: random-exposure outperformed; extremely sparse OOS trades (16) + DD/worst-regime/benchmark failures; no edge vs buy-hold. Correlation-regime construction tested with H96 (SPY–TLT, REJECT 4/9) and H127 (GLD–TLT, REJECT 2/8) — do not rerun same construction class without materially different, pre-registered mechanism/design. Cross-asset IV/corr spread/timing construction class heavily tested (H125 MOVE 4/8, H126 GVZ 2/8, H127 GLD–TLT corr 2/8); OVX−VIX (NF-20261107-14) must not reuse the same construction without a materially different design.

## One precise next task
**Execute Cycle 42 discovery and implement+run H128** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H127, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops), pre-register H128 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
