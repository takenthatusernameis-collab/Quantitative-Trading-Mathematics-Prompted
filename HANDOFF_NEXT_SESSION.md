# HANDOFF_NEXT_SESSION.md — Cycle 51 complete (H137 REJECT); prepare Cycle 52 discovery/H138

## State
- **H85–H137 all REJECTED/recorded.** H137 (NF-20261107-50, SPY timing from realized SPY--GLD return-correlation regime / safe-haven co-movement-diversification transmission) executed REAL: `.experiments/nf_runs/nf_20261107_50_spy_gld_corr/summary.json` (1.75s), verdict **REJECT 2/8**. **Next unused H-ID: H138** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Files (H137):** `run_nf_20261107_50_spy_gld_corr.py`, `tests/test_nf_20261107_50_spy_gld_corr.py` (7 passed), artifact `.experiments/nf_runs/nf_20261107_50_spy_gld_corr/` (`summary.json`, `grid.csv`, `data_meta.json`). Docs updated: `HYPOTHESIS_SPEC.md` §H137, `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 51 discovery/scoring/deferred reassessment + H137 outcome), `NEXT_TASK.md` (Cycle 52), `HANDOFF_NEXT.md`, this file. `src/qtr` unchanged. No published/certified artifact/verdict/threshold/frozen number modified except adding H137 records. No secrets/credentials added. No commit/push performed.
- **Unrelated tracked file present in HEAD/worktree context:** `run_nf_20261107_48_ovx_vix_spread.py` exists as a tracked mislabeled draft (AR(1) body under OVX/H137 name from prior commit `bc4162a`); **not modified/executed by Cycle 51** and not part of H137's validated record. Next session should not treat it as H137 evidence.

## What changed (Cycle 51)
- **Directive §4 discovery:** lineage reconciled to H136. >=3 repo-new mechanism candidates across >=3 broad categories scored honestly (25/25/20/15/10/5): NF-20261107-50 SPY--GLD realized return-correlation regime (safe-haven co-movement/diversification transmission) **3.95, selected/executed H137** (repo-new SPY--GLD pair/channel; honest adjacency to H96/H127/H134 correlation-regime construction class); NF-20261107-49 TLT-SPY realized correlation (rates-equity co-movement/flight-to-quality) **3.60, held** (adj H127/H96 separation); NF-20261107-51 credit-vs-equity *realized-vol divergence* `RV(HYG-LQD)` vs `RV(SPY)` (credit stress/volatility transmission, reassessing NF-20261107-12 with distinct design) **3.50, held** (explicit pre-registration of vol-divergence observable/construction separation required; sep H94/H100/H125); NF-20261107-14/48 OVX−VIX **3.35, held/not selected** — same construction class as H125/H126, **materially different pre-registered design required**.
- **H137 result (REAL, NF-20261107-50):** SPY+GLD 3776 aligned rows 2010-01-04→2025-01-03 (train 2516/val 505/test 755). Selected `corr_window=252, z_window=126, entry_scale=2, vol_target=0.10` (train WF mean 0.685). OOS Val+Test (1437 trades): Sharpe **0.152** (fail), PF **1.035** (fail), maxDD **-14.41%** (pass), trades **1437** (pass), WF stability **0.161** (fail), worst-regime rolling-252 **-0.931** (fail), benchmark p **0.977**/IR **-0.895** (fail), perturbation **0.243** (fail) → **REJECT 2/8**. Ablations: buy-hold 0.759, random-exposure-matched 0.174 (comparable), **inverse 0.943** (materially outperforms — pre-registered falsifier indicates the de-risking-on-elevated-SPY/GLD-correlation mapping is wrong for this construction/sample; not a validated edge under the pre-registered hypothesis).

## What was actually verified
- `python3 -m ruff check run_nf_20261107_50_spy_gld_corr.py tests/test_nf_20261107_50_spy_gld_corr.py` → **All checks passed**.
- `python3 -m ruff format --check run_nf_20261107_50_spy_gld_corr.py tests/test_nf_20261107_50_spy_gld_corr.py` → **2 files already formatted**.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_50_spy_gld_corr.py` → **7 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_50_spy_gld_corr.py` → **REJECT 2/8**; artifact `.experiments/nf_runs/nf_20261107_50_spy_gld_corr/summary.json`.
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 52 discovery/H138 (NEXT_TASK):** Fresh directive §4 cycle: >=3 repo-new candidates across >=3 broad categories, honest 25/25/20/15/10/5 scoring, concrete deferred reassessment (no silent drops). Deferred highlights: NF-04 **blocked**; NF-06-11 **infeasible**; NF-11r/NF-06-18 **SAME root as NF-11**; NF-05/07/08/10/11/13/15/17/20/21/NF-20261106-03/23/24/28/30/32/33/35/NF-20261107-05 deferred. Held: NF-20261107-11/12(51)/14(48)/31/49 with separation/design requirements.
- H85–H137 all rejected; correlation-regime construction class heavily tested across pairs (H96 SPY-TLT, H127 GLD-TLT, H134 SPY-VIX, H137 SPY-GLD) — require clearly distinct mechanism/design if revisited. Do not reframe H137 inverse as a new pass without full pre-registration and gates.
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H137 all REJECTED. H137: fails 6/8 gates (Sharpe 0.152, PF 1.035, WF 0.161, worst-regime -0.931, benchmark p 0.977/IR -0.895, perturbation 0.243); random-exposure comparable; inverse mapping outperforms (pre-registered falsifier) — do not rerun same de-risking construction.
- NF-20261107-32/36/39/43/46/47/50 are duplicates of executed H118/H133/H134/H135/H136/H137 — do not re-execute as "new" without a materially distinct observable/design.
- NF-20261107-14/48 OVX−VIX: same cross-asset IV-spread construction class as H125/H126 — **materially different pre-registered design required** (not reframing).

## Precise next task (one task)
**Execute Cycle 52 discovery and implement+run H138** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H137, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H138 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
