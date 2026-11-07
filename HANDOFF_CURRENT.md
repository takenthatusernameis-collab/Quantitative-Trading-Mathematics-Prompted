# HANDOFF_CURRENT — Cycle 40 complete (H126 REJECT 2/8); prepare Cycle 41 discovery/H127

## State
- H85–H126 all rejected/recorded. H126 (NF-20261107-13, cross-asset gold-vs-equity implied-vol spread timing SPY, `GVZ−VIX`) executed **REJECT 2/8**. Next unused H-ID **H127**.
- New/uncommitted: `run_nf_20261107_13_gvz_vix_spread.py`, `tests/test_nf_20261107_13_gvz_vix_spread.py` (11 passed), artifact `.experiments/nf_runs/nf_20261107_13_gvz_vix_spread/summary.json` (+ `grid.csv`, `data_meta.json`). Docs updated: `HYPOTHESIS_SPEC.md` (H126 pre-reg+outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 40 discovery/scoring/deferred reassessment + H126 outcome), `NEXT_TASK.md`, `HANDOFF_NEXT.md`.
- `src/qtr` unchanged. No secrets. No published/certified artifact/gate threshold/verdict modified except adding H126 records.

## What changed
- **Cycle 40 discovery (directive §4):** >=3 repo-new candidates across >=3 categories with honest 25/25/20/15/10/5: NF-20261107-13 GVZ−VIX gold-vs-equity IV spread (3.90, selected/executed H126), NF-20261107-14 OVX−VIX energy-vs-equity IV spread (3.85, held — same construction class), NF-20261107-15 GLD–TLT correlation regime (3.85, held — adjacent to H96, different pair). Data feasibility verified via yfinance: ^GVZ/^VIX/SPY 3776 aligned rows 2010-01-04→2025-01-03 (0 non-positive); ^OVX feasible (same range); GLD/TLT feasible.
- **Deferred reassessment (no silent drops):** NF-04 blocked; NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 **SAME root as NF-11** (not new root, ^TNX/^FVX feasible); NF-06-11 infeasible; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05 CPI drift deferred; held NF-20261107-11/12/14/15 with concrete separation/evidence notes. NF-20261107-13 executed — not rerun. Executed H115–H126 not rerun.
- **H126 executed (REAL):** OOS Val+Test 66 trades: Sharpe 0.537, PF 1.120, max DD -15.99%, trades 66, WF stability 1.0, worst-regime yearly -0.853 (2022 context in gate calc), benchmark p 0.973 / IR -0.864, perturbation 0.904. Gates 2/8 PASS (WF stability, perturbation). **REJECT**. Ablations: buy-hold 0.759, random-exposure 0.749 (outperforms), inverse 0.386.

## What was actually verified
- `python3 -m ruff check run_nf_20261107_13_gvz_vix_spread.py tests/test_nf_20261107_13_gvz_vix_spread.py` → **All checks passed**.
- `python3 -m ruff format --check ...` → **clean**.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_13_gvz_vix_spread.py` → **11 passed**.
- `python3 run_nf_20261107_13_gvz_vix_spread.py` → completed, artifact written, verdict REJECT 2/8. yfinance data verified (3776 aligned rows).

## What remains unresolved
- **Cycle 41 discovery/H127:** per `NEXT_TASK.md`. Held candidates NF-20261107-11/12/14/15 and all deferred list require concrete reassessment (no silent drops). NF-20261107-14/15 are feasible but adjacent construction classes — require materially different pre-registered designs if selected.
- Baseline full-suite `src/qtr` gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H126 REJECTED. H126: random-exposure outperformed; sparse OOS trades (66) + maxDD breach; no edge vs buy-hold. Cross-asset IV spread construction class now tested with MOVE (H125, 4/8) and GVZ (H126, 2/8) — do not rerun OVX−VIX (NF-20261107-14) with same construction without a materially different, pre-registered design.

## One precise next task
**Execute Cycle 41 discovery and implement+run H127** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H126, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred/held reassessment (no silent drops), pre-register H127 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
