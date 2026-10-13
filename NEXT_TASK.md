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

## Next Task (for next agent): H14 — PF-Margin-Targeted Selection Audit

H13 established that the H10 config's PF margin is
fragile. The open question: is the fragility a property
of the *selection* (Val-Sharpe selection happened to pick
a thin-PF-margin config) or of the *family* (no config
in the 13,824-combo grid has a robust PF margin on this
window)? Bounded, artifact-reuse-first design (≤ 0.2 CPU-h):

1. **Rank by Val PF margin.** From the H10 artifact
   `exp_2026-10-11T17-41-18-169363Z/grid_results.parquet`
   (per-combo `val_profit_factor`), take the top K=50
   configs by Val PF margin (`val_profit_factor − 1.3`),
   excluding the frozen H10 config (already audited).
2. **Re-run the K configs logging per-combo OOS returns**
   (reuse `run_h12_selection_bias_audit._rebuild_grid_oos`
   machinery, restricted to the K configs — ~1 min).
3. **H13 fragility gates per config:** OOS PF bootstrap
   95% CI lower bound (2,000 seeded resamples), worst-case
   DSR-adj OOS Sharpe (N=K), and leave-one-out symbol
   dispensability (reuse `per_symbol_contributions`).
4. **Decision rule (pre-register before execution):**
   - If ≥ 1 config passes all three gates, report it as a
     strictly more robust certification candidate — but it
     then requires its own H12-style selection-bias audit
     at N=K (it was selected on Val PF, so the DSR must
     use the Val-PF distribution and N=K trials).
   - If none pass, the PF-margin fragility is a family
     property on this ~2-year hourly window — a durable
     negative result that closes the H10 line: the only
     remedies are a longer OOS window (paid data) or a
     different construction (e.g., PF-targeted exits).

**Pre-registration for H14** (write before execution):
- Null (H0): no config in the top-K-by-Val-PF-margin
  set passes all three H13 fragility gates (PF bootstrap
  CI LB ≥ 1.3, worst-case DSR-adj OOS Sharpe ≥ 1.0 at
  N=K, all symbols dispensable).
- Deliverables: `run_h14_pf_margin_selection_audit.py`,
  artifacts in `.experiments/artifacts/exp_<H14>/`,
  updated `HYPOTHESIS_SPEC.md` and `INEFFICIENCY_RANKING.md`,
  final verdict with root-cause attribution, regression
  tests.
- Reuse the H12 grid machinery, H13 fragility helpers
  (`_profit_factor`, `bootstrap_profit_factor_distribution`,
  `_leave_one_out_pf`, `deflated_sharpe_ratio`,
  `deflated_sharpe_ratio_single_peek`) and the H11 public
  API — no new engine code.

**Constraints (unchanged):** no live trading, no secrets, no
paid data, Test never enters selection, preserve negative
results, ≤ 4 CPU-h per experiment, reuse existing engine /
tracking / validation infrastructure, all regression tests
passing (105/105 at the time of this writing).

**Documented-but-infeasible items (do not re-attempt
without a new data source):** longer intraday history and
ongoing OOS time-extension — a live (uncached) yfinance
fetch verified on 2026-10-11 returns no hourly `=F` bars
beyond 2026-10-09. Both require a paid data source.
