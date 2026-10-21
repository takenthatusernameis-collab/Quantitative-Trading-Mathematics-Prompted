# Next Task

## State

H35–H50 complete (the coverage gate is measured, declared and complete at 100% statement +
branch; the package's public API and the runners' import surface are both declared and pinned; the
engine's trade log reconciles with the costs it charges; the package's stochastic surface is
seedable; the published validation blocks re-derive from the frozen artifacts; the package's
metadata has exactly one declared source of truth).
**H50 is complete**: the setuptools-generated metadata directory `src/qtr.egg-info/` is **untracked**
and ignored, `pyproject.toml` is the only declared source of the package's metadata, and the
arrangement is pinned by `tests/test_generated_manifest_contract.py` (11 tests).

## What changed (H50)

- `.gitignore` — `*.egg-info/` added.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`); the files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.

## What was actually verified

- `python -m pytest -q -W error tests/test_generated_manifest_contract.py` → **11 passed**.
- `python -m pytest -q -W error` → **1377 passed, 1 skipped** (full suite, up from 1366).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1054
  statements, 320 branches, 0 missed, 0 partial, 100.00%** (unchanged — nothing under `src/qtr`
  was touched); the committed gate reports *"Required test coverage of 100.0% reached. Total
  coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **93 files already formatted**.
- **Negative control** — the contract run against the **pre-fix** state (the manifest re-added to
  the index with `git add -f`): **3 of the 11 tests fail**, every failure behavioural — the
  detector names the offending paths, `git check-ignore` exits 1 against a tracked path, and the
  "only one declaration" invariant lists the duplicate metadata files.
- The manifest files remain on disk and the editable install still resolves (`import qtr` →
  `src/qtr/__init__.py`); the working tree is clean after `pip install -e .`, where it previously
  was not.

## The corrected finding

The tracked manifest was stale (61 of 64 entries; the three test modules added between H33 and H49
were missing), and the earlier reason for rejecting regeneration was **not quite right**: building
the same tree with the local setuptools 68.1.2 writes `Metadata-Version: 2.1` with re-spaced,
re-quoted requirement markers, where the committed file was built under pip's build isolation as
`2.4`. The `Requires-Dist` entries are **not dropped** — every base requirement and every extra's
requirement is present in both builds; they are reformatted and reordered. What is
environment-dependent is the **serialisation**, which is enough to make "regenerate and commit"
irreproducible. Untracking is therefore the right fix, and it is now pinned.

## What remains unresolved

- **The H47 cost-attribution disclosure covers less than the record does.** §H47 publishes that the
  `cost` column of "the committed trade logs (H10, H11, H16, H21, H22, H25)" carries the pre-fix
  aggregate attribution, and `tests/test_trade_log_cost_reconciliation.py` pins that disclosure for
  **one** artifact (H10). A read-only scan of the repository's committed artifacts
  (`git ls-files ".experiments/artifacts/*/trades.parquet"` → **41** trade logs) shows that
  **every** one of them carries the pre-fix attribution: in each, all trades of a bar record the
  same number (`groupby("timestamp")["cost"].nunique() == 1` holds for all 41). The published list
  is therefore **narrower than the truth**, and the disclosure is pinned for one of them. The
  measured scope, from the same scan:

  | artifact | trades | bars | bars with >1 trade | pre-fix attribution |
  |---|---|---|---|---|
  | `exp_2026-10-10T17-02-22-080026Z` | 257 | 231 | 21 | yes |
  | `exp_2026-10-11T15-53-31-819888Z` | 31,519 | 11,029 | 9,216 | yes |
  | `exp_2026-10-11T17-41-18-169363Z` (H10) | 3,701 | 2,975 | 513 | yes |
  | `exp_2026-10-13T23-27-52-101656Z` | 12,624 | 6,335 | 2,897 | yes |
  | `exp_2026-10-14T07-12-35-292010Z` | 4,980 | 2,695 | 830 | yes |
  | `exp_2026-10-10T17-05-58-697503Z` | 1 | 1 | 0 | n/a (single trade: the attributions coincide) |

  (excerpt; the full set is 41 logs and 80 committed `summary.json` files.)
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected, and the stated reason
  was corrected in H50: setuptools 68.1.2 writes `Metadata-Version: 2.1` with re-spaced, re-quoted
  markers, but it does **not** drop the `Requires-Dist` entries. The real problem is that the
  *serialisation* is a function of the build environment, so "regenerate and commit" cannot be
  reproduced. The manifest was **untracked** instead (§H50).
- **Regenerating the manifest with pip's build isolation** — rejected: the resulting bytes depend
  on whichever setuptools pip resolves, which is the same irreproducibility by another route.
- **A git helper that returns "no result" for any non-zero exit code** — rejected inside H50
  itself: it made `git check-ignore` exiting 1 (nothing matched) a *skip* instead of a failure.
  Only a missing git executable or a checkout without a repository may skip.
- **Fixing the H10 trade-log cost by changing the charge** — rejected: the charge was never wrong.
  The H27 `L3` check proves it (the per-bar cost recomputed from the trade log matches the
  engine's per-bar cost to ~1e-19 for all five audited families). Only the *attribution* inside the
  log was wrong, so the fix moves the log, not the charge.
- **A negative control that only asserted the new API exists** — rejected for the same reason in
  H47/H48: the control must be behavioural, not a missing-keyword error.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- The package's public API (§H45) is pinned by `tests/test_public_api_contract.py`; re-run it
  after any change under `src/qtr`.
- The runners' import surface (§H46) is pinned by `tests/test_runner_import_contract.py`; re-run
  it after any change in a runner or under `src/qtr`.
- The engine's trade-log reconciliation (§H47) is pinned by
  `tests/test_trade_log_cost_reconciliation.py`; re-run it after any change under
  `src/qtr/backtest`.
- The seeded reproducibility of `parameter_sensitivity` (§H48) is pinned by
  `tests/test_parameter_sensitivity_reproducibility.py`; re-run it after any change under
  `src/qtr/validation`.
- The published validation blocks (§H49) are pinned by
  `tests/test_h49_validation_block_disclosure.py`; re-run it after any change under
  `src/qtr/validation`.
- The metadata source of truth (§H50) is pinned by
  `tests/test_generated_manifest_contract.py`; re-run it after any change to `pyproject.toml`,
  `.gitignore` or the packaging layout.
- Re-run `tests/test_runner_causality_inventory.py` and `tests/test_runner_metric_agreement.py`
  after any change in a runner.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.

## The next task (H51)

> **Extend the H47 cost-attribution disclosure from the one artifact it is pinned for to every
> committed trade log, and state which artifacts the pre-fix attribution actually changes.**

**Why.** §H47 discloses that the `cost` column of the committed trade logs carries the pre-fix
aggregate attribution, and lists six families. A read-only scan of the committed artifacts shows
that **all 41** tracked trade logs carry it, and that the disclosure is pinned for only **one** of
them (H10). A disclosure that names six of forty-one affected artifacts and is executable for one
is weaker than the record it describes — the drift is invisible in the other forty.

**The work.**

1. **Measure the scope, read-only.** For every `git ls-files ".experiments/artifacts/*/trades.parquet"`
   log, compute the number of trades, the number of bars, the number of bars holding more than one
   trade, the over-count factor (`sum(cost) / sum(bar totals)`) and whether every trade in a bar
   records the same number. Separate the artifacts where the two attributions **coincide** (no bar
   holds more than one trade) from the ones where they differ.
2. **Publish the corrected scope** in `FINAL_REPORT.md` §H51, replacing the six-family list with the
   measured one, and state the over-count factor per family. The artifacts stay **frozen**; this is
   a disclosure, not a rewrite.
3. **Pin it** with `tests/test_h51_cost_attribution_disclosure.py`: assert the measured scope
   (which artifact is affected, by how much) and assert that the H27 `L3` check still proves the
   *charge* was never wrong for every audited family. A negative control must show that the
   detector distinguishes the affected artifacts from the coinciding ones.

**Constraints.** No artifact may be rewritten; the charge is not in question; the H11 reproduction
check (Sharpe, profit factor, drawdown, trade count, walk-forward stability, worst-regime Sharpe)
is unaffected. If the measurement contradicts the published six-family list, the *list* moves —
not a number.
