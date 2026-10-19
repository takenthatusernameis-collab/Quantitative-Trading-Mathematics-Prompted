# NEXT TASK — H28: causal re-certification of the intraday futures TSMOM family

**Status: assigned to the next agent. Free data, bounded, verifiable.**
**Written 2026-10-19, immediately after H27 (P&L level audit + look-ahead attribution).**

## Why this task exists (the evidence)

H27 (pre-registered in `HYPOTHESIS_SPEC.md` §H27, artifacts in
`.experiments/artifacts/h27_pnl_level/`) settled the open question H26 left open about the
*level* of the certified intraday P&L. Two verdicts:

- **`LEVEL_CONFIRMED`** — the P&L level carries **no unit or scale error**. The dollar P&L
  recomputed from the committed prices/positions with the engine's contract maths
  (`contracts = weight x 1e6 / (price x multiplier)`, `P&L = contracts x dPrice x multiplier`)
  reproduces the logged returns to **≤4.9e-16**; the contract specs are exactly consistent
  (`tick_value == tick_size x multiplier`); the cost drag recomputed from `trades.parquet`
  matches the engine to **≤1.1e-19** and is 1.1%–4.9% of the gross edge. The published
  Sharpe is not a factor-of-1000 slip.
- **`LOOKAHEAD_CONFIRMED`** — but the *positions were not knowable when they were traded*.
  `run_h9_intraday_tsmom_experiment.py::_daily_target_from_hourly` collapses the hourly
  signal to `resample("1D").last()` (a day-labelled series holding **that day's closing**
  signal) and `run_h10_intraday_tsmom_pfopt_experiment.py::build_hourly_target` expands it
  back with `reindex(index, method="ffill")`, which assigns **every bar of day D the value
  of day D's label**. Every session is positioned at its own open with the signal computed
  at its own close. This affects **H9, H10, H21, H22 and H25 alike**.

Causal counterfactual (the *selected* config of each family, the daily series lagged by
exactly one day, nothing else in the pipeline changed, all five rebuilds bit-exact against
the committed artifacts):

| Family | Published OOS Sharpe | Causal | Relative drop | Published PF | Causal PF | Published equity | Causal equity |
|---|---|---|---|---|---|---|---|
| H9 (REJECT) | 1.0565 | 0.1860 | 82.4% | 1.253 | 1.042 | 8.02x | 1.26x |
| H10 (PASS) | 1.2758 | 0.2923 | 77.1% | 1.304 | 1.063 | 6.92x | 1.19x |
| H21 (REJECT) | 0.8394 | 0.1317 | 84.3% | 1.206 | 1.030 | 14.96x | 1.27x |
| H22 (PASS) | 1.3725 | 0.3605 | 73.7% | 1.334 | 1.077 | 79.80x | 1.89x |
| H25 (PASS) | 1.3236 | 0.3231 | 75.6% | 1.320 | 1.069 | 100.73x | 2.03x |

94.7%–97.8% of the published gross P&L is **intraday** P&L (open → close), i.e. the part of
the session that can only be earned by knowing that session's close in advance (the mean
`sign(w_open) × r_intraday` tilt is +0.00248 published vs +0.00040 causal — a 5.9×–6.2×
excess). The
equal-weight buy-and-hold of the same five futures grows **1.36x** over the same window,
while the published H25 grows **100.7x** under a 5x gross leverage cap.

**Consequence:** the published PASS verdicts of H10/H11/H12/H22/H25 stand as published (H27
changed no gate, threshold, verdict or certified number) but they are **not evidence of a
tradable edge**. The family must be re-certified under a causal daily collapse.

## Scope

1. **Implement the causal target builder — without editing the published runners.**
   `run_h9_intraday_tsmom_experiment.py` and `run_h10_intraday_tsmom_pfopt_experiment.py`
   are the *historical record*: H26 and H27 both reproduce the committed H10/H21/H22/H25
   artifacts **bit-exactly** from them, and those artifacts are the certified ones. Editing
   those functions in place would silently invalidate that reproducibility. Instead:
   - add a causal builder, e.g. `build_hourly_target(..., lag_days=1)` or a new
     `causal_daily_target_from_hourly(hourly_signal)` next to the existing one (the exact
     implementation is already written and tested in
     `run_h27_pnl_level_audit.py::causal_daily_target_from_hourly` — daily series shifted by
     one calendar day, with the calendar-completeness assertion);
   - add a new runner `run_h28_causal_recertification.py` that imports the H9/H10/H21/H22/H25
     primitives unchanged and uses the causal builder;
   - cover it with unit tests (the shift semantics, the calendar-gap guard, the
     module-restore behaviour).
2. **Re-run the family** with the **same** gates, the same 55/25/20 index splits, the same
   Val-only selection and the same Test protection, the same cost model and the same
   capital/leverage/caps:
   - H22 (8 combos: `target_vol_mult x max_pos`), H25 (8 combos: `target_vol_mult x
     n_assets`), H21 (16 combos), and H10 (13,824 combos, ≈0.48 CPU-h — permitted because
     a defect *was* found and this re-registration is explicit).
   - The H10 grid's selection rule (best Val Sharpe; Val PF reported) and the H25 rule
     (best Val PF margin) must be reused unchanged.
3. **Record an honest verdict.** **Expect REJECT.** The causal counterfactual on the
   *already-selected* configs is OOS Sharpe 0.29–0.36 (gate ≥ 1.0), PF 1.06–1.08 (gate
   ≥ 1.3) and max DD −12% to −26% (gate ≤ 15%). H28's purpose is to certify the truth,
   not to find a passing configuration. A causal re-selection could land on a different
   config; report whatever the selection produces.
4. **Pin the outcome** in `tests/test_h28_*.py` and write the measure log to
   `HYPOTHESIS_SPEC.md` §H28, then update `FINAL_REPORT.md`, `HANDOFF.md` and
   `HANDOFF_NEXT.md`.

## Pre-registration requirements (write the spec BEFORE running)

- The verdict rule, e.g. `CAUSAL_CERTIFIED` iff the causal family's OOS gates all pass on
  the protected OOS window; `CAUSAL_REJECTED` otherwise. State explicitly that the gates,
  the splits, the selection rule and the cost model are **unchanged** from H9–H25, and that
  the published artifacts are **not** rewritten.
- The frozen artifact ids for the causal runs and the frozen list of the *published*
  artifacts that must remain bit-reproducible (H10, H21, H22, H25) — with the requirement
  that the H27 look-ahead regression test keeps passing (the published construction must
  keep its documented look-ahead property, so the record stays auditable).
- A **negative control**: the same pipeline with the *published* (same-day) expansion must
  reproduce the published H10/H21/H22/H25 numbers bit-exactly. If it does not, the causal
  run is not comparable and the run is void.

## Constraints

- **Do not** modify the published artifacts, the published runners' logic, any gate,
  threshold, verdict or certified number.
- **Do not** re-label the published family as certified or uncertified in the artifacts; the
  published verdicts stay as published and the H27 flag travels with them.
- Keep everything **offline and deterministic** (the cached hourly `=F` + `^VIX` data and
  the committed `prices.parquet` are sufficient — no new fetch is needed, and the H27 audit
  rebuilds all five families from the committed prices alone).
- Do not run the paid-data task (wider OOS window) before H28: buying more data for a
  construction with a look-ahead is wasted. The paid-data task remains downstream.

## Verification (same commands as every session)

`python -m pytest -q`, `python -m pytest -W error -q`,
`python -m pytest --cov=qtr --cov-report=term-missing`,
`python -m ruff check src tests run_*.py`, `python -m ruff format --check src tests run_*.py`,
`bash -n .github/scripts/*.sh`, `bash .github/scripts/test_kilo_progress.sh`.

Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.

## Evidence index

- H27 spec + measure log: `HYPOTHESIS_SPEC.md` §H27.
- H27 runner: `run_h27_pnl_level_audit.py`; artifacts:
  `.experiments/artifacts/h27_pnl_level/summary.json` + `level_table.parquet`.
- H27 tests: `tests/test_h27_pnl_level_audit.py` (36 tests, incl. the causal-collapse
  semantics and the negative guards).
- H27 report: `FINAL_REPORT.md` §H27 detail and the executive-summary block.
- H26 (the scale correction that led here): `HYPOTHESIS_SPEC.md` §H26,
  `run_h26_sharpe_scale_audit.py`, `.experiments/artifacts/h26_sharpe_scale/`.
