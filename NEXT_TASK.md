# NEXT TASK — Session 3/3

## Task: Fix H10 prose-grid drift and pin it with a regression test

### Evidence

`run_h10_intraday_tsmom_pfopt_experiment.py:64`:

```python
EXPERIMENT_DESC = (
    "H10: Intraday TSMOM turnover-aware signal + exit grid for profit-factor "
    "optimization; Val-selected, Test-protected, same gates as H9"
)
```

The actual grid (module constants, lines 77-84) is **13,824 combos** across 8
dimensions:

```python
SMOOTH_SPANS          = [None, 4, 8, 16]              # 4
VOL_WINDOWS_LONG      = [252, 504, 1008]              # 3
REGIME_SCALING_FLAGS  = [False, True]                 # 2
MIN_TRADE_INTERVALS   = [0, 4, 8, 24]                 # 4
TRAILING_MULTS        = [1.5, 2.0, 2.5, 3.0]          # 4
MAX_HOLD_BARS         = [60, 120, 240, 480]           # 4
VOL_LIMIT_MULTS       = [1.5, 2.0, 2.5]               # 3
VOL_FLOOR_FRACTIONS   = [0.25, 0.5, 0.75]             # 3
# 4*3*2*4*4*4*3*3 = 13,824
```

`HYPOTHESIS_SPEC.md:881` documents "Full 13,824-combo grid". The prose carries
**no** combo count — the exact defect class fixed eight times already (H22 prose,
H23 prose+spec, H25 prose, H22 pre-registration, H17/H19/H20 prose, and this
session's H16/H18/H21 pins). The string is logged verbatim into
`.experiments/experiments.jsonl` and is the first prose an auditor reads.

### Constraints

- H10 is a **certified PASS edge** (8/8 gates, OOS Sharpe 1.276). Do not
  weaken gates, change selection, or re-run the experiment. This is a
  documentation/pinning task only.
- Follow the exact pattern used this session for H18:
  1. Add module-level `EXPERIMENT_DESC` carrying `"{n}-combo"` and enumerating
     every grid dimension name.
  2. Compute `grid_size` from the constants (don't hardcode).
  3. Add `test_experiment_description_matches_pre_registered_grid` to
     `tests/test_h10_pfopt.py` `TestPreRegistration`, asserting
     `f"{n_combos}-combo" in h10.EXPERIMENT_DESC` and that each dimension name
     appears in the prose.
- Verify with a **negative test**: temporarily strip the combo count from the
  prose, confirm the new test FAILS, then restore and confirm it PASSES.
- Run `python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`; apply formatting if needed.
- Run `python -m pytest -q` (full suite, ~3.5 min) and `python -m pytest -W error -q`.
- Do NOT commit unless explicitly asked.

### Reference: the proven fix pattern (from this session's H18 edit)

```python
EXPERIMENT_NAME = "h18_overnight_intraday"
EXPERIMENT_DESC = (
    "H18: Overnight-vs-intraday equity return decomposition (daily OHLC); "
    "6-combo grid (predictor x hold_convention), Val-selected, "
    "Test-protected, gates per H18 pre-registration"
)
PREDICTORS = ["lagged_1d_overnight_sign", "vix_regime", "prior_5d_return_sign"]
HOLD_CONVENTIONS = ["next_overnight", "next_intraday"]
```

and in `main()`:
```python
"grid_size": len(PREDICTORS) * len(HOLD_CONVENTIONS),
```

and in the test:
```python
def test_experiment_description_matches_pre_registered_grid(self):
    n_combos = (
        len(h10.SMOOTH_SPANS) * len(h10.VOL_WINDOWS_LONG)
        * len(h10.REGIME_SCALING_FLAGS) * len(h10.MIN_TRADE_INTERVALS)
        * len(h10.TRAILING_MULTS) * len(h10.MAX_HOLD_BARS)
        * len(h10.VOL_LIMIT_MULTS) * len(h10.VOL_FLOOR_FRACTIONS)
    )
    assert f"{n_combos}-combo" in h10.EXPERIMENT_DESC
    for dim in ("smooth_span", "vol_window_long", "regime_scaling",
                "min_trade_interval", "trailing_mult", "max_hold_bars",
                "vol_limit_mult", "vol_floor_fraction"):
        assert dim in h10.EXPERIMENT_DESC
```