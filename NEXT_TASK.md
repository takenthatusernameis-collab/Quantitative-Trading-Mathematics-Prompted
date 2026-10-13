# Next Task: H13 complete — REJECT on the fragility axes (PF margin is fragile)

## H13 executed 2026-10-13 — **REJECT** (2 of 3 fragility nulls not rejected)

OOS-level deflation & PF-margin fragility audit of the
frozen H10-selected config (< 0.1 CPU-h,
artifact-reuse-only). Artifacts:
`.experiments/artifacts/exp_2026-10-13T14-35-58-316759Z/`
(`summary.json`, `per_symbol_net_oos.parquet`,
`pf_bootstrap.parquet`, `shifted_splits*.parquet`,
`cost_sensitivity.parquet`). Script:
`run_h13_oos_deflation_pf_audit.py`. Regression tests:
`tests/test_h13_oos_deflation_pf.py` (105/105 passing).

| Pre-registered component | Result | Gate |
|---|---|---|
| 1. OOS worst-case deflation (N=13,824) | E[max SR \| null] = 0.6095 vs OOS SR 1.2758; **DSR-adj OOS Sharpe 1.2745, p = 0.00102**; single-peek (N=1) DSR 1.2758, p < 1e-06 | **PASS** (≥ 1.0) |
| 2. OOS PF bootstrap 95% CI (2,000 resamples, seed 42) | CI **[1.1900, 1.4248]**, median 1.3022, **P(PF ≥ 1.3) = 51.7%** | **FAIL** (LB < 1.3) |
| 3. Symbol dispensability (leave-one-out pooled OOS PF) | ES 1.3070 ✓, NQ 1.3006 ✓, **CL 1.2494 ✗**, **GC 1.2821 ✗**, ZB 1.3114 ✓ | **FAIL** (CL=F, GC=F indispensable) |
| 2c. Shifted splits (confirm + attribution) | 50/25/25 → 1.2806, 60/20/20 → 1.3298, 45/30/25 → 1.2916 — all reproduce H11 E4a bit-exactly (\|Δ\|=0); shortfall driven by **CL=F** (net-PF delta −0.076/−0.084) and the **bull regime** | diagnostic |
| 2d. Cost break-even | **1.5420×** (H11 interpolated 1.5418×, \|Δ\|=0.0002); cost ×2 moves PF only −0.008 | diagnostic |

**Verdict: REJECT** (pre-registered: PASS iff all three
gates hold). Root cause: the H10 certification's binding
constraint — the OOS PF margin (+0.004) — is (a) within
bootstrap sampling noise (CI half-width ±0.117) and
(b) carried by the two highest-PF symbols: CL=F (net PF
1.358, the only symbol above the pooled 1.304; removal
drops pooled PF to 1.249) and GC=F (removal drops it to
1.282 — its below-pooled net PF masks its role offsetting
other symbols' loss bars, so pooled PF is non-monotone in
per-symbol PF). The Sharpe edge is deflation-robust; the
PF gate is not. Costs are not the driver (break-even
1.542×).

**Repo state:** all H13 changes (script, tests, docs) are
in the working tree, **uncommitted** (commit policy: only
commit when explicitly asked). Intended commit, if
desired: `run_h13_oos_deflation_pf_audit.py`,
`tests/test_h13_oos_deflation_pf.py`, `HYPOTHESIS_SPEC.md`,
`INEFFICIENCY_RANKING.md`, `FINAL_REPORT.md`,
`NEXT_TASK.md`, plus the H13 artifacts under
`.experiments/`. Do not stage `__pycache__/*.pyc`
(ignored, but force-added in commit 8015413 — they show
as modified; leave them). H12 and H11-refactor changes
from the prior session are likewise still uncommitted.

---

## H14 completed 2026-10-13 — REJECT (family property)

H14 executed per pre-registration. Top K=50 configs by Val PF margin
(`val_profit_factor - 1.3`), excluding the frozen H10 config, were evaluated
on OOS using H13 fragility gates (artifact reuse). Artifacts:
`.experiments/artifacts/exp_2026-10-13T19-01-59-371405Z/`
(`summary.json`, `h14_results.parquet`, `topk_selected.parquet`,
`subset_oos_metrics.parquet`). Script: `run_h14_pf_margin_selection_audit.py`.

| Gate (per config) | Result across top-K=50 | Pass criterion |
|---|---|---|
| OOS PF bootstrap 95% CI lower bound | mean 1.186, max 1.199 (all < 1.3) | CI LB ≥ 1.3 |
| Worst-case DSR-adj OOS Sharpe (N=K) | mean 1.244 (all ≥ 1.0) | ≥ 1.0 at N=K |
| All symbols dispensable (LOO PF ≥ 1.3) | 0/50 | all dispensable |

**Verdict: REJECT.** No config passed all three gates. The H0 ("no config in
top-K-by-Val-PF-margin set passes all three gates") is **not rejected**. Sharpe
deflation is not the issue; symbol dispensability remains the blocker (CL=F and
GC=F dependencies persist). **Conclusion: PF-margin fragility is a family property**
on this ~2-year hourly window. The H10 line closes with this durable negative
result. Remedies (if pursued) require longer OOS window (paid data) or different
construction (PF-targeted exits). Test never entered selection; artifacts and
docs updated.

## Next Task (for next agent): No new hypothesis specified — H14 closes the H10 family line

All changes from H14 are uncommitted (commit policy: only when explicitly
asked). Intended files if committing: `run_h14_pf_margin_selection_audit.py`,
`HYPOTHESIS_SPEC.md`, `INEFFICIENCY_RANKING.md`, `NEXT_TASK.md`, and the H14
artifact under `.experiments/`. Do not stage `__pycache__/*.pyc`.

**Documented-but-infeasible items (do not re-attempt without a new data source):**
longer intraday history and ongoing OOS time-extension — a live (uncached)
yfinance fetch verified on 2026-10-11 returns no hourly `=F` bars beyond
2026-10-09. Both require a paid data source.
