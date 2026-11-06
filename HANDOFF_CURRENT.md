# HANDOFF_CURRENT.md — H99/NF-20261106-01 executed (REJECT 4/9); Cycle 13 required

## What changed
- No new implementation in this session. Inspected and verified the existing H99/NF-20261106-01 state (already implemented/registered/executed in working state from prior session context, but repository diffs at session start were clean except as noted below).
- Applied `ruff format` to the full `src tests run_*.py` scope to restore clean formatting (2 files reformatted: `tests/test_h53_published_metrics_disclosure.py`, `tests/test_h55_nested_metrics_disclosure.py`). No logic/behavior changes; formatting only.
- Updated `NEXT_TASK.md` to reflect H99 completion and specify the next bounded task (Cycle 13 discovery → H100). Updated this handoff.

## What was actually verified
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261106_01_miner_gold_rv.py` → **10 passed** (1.45s).
- `python3 -m ruff check run_nf_20261106_01_miner_gold_rv.py tests/test_nf_20261106_01_miner_gold_rv.py tests/test_nf_20261105_19_pead.py` → All checks passed.
- `python3 -m ruff check src tests run_*.py` → All checks passed.
- `python3 -m ruff format --check src tests run_*.py` → 135 files already formatted (after formatting fix).
- H99 artifact present: `.experiments/nf_runs/nf_20261106_01_miner_gold_rv/summary.json` exists. HYPOTHESIS_SPEC.md contains §H99 pre-registration + execution (exp `exp_2026-11-06T03-04-40-778747Z`, REJECT 4/9). NEW_FAMILY_RESEARCH_REGISTER.md contains Cycle 12 section + H99 lineage row (REJECT 4/9). NEXT_TASK stale before this session; corrected now.
- `src/qtr` unchanged. Pinned 100% `src/qtr` coverage / `-W error` suite **not re-run** (no `src/qtr` change; evidence: `git diff --name-only` showed no `src/qtr` files). Run if `src/qtr` changes.
- Pre-existing known issue (not introduced/fixed): `test_no_runner_compares_a_p_value_against_max_p_value_directly` fails at HEAD semantics/history per NEXT_TASK/commits; 11 NF runners compare `bench_p <= GATES["max_p_value"]` directly. Do not “fix” by re-routing without understanding published gate semantics (helper adds IR>0) and without explicit authorization to change gate behavior/published results.

## What remains unresolved
- **Cycle 13 required** (STRATEGY_FAMILY_EXPANSION_DIRECTIVE §4/§6): H85–H99 all rejected. No pre-registered NF candidates remain executable without resolving a documented decisive risk. Next unused H-ID is **H100** (H24/H68–H73/H76–H79 unassigned, not recycled).
- Deferred candidates still need concrete reassessment in Cycle 13 (do not silently drop): NF-20261105-04 (commodity carry, point-in-time term-structure/roll proxy unavailable; CL=F non-positive history risk), NF-20261105-05 (short-term CS reversal, decisive daily turnover/net-of-cost risk), NF-20261105-11 (Treasury term-spread, `^IRX`/FRED point-in-time gap), NF-20261105-12 (cross-sectional equity dispersion, complexity/turnover vs smallest decisive test), NF-20261105-17 (cross-sectional volume-shock reversal, turnover/cost-sensitive), NF-20261105-20 (Treasury auction supply-pressure, event calendar/timestamp construction), NF-20261105-21 (month-end pension rebalancing, weak evidence/adjacency risk).
- Working tree contains cosmetic formatting changes to `tests/test_h53_published_metrics_disclosure.py` and `tests/test_h55_nested_metrics_disclosure.py` (not committed; no explicit commit request).

## Failed/blocked approaches (evidence)
- **H99 mechanism (executed, REJECT 4/9, `exp_2026-11-06T03-04-40-778747Z`):** OOS Val+Test Sharpe 0.329 (<1.0), PF 1.065 (<1.3), max DD -12.47% (pass), trades 1286 (pass), WF stability 1.000 (pass), worst-regime rolling-252 Sharpe -1.046 (<0.3), bench p=0.123 (>0.05 vs buy-hold GDX), IR -0.592 (<0), perturbation min ratio 0.937 (pass). Random-exposure-matched ablation Sharpe 0.763/PF 1.173 **outperformed** strategy — falsifies timing mechanism. Inverse-signal 0.243/1.047. GDX buy-hold OOS Sharpe 0.578/PF 1.107/DD -49.79%. Root cause: log(GDX/GLD) spread near-unit-root (shared gold factor); z-score triggers rarely; most performance incidental vol-scaled exposure. Do not re-run NF-01/H99 without a materially different, pre-registered mechanism.
- **Prior fabricated H99 marker (historical, already corrected per register):** commit `e00c722` copied H92 artifact as H99; fabricated artifact/experiments.jsonl entry removed; genuine H99 execution supersedes. Never cite `e00c722` numbers for H99.
- No new failures introduced this session.

## One precise next task
Perform **Cycle 13 discovery → pre-register H100** (and only implement if decision-ready and feasible in-session without weakening gates):
1. Reconcile lineage to H99 (H85–H99 all rejected). Propose ≥3 **repo-new** mechanism candidates spanning ≥3 broad mechanism categories, checked against all root families H1–H99 (do not recycle parameter/instrument/universe/timeframe variants or audits). Explicitly reassess NF-04/05/11/12/17/20/21 with concrete evidence (data availability, point-in-time feasibility, turnover/net-of-cost, decisive blocker) — do not silently drop.
2. Score each 1–5 using directive weights (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%) with honest notes (especially adjacency to H88/H92/H94/H96/H97/H99 RV/regime families).
3. Pre-register the highest-expected-information **feasible** candidate as **H100** in `HYPOTHESIS_SPEC.md` (assign H-ID only upon formal registration) and record all candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 13. Keep the NF-ID as family-level lineage key. Specify the smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, and ablations.
4. If the selected design is decision-ready and uses free/public yfinance data with no `src/qtr` change: implement `run_nf_*_*.py` + focused tests, run `ruff check/format --check` on touched files, run focused pytest, then execute the experiment and record verdict (OOS Val+Test only for selection/gates as pre-registered). **Do not** weaken gates, modify published/certified artifacts, use holdout for selection, or change `src/qtr` unless a genuine defect is evidenced (and then run pinned 100% coverage suite).
5. If no feasible candidate: document blockers/evidence and leave a precise handoff; do not invent candidates or default to maintenance-only parameter work.
