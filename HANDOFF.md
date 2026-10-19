# HANDOFF — H27 P&L level audit + look-ahead attribution (2026-10-19)

## What changed

**H27 — a pre-registered audit of the certified intraday P&L (new hypothesis-instance
H27; no grid was re-run, no gate, threshold, verdict or certified number changed).**

### New
- `run_h27_pnl_level_audit.py` — deterministic, offline audit over the five frozen intraday
  artifacts (H9/H10/H21/H22/H25). It (i) recomputes the per-bar **dollar P&L** from
  `prices.parquet` + `positions.parquet` with the engine's contract arithmetic, (ii) checks
  the contract specs, (iii) recomputes the **cost drag** from `trades.parquet`, (iv) checks
  the vol-target coherence on both annualization scales, (v) proves the information-timing
  defect from the artifacts alone, (vi) re-runs each family's **selected** config with a
  causal one-day-lagged daily collapse, and (vii) splits the gross P&L into its overnight and
  intraday components. Runtime ≈ 5 s, no network, no grid.
- `.experiments/artifacts/h27_pnl_level/summary.json` + `level_table.parquet`.
- `tests/test_h27_pnl_level_audit.py` — 36 tests (level checks, contract specs, vol-target
  coherence, artifact-only look-ahead chain, bit-exact rebuild, causal counterfactual,
  P&L attribution, verdict strings, negative guards).

### Changed
- `HYPOTHESIS_SPEC.md` — new §H27 with the **pre-registration frozen before the audit run**
  (level verdict rule quoted from `NEXT_TASK.md`, the L1–L5 measurement plan, the
  look-ahead sub-rule, the anti-reward-hacking note) and the **measure log**.
- `FINAL_REPORT.md` — executive-summary look-ahead block, a corrected "not established"
  claim, the results-table H27 validity flag, a new §H27 detail section, a corrected
  Conclusion, corrected Summary statistics (28 instances) and a rewritten §Next Task.

## What was actually verified

- `python -m pytest -q` → **622 passed** (586 before + 36 new), 0 warnings.
- `python -m pytest -W error -q` → clean.
- `python -m pytest --cov=qtr --cov-report=term-missing` → coverage unchanged (the audit
  adds no library code; the new helpers live in the runner).
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → clean.
- `bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
- **Audit self-consistency:** for all five families the rebuild of the *selected* config from
  the committed prices reproduces the committed `positions.parquet` **and**
  `returns.parquet` with max abs diff **0.0** (bit-exact), and the published OOS Sharpe is
  re-derived exactly for H10/H21/H22/H25 (|Δ| = 0.0; H9 differs by 1.0e-4 for the
  pre-existing ddof drift H26 already diagnosed).

## The finding (headline)

**The P&L *level* is clean; the *information timing* is not.** H27's two verdicts are
`LEVEL_CONFIRMED` and `LOOKAHEAD_CONFIRMED`, and `certified_family_valid = false`.

**Level (no unit error).** `contracts = weight × 1e6 / (price × multiplier)` and
`P&L = contracts × Δprice × multiplier` reproduce the logged return series to **≤4.9e-16**
(L1); `tick_value == tick_size × multiplier` holds exactly for all five symbols and the
per-contract cost matches `commission + (spread+slippage) × tick_value` exactly (L2); the
cost drag recomputed from `trades.parquet` matches the engine to **≤1.1e-19** and is
**1.1%–4.9%** of the gross edge (L3). The vol target is applied to the same hourly-return
quantity the P&L is built from (L4); the *annualization* is the same mismatch H26 found
from the Sharpe side — the code uses `√(252 × 6.5) = 1638` bars/yr while the artifacts'
bar index implies **5,701** bars/yr (**1.8657×**).

**Look-ahead (the real defect).** `run_h9_intraday_tsmom_experiment.py::_daily_target_from_hourly`
collapses the hourly signal to `resample("1D").last()` — a day-labelled series holding *that
day's closing* signal — and `run_h10_intraday_tsmom_pfopt_experiment.py::build_hourly_target`
expands it back with `reindex(index, method="ffill")`, which assigns **every bar of day D the
value of day D's label**. Every session is therefore positioned at its own open with the
signal computed at its own close. This affects **H9, H10, H21, H22 and H25 alike**.

Three independent proofs (all in the audit artifact):

1. *Artifact-only*: the logged daily collapse equals the logged signal at that day's close
   to 0.0 while the signal at the day's open differs by up to 3.87–4.0; the expansion puts
   the close value on the open bar. For H21/H22/H25 the logged expanded hourly target
   matches the **same-day** expansion on **100%** of bars and the previous-day expansion on
   only **38.6%**.
2. *Bit-exact rebuild*: each family's selected config rebuilt from the committed prices
   reproduces the committed positions and returns with max abs diff **0.0**; the rebuilt
   target matches the same-day expansion on 100% of bars.
3. *Causal counterfactual*: shifting only the daily series by one day (nothing else in the
   pipeline changes) and re-running the same engine:

| Family | Published OOS Sharpe | Causal | Drop | Published equity (full sample) | Causal | Buy-and-hold |
|---|---|---|---|---|---|---|
| H9 (REJECT) | 1.0565 | 0.1860 | 82.4% | 8.02× | 1.26× | 1.33× |
| H10 (PASS) | 1.2758 | 0.2923 | 77.1% | 6.92× | 1.19× | 1.36× |
| H21 (REJECT) | 0.8394 | 0.1317 | 84.3% | 14.96× | 1.27× | 1.36× |
| H22 (PASS) | 1.3725 | 0.3605 | 73.7% | 79.80× | 1.89× | 1.36× |
| H25 (PASS) | 1.3236 | 0.3231 | 75.6% | 100.73× | 2.03× | 1.36× |

**Where the money came from:** 94.7%–97.8% of the published gross P&L is *intraday* P&L
(engine per-bar chain; overnight gap → session open vs. open → close); under the causal build
the intraday P&L falls 4.574 → 0.653 for H25 (**7.0×**), while the *overnight* component is
earned almost identically by both (0.257 vs 0.279) — the entire difference is the same-day
part of the session. The model-free fingerprint: the mean `sign(w_open) × r_intraday` is
**+0.00248** published vs **+0.00040** causal — a **5.9×–6.2×** excess same-day tilt, in
every family. The equal-weight buy-and-hold of the same basket grows 1.36× over the same
window, while the published H25 grows **100.7×** under a 5× gross leverage cap.

## What remains unresolved

- **The certified family has not been re-certified.** The published PASS verdicts
  (H10/H11/H12/H22/H25) stand as published — H27 is an audit and changed no gate, threshold,
  verdict or certified number — but they are inflated by the look-ahead and are **not
  evidence of a tradable edge**. The family needs an explicitly re-registered
  re-certification under a causal daily collapse (H28).
- **The counterfactual is a lower bound.** It re-runs the *selected* config only (no
  re-selection, no grid re-run), so it understates the defect; a causal re-selection could
  land on a *different* config.
- **H23 (crypto) was not audited** — it is a different construction (its own runner, no
  daily-collapse family) and is REJECTED anyway; H27's scope was the intraday futures family.
- `src/qtr/validation/statistics.py:114` remains the single uncovered branch (unreachable
  `walk_forward_splits` empty-window guard, pre-existing).
- The paid-data task (widen the OOS window so the **PF** bootstrap CI clears its gate with
  margin) is still outstanding — but it is now **downstream** of H28: there is no point
  buying more data for a construction with a look-ahead.

## Which approaches have already failed and why

- No failed approaches this session. One honest disclosure: the look-ahead hypothesis was
  first *observed* during exploratory reproduction (before this section was frozen), even
  though the **level verdict rule** was pre-registered by the previous agent in
  `NEXT_TASK.md` before any execution. The look-ahead sub-rule, the frozen artifact ids and
  the tolerances were fixed before the formal audit run; the rule is symmetric (a clean
  timing would have forced a `LOOKAHEAD_ABSENT` report and a "the sample is extraordinary"
  conclusion), and the measurement plan (L1–L5) was fixed before the audit was run.

## One precise next task

**H28 — re-certify the intraday futures TSMOM family under a causal daily collapse**
(free data, bounded, verifiable). Full scope, constraints and the pre-registration
skeleton are in `NEXT_TASK.md`; the short version:

1. Implement the causal target builder **without** editing the published runners (their
   artifacts are the historical record and H26/H27 depend on reproducing them bit-exactly):
   a new `build_hourly_target(..., lag_days=1)`-style helper plus a new H28 runner that
   imports the H9/H10/H21/H22/H25 primitives unchanged.
2. Re-run the family with the **same** gates, the same 55/25/20 splits, the same Val-only
   selection and the same Test protection: H22 (8 combos), H25 (8 combos), H21 (16 combos)
   and H10 (13,824 combos, ≈0.48 CPU-h — now permitted because a defect *was* found and the
   re-registration is explicit).
3. **Expect REJECT.** The causal counterfactual on the already-selected configs gives OOS
   Sharpe 0.29–0.36, PF 1.06–1.08 and max DD −12% to −26%, all below the gates. H28's
   purpose is to record an honest verdict, not to find a passing configuration.
4. Pin the outcome in `tests/test_h28_*.py`, and keep the published H10/H22/H25 artifacts
   untouched and reproducible (the H27 look-ahead regression test must keep passing).
