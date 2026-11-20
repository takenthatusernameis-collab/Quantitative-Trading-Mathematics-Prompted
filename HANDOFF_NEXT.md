# HANDOFF_NEXT.md — H188 net share issuance / external financing executed; H1–H188 exhausted/rejected

## Re-verification banner (2026-11-20T07:59Z, Cycle 233)

> **Provenance caution:** This session executed H188 (NF-20261120-02) on the pre-registered
> construction from HYPOTHESIS_SPEC.md §Cycle 232. The runner was written after the
> pre-registration commit and the artifact timestamp (07:59:06Z) follows the pre-registration,
> establishing temporal ordering by git history.

## What changed this session

- **H188 executed** (Cycle 233): `NF-20261120-02` net share issuance / external financing run
  on SEC XBRL `companyfacts` (free/public/PIT). Runner `run_nf_20261120_02_net_share_issuance.py`
  created, tests `tests/test_nf_20261120_02_net_share_issuance.py` added.
  Artifact: `.experiments/nf_runs/nf_20261120_02_net_share_issuance_20261120_075812/`
  (`summary.json` + `grid.csv` + `data_meta.json`).
  **Result: REJECT (3/8 gates)** — OOS Val+Test Sharpe 0.698 (< 1.0), PF 1.126 (< 1.3),
  worst-regime rolling-252 Sharpe −0.387 (< 0.3), benchmark p=0.178 (IR −0.600),
  OAT perturbation min ratio −0.668 (< 0.5). PASS: trades (14,743), maxDD (−12.43%),
  WF stability (0.880).
- **Mechanism separation from H188 vs H187 verified**: train-block Spearman |ρ| < 0.7
  for all four cross-diagnostics (max |ρ| = 0.29 vs asset_growth). Separation holds.
- **H1–H188 now all executed/rejected**. The SEC XBRL source remains free/public/PIT and
  usable — the *mechanisms* failed on this survivorship-biased large-cap construction after
  5 bps costs, not the data.
- **Documentation updated**: `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 233 added,
  `HYPOTHESIS_SPEC.md` §Cycle 233 (H188 execution result) added, `AGENTS.md` stale claim
  updated to H1–H188 exhausted.
- **Artifact schema pins updated**: `tests/test_experiment_artifact_schema.py` inventory
  bumped for the one new artifact directory (Cycle 219 precedent):
  `EXPECTED_TOTAL_DIRS = 115`, `EXPECTED_SUMMARY_COUNT = 107`, `EXPECTED_DISTINCT_KEYS = 149`.
- **Lint/format**: Clean across `src`, `tests`, `run_*.py`, `scripts` (358 files).

## Actually verified (this session, 2026-11-20)

- `python run_nf_20261120_02_net_share_issuance.py` → REJECT (3/8), artifact created, runtime 67.2 s
- `python -m pytest -q tests/test_nf_20261120_02_net_share_issuance.py` — **17 passed**
- `python -m pytest -q tests/test_experiment_artifact_schema.py` — **112 passed**
- `python -m pytest -q tests/test_nf_20261120_01_equity_accruals.py tests/test_probe_sec_xbrl_fundamentals.py tests/test_h22_futures_tsmom_voltarget.py tests/test_h28_causal_recertification.py tests/test_h29_lookahead_sweep.py tests/test_gate_vacuity_contract.py` — **146 passed**
- `python -m pytest -q tests/test_benchmark_gate_contract.py tests/test_h51_benchmark_container_invariance.py tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py tests/test_trade_log_cost_reconciliation.py` — **426 passed, 47 skipped**
- `python -m ruff check src tests run_*.py scripts` — **All checks passed**
- `python -m ruff format --check src tests run_*.py scripts` — **358 files already formatted**

## Next task

**Execute H189 (NF-20261120-03): gross profitability premium** — currently deferred for
measured data thinness (`CostOfRevenue` annual facts cover only 31/99 names, below the
40-name minimum). Before execution, a different measured cost tag must be found and the
family must be pre-registered as its own H-ID with a mechanism-separation argument
against H187/H188. It may not be run as a variant of H187/H188.

**Alternative (if H189 remains blocked)**: Conclude free-data point-in-time family
discovery is exhausted (H1–H188 all executed/rejected on SEC XBRL) and shift to
auditing/infrastructure per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6.

**Maintainer (unchanged, separate):** apply/push
`patches/0001-gates-workflow-contract-fix.patch`, then verify `CONTRACT SATISFIED` and
7 passing contract tests. The agent cannot land it (hard evidence: GitHub App token lacks
`workflows` permission).

## Approaches already tried and why they should not be repeated

- Do not re-run H187 or H188 as parameter/universe/window variants (feature set, k, entry
  threshold, formulation, or sample window); both are durably REJECTED at the family level.
- Do not re-declare PIT accounting fundamentals (SEC XBRL `companyfacts`) as blocked — the
  source is free/public/PIT with 98/100 usable accrual observations and 88/91 usable
  share-count observations; the mechanisms failed after costs, not for lack of data.
- Do not edit `.github/workflows/**` or weaken any gate or contract test.
- Do not modify the 25 unrecoverable-missing / 11 hash-mismatch backlog without authorization;
  the baseline (both identity digests and `REPRODUCIBILITY_AUDIT_REPORT.md`) must move in
  one commit.

## Constraints

`src/qtr` unchanged unless an evidenced defect requires it (then rerun pinned full gates:
`pytest -q -W error`, ruff check/format, coverage 100% for `src/qtr`); no gate weakening;
no published/certified artifact, verdict, threshold, or frozen number modified without
authorization; no commit/push unless explicitly requested.