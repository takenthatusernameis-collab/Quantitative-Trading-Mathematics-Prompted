# HANDOFF_CURRENT — session complete (H50)

## State

- **H50 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the setuptools-generated metadata directory `src/qtr.egg-info/` is
  **untracked** and ignored, `pyproject.toml` is the only declared source of the package's metadata,
  and the arrangement is pinned by `tests/test_generated_manifest_contract.py` (11 tests). The
  "regenerate and commit" route is closed by measurement: the generated metadata's serialisation
  depends on which setuptools built it.
- **H35–H49 are COMPLETE**: every gate defect class that has surfaced is closed by an executable
  invariant, the point-in-time invariant covers every `run_*.py`, the engine's `total_return` spans
  every bar, the package's two Sharpe implementations agree, the lint/format gate is reproducible,
  the coverage gate is measured, declared and complete, both the package's public API and the
  runners' import surface are declared and pinned, the engine's trade log reconciles with the
  costs it charges, the package's stochastic surface is seedable, and the published validation
  blocks re-derive from the frozen artifacts.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What changed (this session — H50)

- `.gitignore` — `*.egg-info/` added.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`); the files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md` updated.

## The corrected finding

The tracked manifest was stale (61 of 64 entries; the three test modules added between H33 and H49
were missing), and the two earlier sessions' reason for rejecting regeneration was **not quite
right**: building the same tree with the local setuptools 68.1.2 writes `Metadata-Version: 2.1`
with re-spaced, re-quoted requirement markers (`numpy >=1.24.0`,
`yfinance >=0.2.0 ; extra == 'data'`), where the committed file was built under pip's build
isolation as `2.4` (`numpy>=1.24.0`, `yfinance>=0.2.0; extra == "data"`). The `Requires-Dist`
entries are **not dropped** — every base requirement and every extra's requirement is present in
both builds. What is environment-dependent is the **serialisation**, which is enough to make
"regenerate and commit" irreproducible. Untracking is therefore the right fix, and it is now
pinned.

## What was actually verified

- `python -m pytest -q -W error tests/test_generated_manifest_contract.py` → **11 passed**.
- `python -m pytest -q -W error` → **1377 passed, 1 skipped** (full suite, up from 1366).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1054 statements, 320 branches, 0 missed, 0 partial, 100.00%** (unchanged).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **93 files already formatted**.
- **Negative control** — 3 of the 11 contract tests fail against the pre-fix state, every failure
  behavioural.

## What remains unresolved

- The **H47 cost-attribution disclosure** (the `cost` column of the committed trade logs and the
  `avg_trade_cost` of the three exploratory 2026-10-10 summaries) is unchanged: the artifact files
  are frozen and no gate, threshold, verdict or certified number reads them.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict frozen.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted.