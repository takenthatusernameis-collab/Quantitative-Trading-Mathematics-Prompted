# H75 — a vendor panel that omits a required column crashed the fetch

## What changed

`src/qtr/data/fetcher.py` — a real defect in both `fetch_yahoo` and `fetch_futures`:
the column selection was `df[required + extras]` with `required = ["open", "high",
"low", "close", "volume"]` built as a **literal** list, so a vendor panel that omitted
`volume` (or any other required column) raised `KeyError` *inside* the per-symbol fetch
loop, where the broad `except Exception` swallowed it, logged `Failed to fetch`, and
returned the symbol as an **empty frame** — a silent void of the class the H53–H61
audits exist to catch. The selection is now built from the columns actually present
(`present = [col for col in required if col in df.columns]`, then `df[present +
extras]`), which is bit-identical for a complete panel and degrades gracefully for an
incomplete one. The existing `Missing column` warning still fires for each gap.

`tests/test_data_fetcher.py` — **7 tests added** (49, was 42), including two that
re-pinned the corrected behaviour of the pre-existing missing-column tests and a
behavioural negative control that reconstructs the pre-fix literal-list selection and
requires it to raise `KeyError`.

## What was verified (this session)

- Full suite `python -m pytest -q -W error` → **2143 passed, 16 skipped** (was 2135;
  the 16 skips are all intentional and self-declaring).
- Coverage `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` →
  `src/qtr` **1142 stmts / 364 branches / 0 missed / 0 partial / 100.00%**.
- `ruff check src tests run_*.py` → *All checks passed!*; `ruff format --check` →
  **104 files already formatted**.
- Clean venv with only `pip install -r requirements.txt` (unchanged `requirements.txt`,
  re-verified as a regression check): `tests/test_data_fetcher.py`,
  `tests/test_public_api_contract.py`, `tests/test_runner_import_contract.py` →
  **149 passed**.
- New tests fail on the pre-fix source (reverted `fetcher.py`) and pass with the fix.
- `FINAL_REPORT.md` — new **§H75** section.

## Remaining unresolved

- All remaining items in `FINAL_REPORT.md` §H53–§H61 remain **disclosed, not
  quantified** — each depends on an input the record does not hold. None can be
  resolved without new committed inputs; none affect gates.
- No published artifact, gate threshold, verdict or certified number was modified; no
  grid was re-run; the H1–H30 hypothesis space remains exhausted.

## Failed approaches

- **Treating the swallowed-exception path as the fetcher's "no data" contract.**
  Rejected after measurement: the two pre-existing tests asserted `res[symbol].empty`
  for a panel missing every required column, which pinned the *symptom* (an empty
  frame) rather than the cause (a swallowed `KeyError`). The fetcher's own contract
  says an empty frame means "no data"; here it meant "the fetch crashed and the crash
  was swallowed", and the two are indistinguishable to every caller. The corrected
  behaviour returns the panel over the columns the vendor actually carried, and the
  two pre-existing tests were re-pinned to that.
- **Fixing only `fetch_yahoo`.** Rejected: `fetch_futures` carries the identical
  literal-list selection, so the defect is present in both and both were fixed.

## Next task

**None assigned.** Baseline is green and stable, verified from a bare-clone
environment as well as from the system runner.

Constraints that carry forward:
- No published artifact, gate threshold, verdict or certified number may be
  modified. No grid may be re-run. The H1–H30 hypothesis space remains exhausted.
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
  signal / generated manifest / runner import contract / data fetcher) and
  confirm `src/qtr` stays at 100% coverage with gates green.