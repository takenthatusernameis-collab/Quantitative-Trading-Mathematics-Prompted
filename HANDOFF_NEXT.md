# HANDOFF_NEXT — Cycle 38 discovery complete; H124 pre-registered

Cycle 38 discovery executed: lineage reconciled to H123 (REJECT 5/8). Three repo-new candidates proposed across distinct categories (MAX/lottery, cross-asset vol, IVOL spread). Deferred candidates reassessed with no silent drops. H124 pre-registered for NF-20261107-09 (cross-sectional MAX/lottery-demand timing on SPY). src/qtr unchanged.

Next task: Implement runner `run_nf_20261107_09_max_lottery.py` + focused tests `tests/test_nf_20261107_09_max_lottery.py` modeled on H123 runner; verify data (fixed liquid stock universe via yfinance); ruff clean; execute; record verdict (OOS Val+Test only). Do not weaken gates or modify published/certified artifacts.
