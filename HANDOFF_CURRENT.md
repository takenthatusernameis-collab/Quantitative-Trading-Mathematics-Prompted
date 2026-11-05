# HANDOFF_CURRENT.md — H89 (NF-20261105-07, CBOE SKEW tail-risk timing) executed → REJECTED (4/9)

## State
- Working tree has **uncommitted** changes (no commit; no user request): `HYPOTHESIS_SPEC.md` (H89 pre-reg + result), `NEW_FAMILY_RESEARCH_REGISTER.md` (§13 cycle 4 selection + §14 H89 outcome), `NEXT_TASK.md`, `HANDOFF_CURRENT.md`, `run_nf_20261105_07_skew_tail_timing.py`, `tests/test_nf_20261105_07_skew_tail_timing.py`, `.experiments/experiments.jsonl`, and `.experiments/*`/artifact files for `exp_2026-11-05T12-36-06-158635Z`. `src/qtr` **not modified**.
- H1–H30 exhausted; hypotheses documented through **H89**. H85–H88 REJECTED; **H89 REJECTED (4/9)**. Next unused H-ID: **H90**.

## What changed (this session)
- Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` / `NEXT_TASK.md`: reassessed deferred NF-20261105-04/NF-20261105-05 with decisive-risk evidence (NF-04: no free point-in-time deferred/term-structure/roll proxy in current `DataFetcher` pipeline; CL=F continuous has non-positive history; ETF proxies confounded — **deferred**. NF-05: daily CS reversal feasible on sector ETFs but turnover/net-of-cost decisive risk unresolved under pre-registered costs — **deferred**). Proposed third candidate **NF-20261105-07** (CBOE SKEW tail-risk regime, volatility/convexity premia / implied tail dimension), ranked above deferred candidates as highest expected-information feasible free-data test.
- Pre-registered **H89/NF-20261105-07** in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md` §13. Implemented `run_nf_20261105_07_skew_tail_timing.py` + `tests/test_nf_20261105_07_skew_tail_timing.py` (long/flat SPY timed by trailing `^SKEW` z-score, causal 1-bar delay, vol-targeted). Executed H89.

## What was actually verified
- **Focused checks:** `python -m ruff check run_nf_20261105_07_skew_tail_timing.py tests/test_nf_20261105_07_skew_tail_timing.py` → All checks passed. Global `python -m ruff check src tests run_*.py` → All checks passed. `python -m ruff format --check src tests run_*.py` → **115 files already formatted**. `PYTHONPATH=src python -m pytest tests/test_nf_20261105_07_skew_tail_timing.py -q` → **10 passed**.
- **Data feasibility (2026-11-05):** `^SKEW` 2918 rows, 0 non-positive; SPY 2975; aligned 2918 (2015-01-02→2026-10-30). Commodity direct checks: CL=F continuous has 1 non-positive in 2012–2026 spot check (evidence for NF-04 caution); no point-in-time deferred series in current pipeline.
- **Execution evidence (H89, exp `exp_2026-11-05T12-36-06-158635Z`, completed):** prices (2918,2), train/val/test 1241/743/934, grid 48 (5.1s). Selected (train-only WF): lookback=63, entry_z=0.5, exit_z=-0.5, vol_target=0.10. OOS Val+Test (1677 periods, 368 trades): Sharpe **0.524**, PF **1.140**, max DD **−8.53%**, WF stability **1.800** (train 0.427, val 0.309, test 0.768), worst-regime rolling-252 Sharpe **−0.623**, benchmark p=**1.000** / IR **−0.634** vs buy-hold SPY (Sharpe 0.735), perturbation min ratio **0.746**. Ablations: random-state Sharpe −0.371/PF 0.913; inverse-threshold ablation produced 0 OOS trades under long/flat construction (recorded). Gates **4/9 passed** (trades, max DD, WF stability, perturbation) → **REJECT**. Artifact: `.experiments/artifacts/exp_2026-11-05T12-36-06-158635Z/summary.json`.
- **Holdout discipline:** protected holdout evaluated only in pre-registered OOS (Val+Test) gate set after selection; no holdout feedback in discovery/selection/implementation.

## Not verified / not run
- Full pinned `src/qtr` gate suite (`PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`, 100%) **not re-run** because `src/qtr` was not modified.

## What remains unresolved
- NF-20261105-04 (commodity carry) deferred: decisive risk unresolved (point-in-time term-structure/roll proxy not available/evidenced in current free pipeline).
- NF-20261105-05 (short-term CS reversal) deferred: decisive risk unresolved (turnover/net-of-cost realism under pre-registered daily rebalance).
- FINAL_REPORT.md §H53–§H61 disclosed-not-quantified items remain (no gate impact).

## Approaches already tried / failed
- **H89 / NF-20261105-07 (exp `exp_2026-11-05T12-36-06-158635Z`): REJECTED 4/9.** SKEW risk-off gating reduced DD but underperformed buy-hold SPY on OOS Sharpe/PF/benchmark/IR/worst-regime. Do not retune same mechanism as a “new family”.
- Prior rejected cycle families: H85 (lead-lag), H86 (VIX slope timing), H87 (opening-gap fill), H88 (gold–oil RV, GLD/USO amended after CL=F non-positive blocker). See register/spec.

## Precise next task (one task), with evidence and constraints
**H90 discovery/selection + decision-ready pre-registration:** run new-family discovery per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` (H85–H89 rejected). Propose/rank at least **three** materially distinct mechanism candidates spanning mechanism categories not exhausted by simple reuse: (a) only reconsider NF-04/NF-05 if you pre-register and evidence resolution of their decisive risks (point-in-time roll proxy for NF-04; explicit turnover/net-of-cost design for NF-05) — otherwise keep deferred; (b) add a new free-data candidate, e.g. **pre-scheduled FOMC/Fed announcement calendar event drift** (event/auction mechanism; ex-ante dates point-in-time; smallest decisive test: SPY/TLT return around pre-specified windows, net of costs) or another clearly distinct category; verify novelty vs H18 (overnight/intraday persistence, not scheduled macro-event announcement windows) and vs all prior H-IDs. Pre-register top candidate as **H90** with NF temp ID, observables, splits/protected holdout, costs, gates, null/rejection, falsifiers, closest-prior distinction. Implement runner + focused tests + lint/format; run pinned full `src/qtr` gates only if `src/qtr` touched. Execute H90 only if decision-ready; record verdict/artifacts/handoff.

Constraints: preserve protected holdout; no protected-test feedback; do not modify published artifacts/thresholds/prior verdicts; keep `src/qtr` 100% stmt+branch if touched; free/public data only; never commit without explicit user request.
