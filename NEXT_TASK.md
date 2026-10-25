# Next task — H73

Hunt the same defect class as H67-H72 in the remaining unguarded surface:
a **zero-information input being booked as a direction**, or an
**unordered-comparison guard / unguarded division** that lets a degenerate
input produce a number instead of a sentinel.

## Where to look

- `src/qtr/tracking/experiment.py` — artifact serialization, summary
  persistence, run-id / timestamp handling.
- `src/qtr/utils/config.py` — config loading, defaults, boundary handling.

## Method (from the H67-H72 record)

1. Read the module and list every guard: every `if`, every division, every
   comparison against a boundary (0, 1e-15, inf, nan).
2. For each guard, ask: *does this compare unordered?* An `x > 0` guard does
   not fire when `x` is `nan` or `inf` — that is the H62/H68/H70 defect
   class, and it has now been found in `sharpe_ratio`, `compare_to_benchmark`,
   `_vol_scale`, and `momentum_signals`.
3. Probe with the smallest reproducing input **before** changing anything.
   Feed the degenerate case at the function's public surface, not through a
   runner, so the test is a unit test rather than an integration fixture.
4. Fix with the smallest reversible change: a sentinel (0.0) on the
   degenerate branch, matching whatever `validate_strategy` or the matching
   implementation already reports, so the two implementations agree.
5. Add a test with a **negative control** that feeds the pre-fix formula and
   requires the corrected result to differ from it — the guard is only
   load-bearing if the two disagree on the input.
6. Verify the change is **bit-identical** on every committed artifact it
   touches, and that no published verdict, gate threshold, or certified
   number moves.
7. Run the full gates before committing:
   ```bash
   python -m pytest -q -W error
   python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing
   python -m ruff check src tests run_*.py
   python -m ruff format --check src tests run_*.py
   ```

## Constraints

- Coverage is enforced at 100% for `src/qtr` (`pyproject.toml`). Every new
  branch must have a test that reaches it.
- The working tree is left with qtr **uninstalled** so the suite runs from a
  bare clone. Do not `pip install -e .` unless a test requires it; if you do,
  restore the state and note it in the handoff.
- Do not commit unless explicitly asked.

## Evidence from this session (H72)

The defect was found by reading `db7aaff`'s diff (a divide-by-zero guard
added to `validate_strategy`'s drawdown at statistics.py:825) and asking
where the **parallel** drawdown in the engine lacked the same guard —
`src/qtr/backtest/engine.py:504`. Probing with `returns = [-1.0] + [0.001]*19`
confirmed `engine.max_drawdown = nan` vs `validate_strategy.max_drawdown = 0.0`.
The fix was one line; the negative control (raw formula emits `nan`) makes it
non-tautological.