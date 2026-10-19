# NEXT TASK — H30: close the H7 coverage gap (commit H7's artifact, then audit it)

**Status: assigned to the next agent. Free data, bounded, verifiable, minutes of compute.**
**Written 2026-10-19, immediately after H29 (systematic look-ahead sweep of the remaining
families).**

## Why this task exists (the evidence)

H29 swept **every** remaining family for the look-ahead that H27 found and H28 re-certified
(`HYPOTHESIS_SPEC.md` §H29, `FINAL_REPORT.md` §H29). The sweep's verdict is `LOOKAHEAD_FOUND`
for the intraday construction (H11/H12/H13 inherit it, H23 uses it directly) and `CAUSAL` for
every daily/monthly family that has a committed artifact (H1–H6, H8 — each rebuilt **bit-exactly**
from the committed prices, min hold lag **+1 bar**, **0** look-ahead bars).

**One family could not be decided: H7.**

* `run_h7_intraday_tsmom_experiment.py` exists and produced the H7 row of the results table
  (OOS Sharpe 0.789, 1,005 trades, PF 1.166, max DD −14.5%, 3/8 gates → REJECTED).
* But **there is no committed artifact**: no `h7` entry in `.experiments/experiments.jsonl` and
  no `exp_*` directory for it. `grep` over every `summary.json` finds no experiment with
  OOS Sharpe ≈ 0.789.
* Consequence: **H7's published numbers cannot be re-derived from committed evidence**, so H29
  had to report it `INCONCLUSIVE` — a coverage gap, *not* a pass. H29's source sweep classified
  its *mechanism* (`resample("ME")` on a **daily** grid → hold lag +1 bar → causal), but a
  mechanism is not an artifact.

This is the last hole in the repo's audit record: a published result row whose provenance cannot
be checked. Everything else in the family table is reproducible from committed artifacts.

## Scope

1. **Re-run H7 offline so its numbers have a committed artifact.** H7 is a **single fixed
   configuration** (no grid): it builds one multi-horizon regime-weighted TSMOM signal on
   `ES=F, NQ=F, CL=F, GC=F, ZB=F` daily bars, applies intraday-path exits and runs one backtest.
   The futures cache is complete (the same symbols/dates as H4/H5/H6, whose artifacts are
   committed), so this is **offline and fast** — verify with `use_cache=True` semantics
   (`fetcher.fetch_futures(..., use_cache=True)`) and **do not** hit the network.
   Commit the artifact under `.experiments/artifacts/<exp_id>/` and add the experiment to
   `.experiments/experiments.jsonl` through the normal tracker.
2. **Reconcile the re-run against the published H7 row** and record the difference explicitly:
   OOS Sharpe 0.789, trades 1,005, PF 1.166, max DD −14.5%, 3/8 gates, verdict REJECTED. State
   the per-field diff (bit-exact or not) and, if any field moves, say which and why. Note the one
   documented library drift (the 2026-10-19 09:28 `walk_forward_splits` change moves
   `metrics.wf_stability` by ~1.3e-3 on a re-run; the published value is reproduced bit-exactly
   by the pre-change implementation). **A published number that cannot be re-derived is the
   defect class this task closes — a mismatch is a finding, not a nuisance.**
3. **Audit the new artifact with the H29 detector.** Add H7 to `FAMILIES` in
   `run_h29_lookahead_sweep.py` (route `rebuild_collapsed` or `rebuild_pipeline`, collapse
   `"ME"`, grid daily) and re-run the sweep. The expected result is `CAUSAL` (min hold lag +1,
   0 look-ahead bars, a bit-exact rebuild, 0 extra change points) — but the detector, not the
   expectation, decides. **If the committed artifact contradicts the source-classified mechanism,
   report it as a finding.**
4. **Report per family** (H7 only) with the mechanism, the evidence and the artifact id, and
   state explicitly that the H29 sweep's only coverage gap is now closed — or, if it is not,
   exactly why.

## Pre-registration requirements (write the spec BEFORE running)

- A new `HYPOTHESIS_SPEC.md` §H30 with, frozen before the run: the scope, the artifact id that
  the re-run will produce (or the rule that identifies it), the **reconciliation rule** (which
  fields must match the published row and what a mismatch means), the detector leg that will be
  applied, and the **verdict rule** for the reconciliation — e.g.
  `REPRODUCED` iff every published field matches, `NOT_REPRODUCED` otherwise, and
  `CAUSAL` / `LOOKAHEAD` for the timing audit, with `INCONCLUSIVE` for anything that cannot be
  decided.
- The **frozen expectation**: `REPRODUCED` and `CAUSAL` (the source says the collapse is a
  `"ME"` monthly collapse on a daily grid, and the other seven daily families all came out
  `CAUSAL` with a +1 bar hold lag). The rule must be symmetric: a mismatch must be reportable
  as `NOT_REPRODUCED`, and a look-ahead as `LOOKAHEAD`, without any special pleading.
- A **negative control** for the reconciliation: the re-run must be reproducible *by
  construction* — e.g. re-running H7 twice in the same session must produce the same artifact
  values (or, if the runner is not deterministic, that fact must be recorded).

## Constraints

- **Do not** modify the published artifacts, the published runners' logic, any gate, threshold,
  verdict or certified number. Do **not** re-label H7 (or any family) as certified/uncertified in
  the artifacts; H28's `CAUSAL_REJECTED` and H29's `LOOKAHEAD_FOUND` travel with their families.
- **Do not** change the published H7 row in the results table: if the re-run differs, *record*
  the difference in the report and leave the published row as the historical record, with an
  explicit note of the discrepancy.
- Keep everything **offline and deterministic** (the cached futures data is sufficient; no new
  fetch; if the cache misses, **stop and report** rather than fetching).
- Do not re-run any grid (H7 has none; do not re-run H10's 13,824-combo grid either).
- The paid-data task (a wider OOS window for the PF bootstrap margin) stays **downstream** and is
  now unjustified for **every** family in the repo: H28 closed it for the intraday family, and
  H29 shows the daily families are causal but all REJECT.

## Verification (same commands as every session)

`python -m pytest -q`, `python -m pytest -W error -q`,
`python -m pytest --cov=qtr --cov-report=term-missing`,
`python -m ruff check src tests run_*.py`, `python -m ruff format --check src tests run_*.py`,
`bash -n .github/scripts/*.sh`, `bash .github/scripts/test_kilo_progress.sh`.

Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.

## Evidence index

- H29 spec (pre-registration + the pre-execution amendment + the measure log):
  `HYPOTHESIS_SPEC.md` §H29; runner `run_h29_lookahead_sweep.py`; artifacts
  `.experiments/artifacts/h29_lookahead_sweep/`; tests `tests/test_h29_lookahead_sweep.py`
  (36 tests).
- H28 spec + measure log: `HYPOTHESIS_SPEC.md` §H28; runner
  `run_h28_causal_recertification.py`; artifacts
  `.experiments/artifacts/h28_causal_recertification/` + the eight run directories
  (the H10/H22/H25/H21 control/causal exp ids are listed in that `summary.json`).
- H28 tests: `tests/test_h28_causal_recertification.py` (47 tests, incl. the negative controls).
- H27 spec + measure log: `HYPOTHESIS_SPEC.md` §H27; runner `run_h27_pnl_level_audit.py`;
  artifacts `.experiments/artifacts/h27_pnl_level/`; tests
  `tests/test_h27_pnl_level_audit.py` (36 tests).
- H26 (the scale correction that led here): `HYPOTHESIS_SPEC.md` §H26,
  `run_h26_sharpe_scale_audit.py`, `.experiments/artifacts/h26_sharpe_scale/`.
