# HANDOFF_NEXT — Cycle 35 pre-registration (2026-11-07)

Cycle 35 discovery + pre-registration completed (documentation only; no src/qtr changes, no experiment executed).

State: H85–H120 rejected/recorded; H121 pre-registered = NF-20261107-04 Amihud illiquidity-stress regime timing on SPY. Lint passes.

Next task: Implement runner `run_nf_20261107_04_amihud_illiq.py` + tests `tests/test_nf_20261107_04_amihud_illiq.py`, ruff check/format clean, execute, record verdict (OOS Val+Test). Address trade-sparsity risk; if <200 OOS trades, REJECT on trade gate without rescue. Do not weaken gates or modify src/qtr.
