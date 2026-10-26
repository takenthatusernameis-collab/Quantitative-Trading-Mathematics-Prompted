# H72 — engine drawdown guard

## What changed

**`src/qtr/backtest/engine.py:520`** — the engine's drawdown denominator now
carries the same zero-guard `validate_strategy` was given in §H71:

```python
drawdown = (equity - rolling_max) / rolling_max.where(rolling_max > 0, 1.0)
```

The engine previously divided by the raw `rolling_max`, so on a strategy that
loses its entire capital on the **first** bar (`equity[0] == 0`,
`rolling_max[0] == 0`) it emitted `max_drawdown = nan`, while
`validate_strategy` reported `0.0` for the same input. The two
implementations disagreed on a series the record actually contains — any
runner that feeds a first-bar total loss.

The guard is a no-op on every curve that starts at positive capital
(`rolling_max` is positive from the first bar and the substitution never
fires), so the published drawdowns are bit-identical: measured identical to
all five committed equity curves.

**`src/qtr/data/fetcher.py`** — consolidated the tz-normalization that was
duplicated in `DataCache.set` and the three fetch cache-hit paths
(`fetch_yahoo`, `fetch_futures`, `fetch_ccxt`) into the cache layer alone
(`DataCache.get`, fetcher.py:92-96). The four per-fetch blocks were dead
code: `get` already strips tz on the way out, so a cached frame is already
tz-naive when the fetch methods see it. Removing them is what restored the
100% coverage gate (the blocks were the only uncovered lines in the module).

## What was verified

- `python -m pytest -q -W error` — **2136 passed, 13 skipped** (was 2130/16
  before this session; the extra 6 are the new tests plus the 3
  `test_generated_manifest_contract` skips that resolved when qtr was
  uninstalled — see handoff notes).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` —
  **100%** on `src/qtr` (was 99.27%).
- `python -m ruff check src tests run_*.py` — all checks passed.
- `python -m ruff format --check src tests run_*.py` — all files formatted.
- Negative control: reverting `engine.py` to the raw denominator makes both
  new tests fail (`nan != 0.0`), so the guard is load-bearing, not cosmetic.
- The fix is bit-identical on all five committed equity curves (measured).

## Remaining unresolved

None for this task. Two environment notes:

1. The coverage gate only reaches 100% because the committed `.cache/data`
   carries 5 tz-aware parquet files (the futures hourly series ES=F, NQ=F,
   CL=F, ZB=F, GC=F). They were written tz-aware by the original runners
   and are read by `DataCache.get`, which strips tz — so the tz-normalization
   in `set` is the only load-bearing guard. If a future session re-runs those
   fetchers and the frames come back tz-naive, `test_cache_set_strips_a_tz_aware_index_before_writing`
   still covers the branch; if the cache files are ever regenerated tz-aware,
   the coverage holds through `get`.

2. `test_generated_manifest_contract` carries 3 skips keyed on "qtr is not
   installed as a distribution" / "no generated manifest in this working
   tree". They pass when qtr is installed (which is how prior sessions ran
   them) and skip cleanly when it is not. The working tree is left with qtr
   **uninstalled** so the suite runs from a bare clone, matching the
   handoff convention.

## Failed approaches

- **Consolidating tz-normalization into the cache layer first, then
  discovering the fetch-hit blocks were already dead.** Verified
  empirically: with the committed cache restored, `get` strips tz on read,
  so the fetch-hit `if getattr(cached.index, "tz", None) is not None:` blocks
  never fired. The consolidation is correct and is what closes coverage; the
  alternative of keeping four dead per-fetch blocks would have left the gate
  at 99.27%.

## Next task

H73 is complete: probed `src/qtr/tracking/experiment.py` and
`src/qtr/utils/config.py` for the H67-H72 defect class (unguarded division /
unordered boundary comparison / degenerate input booked as a number instead of
a sentinel). Both are clean:

- `config._set_nested` already guards non-finite env values
  (`math.isfinite` keeps nan/inf as the original string).
- `experiment.py` has no numeric/division/boundary-comparison surface at all.

No defect was reproduced, so no code change is warranted (no fabricated fix).

Verified this session:
- `python -m pytest -q -W error tests/test_config.py tests/test_experiment_tracker.py` → 35 passed.
- `python -m ruff check src/qtr/tracking/experiment.py src/qtr/utils/config.py tests/test_config.py tests/test_experiment_tracker.py` → passed.
- `python -m ruff format --check` on the same four files → formatted.
- `git status` → clean working tree (HEAD 8e3ce2a). Nothing committed.

Precise next task: run the full verification gates to confirm the package is
green after H67-H73 and that `src/qtr` stays at 100% branch coverage:

    python -m pytest -q -W error
    python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing
    python -m ruff check src tests run_*.py
    python -m ruff format --check src tests run_*.py

(The full suite previously exceeded a 120s sandbox timeout; allow a longer
window.)

Constraints: qtr is left **uninstalled** (bare clone) — do not
`pip install -e .` unless a test requires it, and restore that state if you do.
Do not modify frozen published numbers/gates under `src/qtr` without re-running
pinned contracts (causality / metric agreement / benchmark gate).