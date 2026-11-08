# NEXT_TASK — Cycle 63: H149 pre-registered; implement + execute

## State (post Cycle 62 / H148)
- H148 REJECT 4/8 (see HYPOTHESIS_SPEC.md §H148). Lineage reconciled H85–H148.
- H149 PRE-REGISTERED (NF-20261106-01, GDX-vs-GLD miner gold-beta RV divergence SPY timing). See HYPOTHESIS_SPEC.md §H149.
- No commit/push; src/qtr unchanged.

## Precise next task (Cycle 63)
Implement `run_nf_20261106_01_miner_gold_rv.py` + `tests/test_nf_20261106_01_miner_gold_rv.py` following the H148 standard gated/ablation protocol (walk-forward train-only selection, protected Test, buy-hold/random-exposure/inverse ablations, gates, perturbation). Free/public yfinance data only. Run ruff check/format, focused pytest, execute runner, record verdict + artifact path in HYPOTHESIS_SPEC.md, NEW_FAMILY_RESEARCH_REGISTER.md, NEXT_TASK.md, HANDOFF_NEXT.md. Do not fabricate results; do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers. If src/qtr touched, rerun pinned 100% coverage suite.
