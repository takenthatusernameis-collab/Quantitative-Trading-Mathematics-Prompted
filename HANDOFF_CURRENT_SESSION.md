# HANDOFF — Current Session (Cycle 92 complete, H178 REJECT 4/8)

## What changed
- **Lineage reconciled to H178.** H85–H178 all rejected/recorded. Next unused H-ID **H179** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.
- **Directive §4 Cycle 92 discovery completed (documented).** Reassessed deferred pool with evidence (no silent drops): NF-16/18/19/02/22/23/12/20/04/05/08-16/09-03. Proposed ≥3 candidates across ≥3 broad mechanism categories with honest 25/25/20/15/10/5 scoring: NF-20261110-03 CBOE equity P/C ratio sentiment/positioning (3.70, **selected**), NF-20261110-04 10Y-3M curve inversion depth (3.80, deferred for honest adjacency to H171/H11r curve families), NF-20261110-05 realized upside/downside jump asymmetry (3.80, deferred for adjacency to H122/H128/H135 and low plausibility/support). NF-root/ID collisions checked (NF-20261110-03 previously listed as candidate only, no executed runner/artifact).
- **H178 pre-registered and executed REAL (NF-20261110-03).** `run_nf_20261110_03_equity_pc_ratio.py` + `tests/test_nf_20261110_03_equity_pc_ratio.py` (**14 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261110_03_equity_pc_ratio_20261110_cycle92/summary.json` (+`grid.csv`, 28.8s).
- **H178 construction.** Trailing z-score of CBOE equity put/call ratio (free PIT CSV) gating vol-targeted SPY exposure; contrarian/momentum modes with hysteresis; 1-bar delay; long-only, MAX_POS 0.5; Equity CostModel defaults. Grid 108: `pc_window {20,60,120} × entry_z {0.5,1.0,1.5} × exit_z {-0.5,0.0,0.5} × vol_target {0.10,0.15} × mode {contrarian,momentum}`. Train-only 4-fold WF selection.
- **H178 data/splits.** SPY + CBOE equity P/C aligned 2010-01-04→2026-10-30 (4233 rows). Train →2018-05-31, Val →2022-08-12, Test protected →2026-10-30 (OOS Val+Test 2117 rows).
- **H178 result (OOS Val+Test).** Selected `pc_window=20, entry_z=0.5, exit_z=-0.5, vol_target=0.10, mode=momentum` (WF 0.957, train 0.847). Sharpe **0.557** fail, PF **1.407** pass, maxDD **−2.78%** pass, trades **115** pass, WF stability **0.658** fail, worst-regime **−1.002** fail, benchmark-p **0.983**/IR **−0.731** vs buy-hold SPY 0.819/+85.03% fail, perturbation **0.588** pass → **REJECT 4/8**. Ablations: random-signal **0.835** (outperformed), inverse-mode −0.156.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H178, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 92, `NEXT_TASK.md` (Cycle 93/H179), `HANDOFF_NEXT.md`, this handoff.

## Actually verified (this session)
- `python -m py_compile` runner + tests — OK.
- `python -m ruff check/format --check` on H178 runner/tests — clean.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261110_03_equity_pc_ratio.py` — **14 passed**.
- `PYTHONPATH=src python run_nf_20261110_03_equity_pc_ratio.py` — REAL execution completed (28.8s), REJECT 4/8.
- Artifact present/parsable: `.experiments/nf_runs/nf_20261110_03_equity_pc_ratio_20261110_cycle92/summary.json` (+`grid.csv`).
- `src/qtr` unchanged; pinned 100% coverage suite **not rerun**.
- `git status --short` clean before changes? session added untracked/new files and modified handoff/spec/register docs (see diff).

## Unresolved / constraints
- H85–H178 all REJECTED/recorded. Gaps H24/H68–H73/H76–H79 unassigned (not recycled). **No commit/push** (not authorized). Published/certified artifacts and thresholds unchanged.
- Cycle 93: directive §4 discovery (≥3 candidates, ≥3 categories, honest scoring, no silent drops, NF-root checks) before selecting H179. Reassess deferred pool including NF-16/18/19/02/22/23/12/20/04/05/08-16/09-03/NF-20261110-04/NF-20261110-05 with evidence.
- If `src/qtr` touched: rerun pinned 100% suite with `-W error --cov=qtr --cov-branch`.

## Approaches that failed / evidence (do not blindly repeat)
- H178 failed Sharpe/WF/worst-regime/benchmark; **random-signal ablation outperformed (0.835)** — no reliable P/C sentiment edge in this construction. Do not rerun same z-score regime without materially different mechanism/observable.
- H177 REJECT 5/8 (Sharpe 0.720, worst-regime −1.133, bench fail; synthetic auction data limitation).
- H176 REJECT 3/8 (low frequency, trades 8, WF/bench fail).
- H175 REJECT 7/8 (inverse-regime falsifier outperformed).
- H174 invalid without point-in-time NAV; H173 REJECT 7/8 (inverse-signal outperformed).

## One precise next task (Cycle 93 / H179)
Reconcile lineage to H178; complete directive §4 discovery (≥3 repo-new/decisive candidates across ≥3 broad mechanism categories, honest 25/25/20/15/10/5, concrete deferred reassessment, NF-root checks). Reassess NF-16/NF-18/NF-19/NF-02/NF-22/NF-23/NF-12 and NF-20261110-04/NF-20261110-05 (with adjacency evidence) alongside ≥1 other repo-new mechanism. Pre-register highest-expected-information feasible candidate as **H179** before validation outcomes. Implement runner + focused tests; `ruff check/format --check`; `PYTHONPATH=src pytest -q` focused tests; execute REAL; record in `HYPOTHESIS_SPEC.md` §H179, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 93, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless authorized. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
