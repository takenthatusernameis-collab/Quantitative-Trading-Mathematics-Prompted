# Next Task: H11 complete — PASS (certified robust)

## H11 executed 2026-10-11 — **PASS**

Robustness / certification of the frozen H10-selected config.
0.016 CPU-h. Artifacts: `.experiments/artifacts/exp_2026-10-11T18-40-37-427062Z/`.
Script: `run_h11_robustness_experiment.py`.

| Pre-registered component | Result |
|---|---|
| F1 gate re-verification | 8/8 PASS, **bit-exact** reproduction of the H10 artifact (max \|Δ\| = 0) |
| E1 seed determinism | HOLDS — seeds {42, 7, 123, 2026} give identical equity (pipeline is deterministic; seeds inert) |
| E1 bootstrap OOS Sharpe CI | **[0.839, 1.698]**, P(Sharpe ≥ 1.0) = 0.888 (2,000 resamples) |
| E2 ±20% perturbation gate (≥ 0.5×) | **PASS** — min perturbed Sharpe 1.027 = **0.805×** optimum (gate previously unevaluated in the family) |
| E3 cost stress ±50% (PF ≥ 1.3) | **PASS** — PF 1.308 (0.5×) / 1.300 (1.5×); break-even cost multiplier **1.542×** |
| E4 shifted splits (diagnostic) | Sharpe 1.204 / 1.365 / 1.234 (all ≥ 1.0); PF 1.281 / 1.330 / 1.292 (**PF fails on 2 of 3 shifted windows**) |
| E4 rolling 25% windows | min 0.709, mean 1.201, max 1.436; 93.75% of 16 windows ≥ 1.0 |
| E4c shifted-window re-selection (324 combos) | **Re-selects the identical config** (vw=1008, tm=2.0, mhb=60, vlm=1.5, vff=0.25) — selection stable |
| E5 per-symbol concentration | HHI(|P&L|) = 0.214 (equal-weight 0.200), max GP share 0.233, all 5 symbols positive Sharpe (0.337–0.797) — **diversified** |
| Live-extension probe | No fresh bars beyond 2026-10-09 (free yfinance hourly source is hard-limited to ~730 days) |

**Verdict: PASS.** The H10 certification is robust on the
pre-registered window.

**Critical caveat carried forward:** the OOS profit factor (1.304)
clears the 1.3 gate by only **+0.004 (+0.3%)**. Under +50% costs
PF = 1.300 (margin +0.0003); on shifted OOS windows PF =
1.281–1.292 (gate fails). **Sharpe is robust; profit factor is
the fragile gate.**

**Largest uncorrected threat:** the H10 selection searched
**13,824 configurations** (and the H1–H11 family has evaluated
~14,400+). No multiple-testing / selection-bias correction has
been applied to the certification. With that many trials, the
expected maximum Sharpe under the null is substantial — the
certification is not yet statistically defensible without a
deflated-Sharpe / PBO audit.

---

## Next Task (for next agent): H12 — Selection-Bias Audit

H11 certified the H10 config as robust to seeds, perturbations,
costs and split shifts. The remaining question is whether a
13,824-combo grid search can manufacture a "passing" config by
chance alone. H12 applies the standard corrections:

1. **Deflated Sharpe Ratio (Bailey & López de Prado 2014)**:
   compute the DSR of the H10 selected config given
   N = 13,824 trials, using the moments (mean, std, skew,
   kurtosis) of the preserved per-combo Val-Sharpe distribution
   (`.experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/grid_results.parquet`,
   column `val_sharpe` — no new backtests needed). The DSR tests
   whether the best-of-N Val Sharpe is distinguishable from the
   expected maximum of N random trials.
2. **Probability of Backtest Overfitting (PBO) via CSCV**
   (Bailey et al. 2014; Arroyo et al. 2022): re-run the H10
   grid logging **per-combo OOS (Val+Test) metrics** (the H10
   run only logged Val metrics per combo; ~29 min, 0.5 CPU-h —
   within the ≤ 4 CPU-h budget), then compute PBO with S = 16
   combinatorially-symmetric blocks. PBO < 0.3 indicates the
   selection is not an overfitting artifact.
3. **Family-wide multiple-testing audit**: pool the trial counts
   of every grid search in the family (H1: 18, H2: 54, H3: 108,
   H4: 18, H5: 6, H6: 6, H8: 5, H10: 13,824, H11: ~350 →
   ~14,400) and recompute the deflated Sharpe / Bonferroni- and
   FDR-adjusted significance of the H10 OOS benchmark p-value
   (4.8e-10) under the pooled trial count.
4. **PF-margin sensitivity (diagnostic)**: using the H10 grid
   artifact, report the distribution of `val_profit_factor` and
   the fraction of combos with PF ≥ 1.3 — quantifies how much of
   the PF "pass" is selection pressure vs genuine edge.

**Pre-registration for H12** (to be written by the next agent
before execution):
- Null (H0): the H10 selected config's edge does not survive
  selection-bias correction — DSR-adjusted Sharpe < 1.0, or
  PBO ≥ 0.5, or the benchmark alpha is not significant after
  family-wide multiple-testing correction.
- Deliverables: `run_h12_selection_bias_audit.py`, artifacts in
  `.experiments/artifacts/exp_<H12>/`, updated `HYPOTHESIS_SPEC.md`
  and `INEFFICIENCY_RANKING.md`, final PASS/REJECT verdict with
  root-cause attribution.

**Constraints (unchanged):** no live trading, no secrets, no paid
data, Test never enters selection, preserve negative results,
≤ 4 CPU-h per experiment, reuse existing engine / tracking /
validation infrastructure, all regression tests passing.

**Documented-but-infeasible items (do not re-attempt without a
new data source):** longer intraday history and ongoing OOS
time-extension — a live (uncached) yfinance fetch verified on
2026-10-11 returns no hourly `=F` bars beyond 2026-10-09.
Both require a paid data source.
