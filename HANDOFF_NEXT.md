# HANDOFF_NEXT.md — H188 net share issuance / external financing executed; H1–H188 exhausted/rejected

## Re-verification banner (2026-11-20T07:59Z, Cycle 233)

> **Provenance caution:** This session executed H188 (NF-20261120-02) on the pre-registered
> construction from HYPOTHESIS_SPEC.md §Cycle 232. The runner was written after the
> pre-registration commit and the artifact timestamp (07:59:06Z) follows the pre-registration,
> establishing temporal ordering by git history.

## What changed this session

- **H189 confirmed data-blocked** (Cycle 234): gross profitability requires revenue AND cost
  on the same 10-K fiscal-year end. Offline probe of all 100 S&P 100 names from the cached
  `.cache/xbrl` companyfacts bundles (reusing `scripts/probe_sec_xbrl_fundamentals`
  helpers): `CostOfRevenue` co-reported with `Revenues` on the same 10-K end = 28/100 names
  (>=2 periods: 28/100); `CostOfGoodsSold` co-reported with `Revenues` = 29/100 (>=2
  periods: 29/100). Both below the 40-name minimum, so no executable gross-profitability
  test exists on SEC XBRL at the required universe size. `NEW_FAMILY_RESEARCH_REGISTER.md`
  Cycle 234 added; `AGENTS.md` H189 bullet updated to "confirmed data-blocked" with evidence.
- **H1–H188 all executed/rejected** (Cycle 233 complete). SEC XBRL fundamental source tested
  across its three accounting mechanisms: H187 REJECT 2/8 (Cycle 231), H188 REJECT 3/8
  (Cycle 233), H189 data-blocked (Cycle 234).
- **Documentation updated**: `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 234 added,
  `HYPOTHESIS_SPEC.md` §Cycle 234 (H189 data-blocked record) referenced from the register,
  `AGENTS.md` H189 bullet corroborated with measured evidence.

## Actually verified (this session, 2026-11-20)

- `python run_nf_20261120_02_net_share_issuance.py` → REJECT (3/8), artifact created, runtime 67.2 s
- `python -m pytest -q tests/test_nf_20261120_02_net_share_issuance.py` — **17 passed**
- `python -m pytest -q tests/test_experiment_artifact_schema.py` — **112 passed**
- `python -m pytest -q tests/test_nf_20261120_01_equity_accruals.py tests/test_probe_sec_xbrl_fundamentals.py tests/test_h22_futures_tsmom_voltarget.py tests/test_h28_causal_recertification.py tests/test_h29_lookahead_sweep.py tests/test_gate_vacuity_contract.py` — **146 passed**
- `python -m pytest -q tests/test_benchmark_gate_contract.py tests/test_h51_benchmark_container_invariance.py tests/test_h53_published_metrics_disclosure.py tests/test_h55_nested_metrics_disclosure.py tests/test_trade_log_cost_reconciliation.py` — **426 passed, 47 skipped**
- `python -m ruff check src tests run_*.py scripts` — **All checks passed**
- `python -m ruff format --check src tests run_*.py scripts` — **358 files already formatted**

## Next task

H189 (NF-20261120-03, gross profitability) is **confirmed data-blocked** (Cycle 234): revenue
AND cost on the same 10-K end cover only 28/100 names via `CostOfRevenue` and 29/100 via
`CostOfGoodsSold`, below the 40-name minimum; both cost tags probed on this source. **Do not
execute H189** (prerequisite ≥40 active names known missing) and do not run it as a variant of
H187/H188.

Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6, the next research task is to discover and
assess a new strategy family from a **materially different source or mechanism category**
(directive §4.1: at least three candidates spanning at least three broad categories — e.g.
information transmission/lead-lag, relative value/convergence, carry/term structure,
volatility/convexity premia, liquidity provision/order-flow, event/auction, supply/flow
constraints). The free PIT fundamental source (SEC XBRL `companyfacts`) is tapped out
(H187 REJECT, H188 REJECT, H189 data-blocked); price-based families (H1–H30, H184–H188) are
already exhausted per the register. If no materially different candidate is testable on a
free/public source, conclude per directive §6 §6 and shift to auditing/infrastructure work,
leaving a precise handoff with the deferred families and the reason each was blocked.

Do **not** declare the global queue exhausted on the basis of this session alone; directive
§6 requires searching one materially different set of sources/mechanism categories first.

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
- Do not re-probe H189 cost tags: `CostOfRevenue` (28/100) and `CostOfGoodsSold` (29/100)
  names report revenue AND cost on the same 10-K end, both below the 40-name minimum;
  H189 is data-blocked on this source, not executable.
- Do not edit `.github/workflows/**` or weaken any gate or contract test.
- Do not modify the 25 unrecoverable-missing / 11 hash-mismatch backlog without authorization;
  the baseline (both identity digests and `REPRODUCIBILITY_AUDIT_REPORT.md`) must move in
  one commit.

## Constraints

`src/qtr` unchanged unless an evidenced defect requires it (then rerun pinned full gates:
`pytest -q -W error`, ruff check/format, coverage 100% for `src/qtr`); no gate weakening;
no published/certified artifact, verdict, threshold, or frozen number modified without
authorization; no commit/push unless explicitly requested.