# HANDOFF — Session 14 (Kilo)

## What changed

Committed `15cf94f`: made the 18 shebang-carrying `run_*.py` scripts
executable, clearing the last large ruff class (EXE001).

- `chmod +x` on the 18 scripts below. `run_h23_crypto_futures_tsmom.py` was
  already executable; the remaining 18 were the open EXE001 sites. The
  shebangs (`#!/usr/bin/env python3`) are intentional and byte-identical;
  only the file mode changed (100644 -> 100755, 0 insertions/0 deletions).
  Scripts are still invoked via `python run_*.py` per repo convention.
- Files: run_alternatives.py, run_baseline.py, run_cs_momentum_experiment.py,
  run_ddcv_experiment.py, run_experiment.py, run_futures_tsmom_experiment.py,
  run_h10_intraday_tsmom_pfopt_experiment.py, run_h11_robustness_experiment.py,
  run_h12_selection_bias_audit.py, run_h13_oos_deflation_pf_audit.py,
  run_h14_pf_margin_selection_audit.py, run_h6_vix_ddcv_experiment.py,
  run_h7_intraday_tsmom_experiment.py, run_h8_rolladjusted_tsmom_experiment.py,
  run_h9_intraday_tsmom_experiment.py, run_param_sweep.py,
  run_regime_gated_momentum_experiment.py, run_ts_momentum_experiment.py.

## What was verified

- `python -m ruff check run_*.py` -> 8 errors (was 26; 18 EXE001 cleared).
  Remaining: 4 RUF046, 2 SIM102, 2 PERF102 — all style-only, deliberately
  left untouched (see below).
- `python -m ruff check src tests` -> All checks passed.
- `python -m py_compile run_*.py` -> all 27 scripts byte-compile.
- `python run_baseline.py --help` -> smoke test runs to completion
  (buy_and_hold_baseline_v1, Sharpe 0.685).
- `python -m pytest -q` -> 359 passed in 203 s.

## What remains unresolved

`ruff check run_*.py` still reports 8 style-only errors. Two are genuinely
safe one-line fixes (4 RUF046); two are intentional trade guards (2 SIM102);
two are dict-iteration (2 PERF102) where the auto-fix is unsafe for one and
debatable for the other. See `HANDOFF_NEXT.md` for the precise next task.

## Approaches already tried and why

- `chmod +x` (this session): zero-risk, mode-only change, verified by ruff +
  smoke test + pytest. The correct fix for EXE001; nothing else was needed.
- Line-number-based bulk edits (prior session): caused two real bugs
  (deleted an `else` branch in run_regime_gated_momentum_experiment.py;
  dropped the skew/kurt computation in run_h14). Lesson: content-based
  edits with verification beats blind line-based edits. Not repeated.
- `ruff --fix --unsafe-fixes` on the full rule set: unsafe for PERF102 and
  SIM102 (would change runtime behavior). Used only for safe I001 import
  sort in prior sessions.

## Next task (precise)

**Clean the 4 RUF046 sites — the only remaining zero-risk ruff class.**

Each is `int(round(value))` where `round()` already returns `int` in
Python 3, so the `int()` wrapper is provably redundant. Removing it is a
one-token, semantics-preserving edit. Sites:

- run_h11_robustness_experiment.py:112  `return int(round(value))`
- run_h16_factor_timing_experiment.py:366   `v = int(round(base * factor))`
- run_h17_vrp_experiment.py:286              `v = max(1, int(round(v)))`
- run_h23_crypto_futures_tsmom.py:374        `vw = int(round(v))`

Verify with `ruff check run_*.py` (expect 4 errors: 2 SIM102, 2 PERF102),
re-run `pytest -q` (359/359) and `ruff check src tests`, then commit.

Constraints:
- Do not touch `src/` or `tests/` — clean and must stay clean.
- Do not auto-fix SIM102 or PERF102: SIM102 sites are intentional trade
  guards (`elif in_pos and cur_tgt <= 0:` / `if can_trade:`) and PERF102
  line 223 uses `sp` inside the body, so `values()` is unsafe there.
- The two remaining classes are a deliberate, evidence-based stopping point;
  do not expand scope beyond RUF046 without new evidence.