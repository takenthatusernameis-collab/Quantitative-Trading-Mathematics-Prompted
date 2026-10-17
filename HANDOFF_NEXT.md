# Agent Handoff — For the next agent

## State you are inheriting
The repo is at **HEAD `c148694`** (preceded by `9fe88a1` "Remove tracked bytecode
artifacts", `65ea3eb` "Fix post-merge Kilo audit workflow guard (#6)"). Everything
through H25 is committed and verifiable. The baseline is **359/359 tests**.

## What this session did
The prior session's `.pyc` cleanup (commit `9fe88a1`) left the working tree clean.
This session executed the remaining bounded free-data hygiene task from HANDOFF_NEXT.md
§2:

**Repo-root scratch-artifact cleanup (committed as `c148694`).** Inspected all 8
tracked repo-root scratch artifacts before deleting:
- `_t.txt`, `_t2.py`, `_wtest.py`, `_wtest2.py` — 1-3 line `print()` placeholders
- `h23_output.log` — 485 KB runtime experiment log (reproducible from artifacts)
- `run_h23_crypto_futures_tsmom.py.bak` — superseded `.bak` of the H23 script
- `run_h23_test.py` — root-level test superseded by `tests/test_h23_*.py`
- `FINAL_REPORT.md.backup` — pre-H24/H25 report version, superseded

None are referenced by any source, test, or experiment. Verified: **359/359 tests
pass** (no regression), working tree clean, `git ls-files | grep -cE "\.pyc$|__pycache__"` → 0 tracked bytecode.

## Precise next task (your call)
The free-data hypothesis space is **exhausted** (H1–H25, H15 probe). The sole passing
edge family (intraday futures TSMOM: H10/H11/H22/H25) is real but **qualified/CI-fragile**
on the ~730-hour free `=F` window (H25 Robustness audit: PF CI [1.2049, 1.4425],
P(PF≥1.3)=0.6215; Sharpe CI LB dips below 1.0).

**No bounded, verifiable free-data task remains.** The only non-redundant next step
requires paid data (out of free-data scope):

**Acquire paid hourly futures data (NEEDS BUDGET/APPROVAL — out of free-data scope).**
The audit pins the target: the PF CI half-width (±0.120) must shrink ~3-4x for
P(PF≥1.3) ≥ 0.90, which needs ~3-4x more bars (≈2-3 years of hourly `=F`, e.g.
Databento/Polygon/CMC). Re-run H25's pipeline verbatim (`run_h25_futures_tsmom_pfmargin.py`)
on the longer window, then re-run `run_h25_pf_robustness.py`. **Do NOT** run any new
free-data hypothesis — H1-H25 already prove free-data families land at Sharpe 0.2-0.8 /
CI-fragile PF < 1.3.

(Deferred optional hygiene, not part of the critical path: ~466 pre-existing `ruff`
errors repo-wide (`UP006` `Dict`→`dict`, `I001` import sorting, `F401` unused imports)
could be swept in one `ruff --fix` pass, but that risks the pinned 1e-9 artifacts and
needs a full suite re-run afterward.)

## Constraints handed down
- No paid data available in this session (free only); respect the ≤2 CPU-h budget.
- Do NOT weaken gates (PROMPT_V2 §H15): the honest outcome is "qualified pass,
  CI-fragile," not a forced pass.
- Do NOT re-run/repurpose committed H25 artifacts or tests — they're pinned at
  1e-9 (the audit's point estimates reproduce H25 `summary.json` exactly).
- Commit-per-experiment convention; bytecode is gitignored (now enforced).

## Files changed this session (committed as `c148694`)
- Deleted 8 tracked repo-root scratch artifacts (`_t.txt`, `_t2.py`, `_wtest.py`,
  `_wtest2.py`, `h23_output.log`, `run_h23_crypto_futures_tsmom.py.bak`,
  `run_h23_test.py`, `FINAL_REPORT.md.backup`) — 5428 deletions, 0 additions.
- `HANDOFF.md`, `HANDOFF_NEXT.md` — this session's record.

Run `python -m pytest -q` to confirm the green baseline (359 passed) before starting.
`git status` should be clean (no `.pyc` churn).

(End of file)