# H74 — clean-venv verification of the documented quick start

## What changed

No code change. The carried-forward task from `HANDOFF.md` ("run the full
verification gates to confirm the package is green after H67-H73") was executed
**in a fresh venv with only `pip install -r requirements.txt`** — the same
inspection that found the missing `setuptools` (§H63) and `ruff` (§H64)
dependencies in earlier sessions — rather than in the system runner where
apt-installed packages mask the skip list.

The baseline was already green, and it stayed green through the clean-venv run,
so no defect was reproduced and no code change is warranted (no fabricated fix).

## What was verified (this session)

Fresh venv (`/home/runner/work/_temp/kilo-tmp/venv`, Python 3.12.3, only
`pip install -r requirements.txt`):

- Installed versions: `setuptools-84.2.1`, `pyarrow-26.0.0`, `ruff-0.17.2`,
  `pytest-9.1.1`, `pytest-cov-7.1.0`, `coverage-7.17.0`, `numpy-2.5.4`,
  `pandas-3.1.0`, `scipy-1.18.1`, `scikit-learn-1.9.1`, `PyYAML-6.0.3`,
  `python-dotenv-1.2.4`, `loguru-0.7.3`, `yfinance-1.7.0`, `ccxt-4.5.90`.
- `python -m pytest -q -W error` → **2135 passed, 16 skipped** (identical to the
  system-runner baseline; the 16 skips are all intentional and self-declaring).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` →
  **1138 stmts / 364 branches / 0 missed / 0 partial / 100.00%** on `src/qtr`.
- `ruff check src tests run_*.py` → **All checks passed!**
- `ruff format --check src tests run_*.py` → **104 files already formatted**
- Pinned contract subset in the fresh venv
  (`test_public_api_contract`, `test_ruff_reproducibility`,
  `test_coverage_gate_contract`, `test_generated_manifest_contract`) →
  **61 passed, 3 skipped** (the 3 skips are the qtr-not-installed /
  no-manifest skips, which are correct in a bare clone).

## Remaining unresolved

- All remaining items in `FINAL_REPORT.md` §H53–§H61 remain **disclosed, not
  quantified** — each depends on an input the record does not hold. None can
  be resolved without new committed inputs; none affect gates.
- The 3 skips in `test_generated_manifest_contract` are structural, not
  environmental: they pass when qtr is installed and skip cleanly when it is
  not. The working tree is left with qtr **uninstalled** (bare clone), matching
  the handoff convention.
- The coverage gate reaches 100% because the committed `.cache/data` carries
  tz-aware parquet files read by `DataCache.get`, which strips tz. See the
  note in the previous handoff.

## Failed approaches

- **Running the gates only in the system runner.** Rejected: the system runner
  has apt-installed `setuptools` and `ruff`, so its skip list does not reflect
  the documented quick start. The clean-venv run is the only measurement that
  can show whether `requirements.txt` declares everything the suite imports.
  This session's clean-venv run showed the declaration is now complete —
  `setuptools`, `pyarrow` and `ruff` are all in `requirements.txt`, and no
  pinned contract test skips that should not.

## Next task

**None assigned.** Baseline is green and stable, verified from a bare-clone
environment as well as from the system runner.

Constraints that carry forward:
- No published artifact, gate threshold, verdict or certified number may be
  modified. No grid may be re-run. The H1–H30 hypothesis space remains
  exhausted.
- `src/qtr` coverage gate must stay at 100% (statement + branch).
- Ruff lint and format gates must stay clean.
- `requirements.txt` is the contract that must declare every dependency a
  pinned contract test imports; verify it by running the suite from a fresh
  venv with only `pip install -r requirements.txt`.
- qtr is left **uninstalled** (bare clone) — do not `pip install -e .` unless a
  test requires it, and restore that state if you do.
- After any change under `src/qtr` or affecting runners/validation, re-run the
  pinned contracts (causality / metric agreement / benchmark gate / public API
  / ruff reproducibility / coverage gate / trade log reconciliation / tsmom
  signal / generated manifest) and confirm `src/qtr` stays at 100% coverage
  with gates green.