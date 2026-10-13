# Next Task: H12 complete — PASS (selection bias rejected)

## H12 executed 2026-10-13 — **PASS**

Selection-bias audit of the frozen H10-selected config.
39.1 min, 0.652 CPU-h (budget ≤ 4 CPU-h). Artifacts:
`.experiments/artifacts/exp_2026-10-13T12-51-06-515939Z/`
(`summary.json`, `grid_oos_metrics.parquet` — per-combo OOS
metrics for all 13,824 configs, `cscv_rank_distribution.parquet`,
`val_sharpe_distribution.parquet`). Script:
`run_h12_selection_bias_audit.py`. Regression tests:
`tests/test_h12_selection_bias.py`.

| Pre-registered component | Result |
|---|---|
| 1. Deflated Sharpe Ratio (N=13,824) | E[max SR \| null] = 0.6214 vs observed best-of-N Val SR 1.4134 (+2.86 grid SD); **DSR-adjusted Sharpe 1.4094, p = 0.00283** |
| 2. PBO via CSCV (S=12, T=5,148, 924 combos) | **PBO = 0.0552** (< 0.3 strict, < 0.5 H0); median OOS rank of IS-optimal = 1,716/13,824 (top 12%) |
| 3. Family-wide multiple testing (N=14,389) | DSR (family) = 1.4093, p = 0.00288; benchmark p 4.79e-10 → Bonferroni/BH/Šidák ≈ **6.89e-06** (< 0.05) |
| 4. PF-margin sensitivity (diagnostic) | Selected Val PF 1.3527 (rank 9/13,824); PF ≥ 1.3 fraction: **7.26% Val vs 0.32% OOS** |

**Verdict: PASS.** The H10 certification is not a best-of-N
selection artifact. The re-run grid reproduces the H10 OOS
metrics of the selected config bit-exactly (OOS Sharpe
1.275759, PF 1.304165).

**Fix applied during H12:** the pre-written CSCV helper had an
inverted rank comparison (`pbo = mean(ranks < median_rank)`);
rank 1 is the best OOS rank, so "below the OOS median" is
`rank > median_rank`. The new regression tests caught this
(a perfectly-skilled synthetic strategy returned PBO=1.0 before
the fix). Always trust the tests over pre-written machinery.

**Caveats carried forward:**
1. CSCV's exchangeability assumption holds only approximately
   for a correlated candidate grid — the low PBO partly measures
   selection *stability within* the family, not independence
   across families.
2. The profit factor remains the fragile gate: OOS PF 1.304
   clears 1.3 by only +0.004; only 0.32% of configs clear
   PF ≥ 1.3 OOS.
3. Free yfinance hourly `=F` data is hard-capped at ~730 days
   (no bars beyond 2026-10-09); the sample is a single ~2-year
   hourly window. Both require a paid data source to lift.

**Note on repo state:** all H12 changes (script, tests, docs)
are in the working tree, **uncommitted** (commit policy: only
commit when explicitly asked). Intended commit, if desired:
`run_h12_selection_bias_audit.py`, `tests/test_h12_selection_bias.py`,
`HYPOTHESIS_SPEC.md`, `INEFFICIENCY_RANKING.md`, `FINAL_REPORT.md`,
`NEXT_TASK.md`, plus the H11 public-API refactor of
`run_h11_robustness_experiment.py` (fixes the 13 failing
regression tests: `FROZEN_CONFIG`, `PERTURBATIONS` ±20% pairs,
`JOINT_PERTURBATIONS`, `build_positions`, `make_cost_stressed_config`,
`per_symbol_contributions`, `bootstrap_sharpe_distribution`,
`probe_live_extension`, `MAX_POSITION_SIZE`) and the H12
experiment artifacts under `.experiments/`. Do not stage
`__pycache__/*.pyc` (ignored, but force-added in commit
8015413 — they show as modified; leave them).

---

## Next Task (for next agent): H13 — OOS-Level Deflation & PF-Margin Fragility Audit

H12 deflated the *Val* (selection-metric) Sharpe. Two bounded,
artifact-reuse-only follow-ups remain (no new backtests, ≤ 0.1 CPU-h):

1. **OOS worst-case deflation.** Using the H12 artifact
   `grid_oos_metrics.parquet` (per-combo OOS Sharpe for all
   13,824 configs — the H12 grid re-run), compute the DSR of
   the selected config's **OOS** Sharpe (1.275759) under the
   *worst-case* assumption that OOS had been the selection
   metric with N=13,824 trials (moments: OOS-Sharpe
   distribution mean/SD from the same artifact; OOS-return
   skew/kurtosis from the H10 artifact `returns.parquet` on
   the OOS mask). This is a conservative "peeking" bound: the
   config was actually selected on Val, so the true OOS
   deflation is weaker (N≈1 for a single OOS evaluation).
   Report both the worst-case (N=13,824) and the single-peek
   (N=1) DSR.
2. **PF-margin fragility decomposition.** Using the H10 artifact
   (`returns.parquet`, `trades.parquet`, `positions.parquet`,
   `prices.parquet`) and the H11 per-symbol machinery
   (`run_h11_robustness_experiment.per_symbol_contributions`):
   (a) net per-symbol OOS profit factors (decompose the pooled
   PF 1.304 into the 5 symbols' contributions); (b) bootstrap
   95% CI of the OOS PF (2,000 resamples of OOS returns, seeded);
   (c) PF under the H11 shifted splits (already computed:
   1.281–1.292 — confirm and attribute which symbol/regime
   drives the shortfall); (d) the cost multiplier at which the
   *selected* config's OOS PF crosses 1.3 (H11 found the
   break-even at 1.542× — verify against the H12 re-run).

**Pre-registration for H13** (write before execution):
- Null (H0): the OOS Sharpe does not survive the worst-case
  OOS-level deflation (DSR-adjusted OOS Sharpe < 1.0), or the
  OOS PF bootstrap CI lower bound < 1.3, or no single symbol
  is dispensable (each symbol's removal keeps PF ≥ 1.3 — i.e.
  the margin is robust).
- Deliverables: `run_h13_oos_deflation_pf_audit.py`, artifacts
  in `.experiments/artifacts/exp_<H13>/`, updated
  `HYPOTHESIS_SPEC.md` and `INEFFICIENCY_RANKING.md`, final
  PASS/REJECT verdict with root-cause attribution.
- Reuse `run_h12_selection_bias_audit.deflated_sharpe_ratio`,
  `_expected_max_sharpe`, `_load_cached_data`, `_splits`,
  `_period_metrics`, `_count_in` and the H11 public API — no
  new engine code.

**Constraints (unchanged):** no live trading, no secrets, no paid
data, Test never enters selection, preserve negative results,
≤ 4 CPU-h per experiment, reuse existing engine / tracking /
validation infrastructure, all regression tests passing (78/78
at the time of this writing).

**Documented-but-infeasible items (do not re-attempt without a
new data source):** longer intraday history and ongoing OOS
time-extension — a live (uncached) yfinance fetch verified on
2026-10-11 returns no hourly `=F` bars beyond 2026-10-09.
Both require a paid data source.
