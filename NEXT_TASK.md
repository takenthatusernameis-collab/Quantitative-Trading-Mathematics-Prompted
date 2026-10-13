# Next Task — H15 (regime-aware exit redesign) prep: bar-level per-symbol OOS contribution decomposition

## Status of previous work
- **H10–H12**: certified chain (Sharpe-robust, selection-bias-corrected). All gates PASS.
- **H13**: REJECT on the PF-fragility axes — OOS Sharpe *is* deflation-robust (worst-case DSR-adj 1.2745, p = 0.00102) but the PF margin is statistically fragile (bootstrap 95% CI [1.190, 1.425], P(PF ≥ 1.3) = 51.7%) and **single-symbol-dependent** (CL=F and GC=F indispensable: leave-one-out pooled PF 1.249 / 1.282).
- **H14**: REJECT — PF-margin fragility is a **family property** on this window (0/50 top-by-Val-PF-margin configs clear all three gates; CI-LB max 1.199).
- **Probe (this repo's prior NEXT_TASK)**: feasibility probe concluded extended-data acquisition is **UNLIKELY** to fully resolve the fragility on the free `yfinance` hourly `=F` horizon (~730-day hard cap, no bars past 2026-10-09); paid data would need ~5× current OOS bars (~25k) *if* the point estimate (PF 1.304) holds, and CL/GC indispensability is structural, not sample-limited. Committed at `.experiments/probes/extended_data_feasibility_probe.md` + `tests/test_probe_report_schema.py` (6 tests).

## What changed in this session
- **Added `tests/test_certified_artifact_values.py`** — 34 value-pinning regression tests (drift guards) that assert the *published* H10–H14 gate numbers directly against the frozen artifacts (summary.json + parquet), which were previously NOT pinned (grep for `1.304`, `1.2758`, `1.190`, `1.2745`, `6.9e-06`, `indispensable`/`leave_one_out` across `tests/` returned zero matches before this change). Covers:
  - H10: selected config, OOS Sharpe 1.2758 / PF 1.3042 / MDD -0.0584 / 2416 trades / wf-stability 0.7806 / benchmark p 4.79e-10 / 8/8 gates PASS; `regime_scaling_only` ablation lowers PF (1.304→1.249) — a pre-registered data-wall signal.
  - H11: bit-exact reproduction of H10 (abs_diff = 0), seed determinism (max equity Δ = 0 across seeds 42/7/123/2026), ±20% perturbation floor passes (ratio 0.805 ≥ 0.5), ±50% cost stress (PF stays ≥ 1.3 through 2.0×; breakeven 1.5418×), shifted-split reproduction, non-concentration.
  - H12: DSR-family 1.4093 (p 0.00288), PBO 0.0552, family-wide Bonferroni/BH p 6.89e-6, family trials 14,389, Val-PF-margin quantiles (frac OOS PF pass 0.32%).
  - H13: worst-case DSR-adj 1.2745 (p 0.00102), PF bootstrap CI [1.190018, 1.424838] (LB < 1.3 ⇒ FAIL), P(PF≥1.3)=51.7%, CL/GC indispensable, cost break-even 1.54199 (matches H11 to 2e-4), shifted-split PF shortfalls.
  - H14: 0/50 passing, CI-LB max 1.1993, all DSR ≥ 1.0, all `all_symbols_dispensable` False.
  - **Cross-artifact identity**: H10 PF = H11 f1 OOS PF = H13 `selected_oos_profit_factor` = 1.3041645169434146 exactly (and Sharpe = 1.2757590680990518) — a bit-identity invariant across the certification chain.
- **Working tree**: restored stale tracked `.pyc` bytecode churn (8 files) so `git status` is clean except the new test file.

## What was verified
- `python -m pytest tests/ -q` → **149 passed in 3.76s** (115 prior + 34 new). No regressions.
- The new tests read only committed frozen artifacts; no pipeline recompute, no network (the test process used the `.cache/data` layer already on disk, never refetched).
- All pinned values match the report-quoted certification numbers in `FINAL_REPORT.md`, `HYPOTHESIS_SPEC.md` (H13/H14), and the artifact `summary.json` files.

## What remains unresolved (the H10–H14 line is data-walled)
- **Data horizon**: free `yfinance` hourly `=F` hard-capped at ~730 days (no bars past 2026-10-09). This is a hard stop for extending the *futures TSMOM* line; paid data (CQG/Rithmic/IQFeed/Databento/Polygon) required.
- **PF-margin fragility is structural**, not selection-mined: H14 showed 0/50 even when selecting on Val PF margin (excluding H10). The margin (+0.004 over 1.3) is thinner than bootstrap noise (CI half-width ±0.117) and carried by commodity loss-offsetting (CL=F net PF 1.358 is the *only* symbol above the pooled PF, yet its removal collapses pooled PF to 1.249 — the non-monotonicity flagged in H13).
- **regime-aware vol-scaling does not rescue PF** — the frozen H10 grid's `regime_scaling_only` ablation *lowers* OOS PF (1.304→1.249). A regime-aware *exit* redesign (vs. vol scaling) remains untested and is the only un-tried signal-redesign lever.

## Approaches already failed and why
- PF-margin-targeted selection over top-K by Val PF margin (H14): all 50 fail the OOS PF bootstrap CI-LB gate (max 1.199); fragility is family-level, not a single bad config.
- Extended-data feasibility alone (probe): needs ~5× OOS bars to plausibly move CI-LB ≥ 1.3 *only if* point estimate holds; not available (no paid data); CL/GC indispensability is structural, not N-limited.
- Regime-aware **vol** scaling (frozen H10 ablation): lowers PF (1.304→1.249), Sharpe (1.276→1.021).

## One precise next task (bounded, verifiable, no network)
**H15-prep: refine the CL/GC loss-offset root-cause via a bar-level per-symbol OOS contribution decomposition on the frozen H10 artifacts.**

The H13 root cause states pooled PF is *non-monotone* in per-symbol PF because GC=F (below-pooled net PF) masks an offsetting role. That attribution was computed at trade-aggregate level. The frozen H10 artifacts contain **bar-level** `positions.parquet` (5 symbols), `prices.parquet`, `returns.parquet`, `regime_factors.parquet` (1.0/0.5/0.25), and `vix_hourly.parquet` over the full 11,441-bar history. The next agent should:

1. **Compute bar-level per-symbol contribution to OOS P&L** on the frozen OOS window (last 4,576 bars, matching H13's 60/20/20 split) as `pos.shift(1) * price.pct_change`, decomposed by regime factor and by high-VIX crisis stratum (VIX ≥ 20 and ≥ 25).
2. **Decompose per-symbol gross wins / gross losses** to identify which (symbol × regime) loss bars the CL/GC legs offset (the mechanism that pins pooled PF ≥ 1.3).
3. **Check the monotonicity claim directly**: confirm that removing CL=F or GC=F *at the bar level* reverses the win/loss balance enough to drop the pooled PF below 1.3, and that the two symbols' loss bars are anti-correlated (the offsetting structure).
4. Produce a single derived artifact `.experiments/probes/h15_loss_offset_decomposition.parquet` (per-symbol × regime gross-up / gross-dn / net, plus CL/GC loss-bar overlap statistic) and a structured markdown report `.experiments/probes/h15_loss_offset_decomposition.md`.
5. add `tests/test_h15_loss_offset_decomposition.py` validating: (a) the report schema (required fields), (b) the **decomposition invariant** — strata gross-up/gross-dn sums reconstruct the pooled PF to bit-exactness (PF = Σup / Σdown across strata), (c) per-symbol contributions sum to the portfolio return series to within float tolerance, and (d) CL=F / GC=F are flagged as the indispensable loss-offset pair.

**Constraints:** no recomputation of the frozen pipeline (use frozen `positions`/`prices`/`returns`/`regime_factors`/`vix` only); no network; runtime < 0.1 CPU-h; do not modify any committed H10–H14 artifact. This is a *diagnostic*, not a new selection — it sharpens root-cause attribution so the eventual H15 regime-aware-exit redesign (which needs paid/longer data and is explicitly out of scope until then) is targeted.

## Evidence / constraints
- Frozen bar-level artifacts available and aligned (11,441 rows, identical DatetimeIndex): `.experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/{positions,prices,returns,regime_factors,vix_hourly,trades}.parquet`.
- OOS window = last 4,576 bars (60/20/20 split; matches H13 `shifted_splits` 60/20/20 `oos_bars=4576`).
- H13 `reproduction_checks`: `returns_max_abs_diff_vs_h10 = 0.0`, `per_symbol_reconstruction_max_abs_diff = 6.9389e-18` — the frozen engine state is the ground truth to decompose against.
- Invariants to assert: (i) Σ_stratum gross_up / Σ_stratum gross_down = pooled OOS PF; (ii) Σ_symbol (pos.shift * ret) = portfolio `returns.parquet` on OOS; (iii) CL/GC leave-one-out pooled PF < 1.3 at bar level.
