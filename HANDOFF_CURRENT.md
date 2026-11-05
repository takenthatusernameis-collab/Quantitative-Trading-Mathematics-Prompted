# HANDOFF_CURRENT.md — H88 (NF-20261105-06, GLD/USO amended) executed → REJECTED (1/9)

## State
- Working tree has **uncommitted** changes (no commit; no user request): modified `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_CURRENT.md`, `.experiments/experiments.jsonl`, `run_nf_20261105_06_gold_oil_rv.py`, `tests/test_nf_20261105_06_gold_oil_rv.py`. `src/qtr` **not modified**.
- H1–H30 exhausted; hypotheses documented through H88. H85–H87 REJECTED. **H88 REJECTED (1/9)** under 2026-11-05 option-b GLD/USO ETF-proxy re-specification (material instrument/cost/basis change disclosed; amendment recorded before outcome evaluation). Original GC=F/CL=F attempt remained **BLOCKED** (CL=F non-positive 2020-04-21), not rejected. Next unused H-ID: **H89**.

## What changed (this session)
- Executed assigned NEXT_TASK: chose **option (b) GLD/USO ETF proxy** (feasibility clean: 4233 rows each, 0 non-positive, 2010-01-01→2026-10-31). Recorded amendment in `HYPOTHESIS_SPEC.md` §H88 and `NEW_FAMILY_RESEARCH_REGISTER.md` §11/§12 before outcome evaluation.
- Updated `run_nf_20261105_06_gold_oil_rv.py` to GLD/USO + `AssetClass.EQUITY` cost/config; updated `tests/test_nf_20261105_06_gold_oil_rv.py` (14 tests).
- Executed amended H88: exp `exp_2026-11-05T12-24-33-350043Z` (completed). Summary: `.experiments/artifacts/exp_2026-11-05T12-24-33-350043Z/summary.json`.

## What was actually verified
- **Focused checks:** `python -m ruff check src tests run_nf_20261105_06_gold_oil_rv.py tests/test_nf_20261105_06_gold_oil_rv.py` → All checks passed. `python -m ruff format --check src tests run_*.py` → 113 files already formatted. `PYTHONPATH=src python -m pytest tests/test_nf_20261105_06_gold_oil_rv.py -q` → **14 passed**.
- **Execution evidence:** `PYTHONPATH=src python run_nf_20261105_06_gold_oil_rv.py` completed. Prices (4233,2), train/val/test 2264/1008/961, grid 18 (5.0s). Selected lookback=252, entry_z=2.0, exit_z=0.75. OOS Val+Test: Sharpe −0.535, PF 0.866, max DD −34.53%, trades 1766, WF stability 0.000 (train −0.278, val −0.666, test −0.395), benchmark p=0.0872 / IR −0.417, perturbation min ratio 0.000, worst-regime −0.666. Ablations: random_entry Sharpe 0.256/PF 1.056; equal-weight GLD/USO Sharpe 0.740/PF 1.142. Spread diagnostic acf1≈0.999/ar1≈0.999. **Gates 1/9 passed (trades only) → REJECT.**
- **Holdout discipline:** protected holdout evaluated only in pre-registered OOS (Val+Test) gate set after amendment/runner execution; no holdout feedback used in re-specification or train-only selection.

## Not verified / not run
- Full pinned `src/qtr` gate suite (`-W error --cov=qtr --cov-branch`, 100%) **not re-run** because `src/qtr` was not modified.

## What remains unresolved
- NF-20261105-04 (commodity carry, roll-proxy point-in-time risk) and NF-20261105-05 (short-term CS reversal, turnover/net-of-cost risk) remain deferred; must address decisive risks before execution.
- FINAL_REPORT.md §H53–§H61 disclosed-not-quantified items remain (no gate impact).

## Approaches already tried / failed
- **H88 original GC=F/CL=F (pre-registered universe):** blocked deterministically by CL=F non-positive price -14.0 on 2020-04-21 under fail-closed `DataFetcher._reject_non_positive_prices` (exp `exp_2026-11-05T12-16-14-717827Z`). Do not rerun identical GC=F/CL=F full-window command.
- **H88 amended GLD/USO ETF proxy (option b, exp `exp_2026-11-05T12-24-33-350043Z`):** **REJECTED 1/9**. Negative OOS Sharpe/PF, large DD, WF/perturbation/benchmark failures; spread highly persistent (acf1≈0.999). Do not treat as profitable/robust; do not retune same mechanism as a “new family”.

## Precise next task (one task), with evidence and constraints
**H89 discovery/selection:** run new-family discovery per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` (H85–H88 rejected). Reassess NF-20261105-04 (roll-proxy point-in-time feasibility) and NF-20261105-05 (net-of-cost/turnover) with explicit decisive-risk evidence; add a third materially distinct mechanism if needed; pre-register top decision-ready candidate as H89 (NF temp ID, splits/protected holdout, costs, gates, null/falsifiers). Implement + focused tests + lint/format; run pinned full `src/qtr` gates if `src/qtr` touched; execute H89 only if decision-ready and record verdict/artifacts.

Constraints: preserve protected holdout; no protected-test feedback; do not modify published artifacts/thresholds/prior verdicts; keep `src/qtr` 100% stmt+branch if touched; free/public data only; never commit without explicit user request.
