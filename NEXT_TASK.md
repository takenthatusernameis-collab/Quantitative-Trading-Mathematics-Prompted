# NEXT_TASK.md — H88 (NF-20261105-06 gold–oil RV mean reversion) pre-registered/implemented — EXECUTE

Cycle 3 new-family discovery completed (NEW_FAMILY_RESEARCH_REGISTER.md §10–11).
Three repo-new candidates across three mechanism categories were assessed and ranked:
NF-20261105-06 gold–oil relative-value mean reversion (3.95), NF-20261105-04 commodity
carry/roll proxy (3.70, deferred: yfinance point-in-time roll construction risk),
NF-20261105-05 short-term cross-sectional reversal (3.35, deferred: net-of-cost/turnover risk).

Selected: **H88 / NF-20261105-06** (relative value and convergence). Formalized in
HYPOTHESIS_SPEC.md §H88; decision-ready implementation in
`run_nf_20261105_06_gold_oil_rv.py` with focused tests in
`tests/test_nf_20261105_06_gold_oil_rv.py`.

**Verified this session (no `src/qtr` changes):**
- `python -m ruff check src tests run_nf_20261105_06_gold_oil_rv.py tests/test_nf_20261105_06_gold_oil_rv.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 113 files already formatted.
- `PYTHONPATH=src python -m pytest tests/test_nf_20261105_06_gold_oil_rv.py -q` → 13 passed.

**Not executed:** the H88 backtest (requires yfinance network fetch for GC=F/CL=F,
2010–2026, isolated cache; protected holdout). Execution was left as the next bounded task.

## Next task (one task)

Execute H88 and record the outcome:

```bash
cd /home/runner/work/Quantitative-Trading-Mathematics-Prompted/Quantitative-Trading-Mathematics-Prompted
PYTHONPATH=src python run_nf_20261105_06_gold_oil_rv.py
```

Then:
1. Capture experiment ID, gate counts, OOS metrics, selected config, and verdict from the printed summary/artifacts.
2. Update `HYPOTHESIS_SPEC.md` §H88 status/result/verdict (do not alter prior sections).
3. Append §12 outcome to `NEW_FAMILY_RESEARCH_REGISTER.md` with lineage-map row and next candidate decision.
4. Run focused NF tests + lint/format checks; if any `src/qtr` file changed, run pinned full gates:
   `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (must stay 100%).
5. Update `HANDOFF_CURRENT.md`/`NEXT_TASK.md` with evidence. Do not modify published artifacts, thresholds, or prior verdicts.

If execution fails due to data/network: preserve traceback/evidence, mark H88 execution blocked (not rejected), and choose NF-20261105-04 or NF-20261105-05 only after documenting the specific blocker and data feasibility.
