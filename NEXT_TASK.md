# NEXT TASK — H29: systematic look-ahead sweep of the remaining certified families

**Status: assigned to the next agent. Free data, bounded, verifiable.**
**Written 2026-10-19, immediately after H28 (causal re-certification of the intraday family).**

## Why this task exists (the evidence)

Two sessions of work have established, and then closed out, the look-ahead question for the
**intraday** futures TSMOM family:

- **H27** (`HYPOTHESIS_SPEC.md` §H27) — `LEVEL_CONFIRMED` / `LOOKAHEAD_CONFIRMED`. The P&L
  *level* is arithmetically clean (L1 ≤ 4.9e-16, L2 exact, L3 ≤ 1.1e-19), but the positions
  were **not knowable when they were traded**: the daily-target collapse hands every bar of day
  D the signal at day D's **close**.
- **H28** (`HYPOTHESIS_SPEC.md` §H28) — the **re-certification**. Under a causal daily collapse
  (same gates, same 55/25/20 splits, same Val-only selection, same Test protection, same cost
  model, full grids re-run) **every family fails**:

  | Family | Published | Causal verdict | OOS Sharpe | OOS PF | Max DD | Gates |
  |---|---|---|---|---|---|---|
  | H10 | PASS | **CAUSAL_REJECTED** | 0.3909 | 1.087 | −10.1% | 3/8 |
  | H21 | REJECT | **CAUSAL_REJECTED** | 0.1317 | 1.030 | −26.1% | 3/8 |
  | H22 | PASS | **CAUSAL_REJECTED** | 0.3605 | 1.077 | −22.8% | 4/9 |
  | H25 | PASS | **CAUSAL_REJECTED** | 0.3231 | 1.069 | −26.2% | 4/9 |

  All four negative controls reproduced the published artifacts **bit-exactly** (max abs diff
  0.0, including every one of the 13,824 H10 grid rows), so the comparison is sound; and the
  causal re-selection buys at most +0.10 Sharpe, so the REJECT is not an artefact of a frozen
  configuration.

**The defect is mechanical, and that makes it searchable.** `pandas` labels a resampled bin at
its **left edge** for most frequencies but at its **right edge** for month-end frequencies:

| Collapse | Bin label | Value held | Expansion `reindex(..., method="ffill")` | Look-ahead? |
|---|---|---|---|---|
| `resample("1D")` | **bin start** (day D 00:00) | day D's **close** | every bar of day D gets day D's close | **YES** |
| `resample("ME")` | **bin end** (last day of the month) | the month's close | the month gets the *previous* month's close | no |

H9/H10 (and everything descending from them: H21/H22/H25) use the first row; H6/H7/H8 use the
second. That distinction is a *hypothesis* about the untested families, not a result: it was
derived from the pandas semantics and has **not** been checked against the committed artifacts of
the daily families.

## Scope

1. **Enumerate every certified family and audit it for the same pattern.** The families H27/H28
   covered (H9, H10, H21, H22, H25) are done. The ones that are **not**:
   - the **daily / monthly** families (H1–H8) — the "certified" daily TSMOM family, which is the
     only other PASS family in the repo;
   - the **intraday diagnostics** that inherit H10's construction (H11 robustness, H12 selection
     bias, H13 OOS deflation / PF audit);
   - **H23** (crypto) — a different runner with no daily-collapse construction; REJECTED, but it
     should be swept for completeness.
2. **For each family, decide from the committed artifacts alone** whether the position held at
   the start of a period is aligned with *that* period's own close (look-ahead) or with the
   previous period's close (causal). Use the same artifact-only evidence chain H27 used: compare
   the logged collapsed target against the signal at the period's open and at its close, and
   check the fraction of bars on which the logged target matches the *same-period* expansion.
3. **Sweep the source for the pattern**, not just the artifacts: grep every runner for
   `resample(...)` followed by a forward-fill expansion, and classify each occurrence by the
   bin-label position. A construction that collapses a sub-daily signal to a coarser frequency
   and expands it back with `method="ffill"` is a look-ahead **iff** the bin label sits at the
   bin's start.
4. **Report per family**, with the mechanism, the evidence and the frozen artifact ids. Where a
   family is affected, state the magnitude in the same terms H27 used (OOS Sharpe under the
   minimal causal fix, and the intraday/overnight P&L split) — but do **not** re-run grids.
   The families that use `resample("ME")` are expected to be clean; a family that is *not* clean
   is a finding and must be reported as such.

## Pre-registration requirements (write the spec BEFORE running)

- The verdict rule: `SWEEP_CLEAN` iff no audited family shows the same-period expansion on its
  committed artifacts; `LOOKAHEAD_FOUND` otherwise, listing the affected families. State
  explicitly that no published artifact is rewritten, no published verdict is changed and no
  published runner is edited.
- The frozen list of artifact ids to audit, and the frozen list of the *already-audited*
  families (H9/H10/H21/H22/H25) whose H27/H28 results must be reproduced by the sweep's
  machinery (a self-check: the sweep's detector must **fire** on H10 and **not** fire on a
  monthly family, or the detector is broken).
- A **negative control for the detector**: the same detector run against a deliberately
  *causal* construction (the H27 `causal_daily_target_from_hourly` lag) must report clean.

## Constraints

- **Do not** modify the published artifacts, the published runners' logic, any gate, threshold,
  verdict or certified number.
- **Do not** re-label the published family as certified or uncertified in the artifacts; H28's
  `CAUSAL_REJECTED` travels with it.
- Keep everything **offline and deterministic** (the cached data and the committed
  `prices.parquet` are sufficient; no new fetch).
- If the sweep finds a *second* defective family, the follow-up (a causal re-certification like
  H28) is a separate, explicitly re-registered task — do not run it inside H29.
- The paid-data task (a wider OOS window for the PF bootstrap margin) stays **downstream** and
  is *not* justified for the intraday family: a causal construction that fails the gates on the
  free window will not be rescued by more of the same data. It may still be justified for the
  *daily* families, which H29 would certify as clean.

## Verification (same commands as every session)

`python -m pytest -q`, `python -m pytest -W error -q`,
`python -m pytest --cov=qtr --cov-report=term-missing`,
`python -m ruff check src tests run_*.py`, `python -m ruff format --check src tests run_*.py`,
`bash -n .github/scripts/*.sh`, `bash .github/scripts/test_kilo_progress.sh`.

Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.

## Evidence index

- H28 spec + measure log: `HYPOTHESIS_SPEC.md` §H28.
- H28 runner: `run_h28_causal_recertification.py`; artifacts:
  `.experiments/artifacts/h28_causal_recertification/` + the eight run directories
  (`h10_h22_h25_h21` control/causal exp ids are listed in that `summary.json`).
- H28 tests: `tests/test_h28_causal_recertification.py` (47 tests, incl. the negative controls).
- H27 spec + measure log: `HYPOTHESIS_SPEC.md` §H27; runner `run_h27_pnl_level_audit.py`;
  artifacts `.experiments/artifacts/h27_pnl_level/`.
- H27 tests: `tests/test_h27_pnl_level_audit.py` (36 tests).
- H26 (the scale correction that led here): `HYPOTHESIS_SPEC.md` §H26,
  `run_h26_sharpe_scale_audit.py`, `.experiments/artifacts/h26_sharpe_scale/`.
