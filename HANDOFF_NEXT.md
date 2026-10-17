# Agent Handoff — For the next agent

## State you are inheriting

The repo is at **HEAD `15cf94f`** (this session's EXE001 fix), preceded by
`21b0d25` (handoff housekeeping), `68fdf8d` (F-rule ruff sweep), and earlier
the CI telemetry fix `893e276`. The baseline is **359/359 tests** and
`ruff check src tests` is clean.

## What this session did

Executed the assigned task from `NEXT_TASK.md`: cleared the 18 `EXE001` ruff
errors by making the shebang-carrying `run_*.py` scripts executable.

- `chmod +x` on 18 scripts (run_h23 was already executable). Mode-only
  change: 100644 -> 100755, 0 insertions, 0 deletions. Shebangs unchanged.
- Verified: `ruff check run_*.py` 26 -> 8 errors; `ruff check src tests` clean;
  `py_compile` clean; `run_baseline.py --help` smoke test passes;
  `pytest -q` 359 passed in 203 s.
- Committed as `15cf94f` with a body documenting the verification.

Two runtime-artifact cleanups were needed: the pre-commit hook ran
`run_alternatives.py` (writing `.experiments/artifacts/exp_.../` and three
`.meta.json` files), and my own `run_baseline.py --help` smoke test wrote
`.experiments/experiments.jsonl` + an artifact dir. Both were reverted so the
commit contains only the mode changes.

## Precise next task (your call)

**Clean the 4 RUF046 sites — the only remaining zero-risk ruff class in
`run_*.py`.**

`int(round(value))` is redundant because `round()` returns `int` in
Python 3 (the project targets >=3.10). Removing the `int()` wrapper is a
one-token, semantics-preserving edit. Sites:

- `run_h11_robustness_experiment.py:112` — `return int(round(value))`
- `run_h16_factor_timing_experiment.py:366` — `v = int(round(base * factor))`
- `run_h17_vrp_experiment.py:286` — `v = max(1, int(round(v)))`
- `run_h23_crypto_futures_tsmom.py:374` — `vw = int(round(v))`

After the edit: `ruff check run_*.py` should report 4 errors (2 SIM102,
2 PERF102), `pytest -q` 359/359, `ruff check src tests` clean. Commit with
a one-line summary + verification body matching repo style.

## Constraints handed down

- Do NOT touch `src/` or `tests/` — clean and must stay clean.
- Do NOT auto-fix the remaining SIM102 or PERF102:
  - SIM102 (run_h10:208, run_h23:211) are intentional trade guards:
    `elif in_pos and cur_tgt <= 0:` / `if can_trade:` — collapsing them
    would drop the `can_trade` gate.
  - PERF102 (run_h11:223, run_h11:403): line 223 uses `sp` inside the
    body, so `values()` is unsafe; line 403 iterates `data.items()` and
    uses `sym`, so the fix is also unsafe. Left as-is deliberately.
- The free-data hypothesis space (H1–H25) is exhausted; no bounded
  free-data experiment remains. The only non-redundant next step requires
  paid hourly futures data (out of free-data scope).
- Commit-per-experiment convention; bytecode is gitignored.
- The CI progress telemetry is driven by the controller
  (`.github/scripts/kilo-controller.sh`); do not edit the helper's
  advertised field names without updating the controller and the audit
  guard together.
- Reconcile remote changes instead of blindly overwriting; verify
  persistence before declaring done.

## Files changed this session (committed as `15cf94f`)
- 18 `run_*.py` scripts — mode 100644 -> 100755 (chmod +x).
- `HANDOFF.md`, `HANDOFF_NEXT.md`, `NEXT_TASK.md` — this session's record.

Run `python -m pytest -q` to confirm the green baseline (359 passed) before
starting. `git status` should be clean.

(End of file)