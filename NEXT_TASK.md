# NEXT TASK

**Clean the 4 RUF046 sites — the only remaining zero-risk ruff class in
`run_*.py`.**

`int(round(value))` is redundant because `round()` returns `int` in
Python 3 (the project targets >=3.10). Removing the `int()` wrapper is a
one-token, semantics-preserving edit. Sites:

- `run_h11_robustness_experiment.py:112` — `return int(round(value))`
- `run_h16_factor_timing_experiment.py:366` — `v = int(round(base * factor))`
- `run_h17_vrp_experiment.py:286` — `v = max(1, int(round(v)))`
- `run_h23_crypto_futures_tsmom.py:374` — `vw = int(round(v))`

Verify with `ruff check run_*.py` (expect 4 errors: 2 SIM102, 2 PERF102),
re-run `pytest -q` (359/359) and `ruff check src tests`, then commit.

Constraints:
- Do not touch `src/` or `tests/` — clean and must stay clean.
- Do not auto-fix SIM102 or PERF102:
  - SIM102 (run_h10:208, run_h23:211) are intentional trade guards
    (`elif in_pos and cur_tgt <= 0:` / `if can_trade:`); collapsing them
    would drop the `can_trade` gate.
  - PERF102 (run_h11:223, run_h11:403): line 223 uses `sp` inside the
    body, so `values()` is unsafe; line 403 iterates `data.items()` and
    uses `sym`, so the fix is also unsafe. Both left as-is deliberately.
- The two remaining classes are a deliberate, evidence-based stopping
  point; do not expand scope beyond RUF046 without new evidence.

## Context

Session 14 (commit `15cf94f`) cleared the 18 EXE001 sites by `chmod +x`ing
the shebang-carrying `run_*.py` scripts (mode-only change, 0 insertions).
That left 8 style-only ruff errors: 4 RUF046, 2 SIM102, 2 PERF102. This
task addresses the 4 RUF046 sites — the only class that is both zero-risk
and a genuine redundant cast.

See `HANDOFF.md` for the full session record, including approaches that
already failed (line-number-based bulk edits caused two real bugs; use
content-based edits with verification instead).