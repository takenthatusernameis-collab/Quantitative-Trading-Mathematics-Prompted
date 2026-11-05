# NEXT_TASK.md — H88 (NF-20261105-06) execution BLOCKED by CL=F data; re-specify observables

## State
- H88 pre-registered/implemented (`run_nf_20261105_06_gold_oil_rv.py`, `tests/test_nf_20261105_06_gold_oil_rv.py`). Execution attempted 2026-11-05: **BLOCKED, not rejected**.
- Evidence: exp `exp_2026-11-05T12-16-14-717827Z` (`.experiments/experiments.jsonl`, status failed). `DataFetcher._reject_non_positive_prices` refused CL=F: 4 non-positive prices, first `-14.0` on 2020-04-21 (WTI negative-settlement episode). No grid/OOS/gates evaluated; **protected holdout untouched**.
- `src/qtr` unchanged. Focused checks green: `ruff check/format` clean; `pytest tests/test_nf_20261105_06_gold_oil_rv.py -q` → 13 passed.

## Next task (one bounded task)
Make an **explicit, pre-registered re-specification** for H88 observables before any further execution, preserving holdout integrity:

1. **Choose one option and record it** in `HYPOTHESIS_SPEC.md` §H88 and `NEW_FAMILY_RESEARCH_REGISTER.md` (amendment with date/reason):
   - **(a) CL=F trimmed/segmented**: exclude non-positive CL bars (e.g., adjust window/splits so 2020-04 negative episode is not in any priced return base used by engine; disclose exact rule and confirm train/val/test still meaningful and holdout protected).
   - **(b) GLD/USO ETF proxy**: yfinance GLD/USO verified clean 2026-11-05 (4233 rows each, 0 non-positive, 2010-01-01→2026-10-31). Material construction change (ETF basis/costs/tracking vs futures); update universe, cost model, mechanism disclosure, and tests/runner accordingly.
2. Update runner/tests for the chosen option; run focused NF tests + lint/format. If `src/qtr` touched, run pinned full gates: `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (100% required).
3. Only after re-spec is recorded, execute: `PYTHONPATH=src python run_nf_20261105_06_gold_oil_rv.py`. Then record experiment ID, gate counts, OOS metrics, selected config, verdict in spec/register §12/lineage; update handoff.

## Constraints
- Do **not** mark H88 rejected due to this data blocker; blocked ≠ rejected.
- Do **not** use protected-test feedback in re-specification decisions.
- Do **not** modify published artifacts/thresholds/prior verdicts.
- Do **not** silently change the universe/construction without spec/register disclosure.
- NF-20261105-04 (commodity carry, roll-proxy point-in-time risk) and NF-20261105-05 (CS reversal, turnover/net-of-cost risk) remain deferred; revisit only after H88 is resolved or re-spec is infeasible with documented evidence.
