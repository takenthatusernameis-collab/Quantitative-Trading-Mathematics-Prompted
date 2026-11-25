# Next Task

## AUTHORITATIVE STATUS — Cycle 308 (2026-11-25): loop terminated by consolidating this handoff; no agent-executable code/research task exists; sole remaining red is maintainer-only

**Read this block only. Everything the previous ~30 cycles recorded is consolidated here; the
redundant per-cycle blocks (Cycles ~257–307) have been removed because re-appending them was the
repeated-failure loop that reliability rule 2 forbids.**

### What changed this session
- **No `src/qtr`, test, runner, `.experiments` artifact, gate, frozen number, H-ID, or inventory
  marker change.** The only file changed is this handoff (`NEXT_TASK.md`), consolidated from 2294
  lines of ~30 near-identical "verified, nothing to do" blocks into this single authoritative block.
  This is a handoff, **not** code/project progress, and is left uncommitted per the
  no-commit-without-explicit-request policy (the controller commits it with an empty message).
- **Genuine finding recorded (not make-work):** ran
  `scripts/analyze_equity_cross_section_rejects.py` (read-only, stdlib-only, tested by
  `tests/test_analyze_equity_cross_section_rejects.py` → 29 passed). It decomposes all 11 equity
  cross-section runs (H187–H199) and shows the REJECT streak is **genuine mechanism weakness, not a
  benchmark-construction artifact**: exposure spans the beta spectrum (3 long-biased / 7
  market-neutral / 1 short-biased), 11/11 runs have negative information ratio, and the passive
  equal-weight book's median OOS Sharpe (1.075) dominates the anomalies' median (0.187). This is the
  durable evidence a maintainer needs to decide between "authorize a new universe" and "close the
  program" — do not re-derive it.

### What I actually verified (fresh evidence, 2026-11-25, deps already installed)
- `scripts/verify_hypothesis_inventory.py` → **IN SYNC** (recorded high-water mark H199 == README H199).
- `scripts/backtest_perf_regression_gate.py` → **PASSED** (0.427 s / 5 s limit).
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` → **397 files already formatted**.
- `pytest -q tests/test_gates_workflow.py` → **exactly 7 failed** (all maintainer-gated `gates.yml`
  gaps: missing `scripts/**` path triggers, `pip install -e . --no-deps`, `scripts` ruff targets,
  perf-gate step). No other red.
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **applies cleanly**;
  `scripts/verify_gates_workflow_patch.py` → **PATCH VERIFIED** (resolves all 7 violations).
- Coverage/verify guards green: `test_verify_gates_workflow_patch`, `test_script_test_coverage`,
  `test_probe_script_coverage`, `test_nf_runner_test_coverage` → 23 passed;
  `test_analyze_equity_cross_section_rejects` → 29 passed.
- Working tree clean apart from this block; HEAD == origin/main (`98c7241`).

### Unresolved (maintainer / authorization only — out of agent scope)
1. **Workflow contract patch — the sole remaining red (7 `tests/test_gates_workflow.py` failures).**
   `.github/workflows/**` is genuinely agent-unreachable: `.github/scripts/kilo-controller.sh:307-340`
   restores it from `origin/main` after every session and excludes it from staging, and the repo
   GitHub App token has no `workflows` scope. A maintainer with `workflows`-scoped creds runs:
   `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.
   Do NOT re-edit `gates.yml` in a commit (it will not persist); do NOT weaken the contract test.
2. **Equity cross-section program closure / new universe.** H1–H199 exhausted/rejected; the reject
   is genuine mechanism weakness (see finding above). A new H200 needs a genuinely-distinct mechanism
   on a *new* universe (directive §2) — not another 98-name / broad-universe cross-section.
3. **Reproducibility artifact cleanup (non-blocking).** 25 unrecoverable missing rows + 356 orphaned
   files are **committed** (`.cache/` is tracked; 82 parquet files; `.gitignore` line 25 keeps them
   for reproducibility). Deletion/move is destructive and needs explicit authorization.

### Approaches already failed — do NOT repeat
- Re-running the fast invariants or the 750 s baseline **as the deliverable** (Cycles ~257–307) —
  adds no information; the state is unchanged.
- Appending another "verified, nothing to do" block / adding another guard test / reconciling a doc
  (Cycles ~274–307) — make-work; this consolidation replaces that loop.
- Fabricating H200 or running another equity cross-section / discovery scan — program complete
  through H199; the passive equal-weight long book (+0.462 OOS Sharpe) dominates every tested
  mechanism.
- Editing `.github/workflows/**` in a commit — controller restores it; token lacks `workflows` scope.
- Chasing the `src/qtr` audit candidates (cost-attribution timing, negative-equity drawdown,
  beta ddof, market-impact NaN, `QTR_CACHE_DIR` fallback) as "bugs" — verified to be documented
  conventions / false positives / frozen numerical core.

### Precise next task
No bounded, agent-executable *research* or *code* task remains that is not frozen, make-work, or
authorization-gated. The single highest-value action is **maintainer-only**: apply
`patches/0001-gates-workflow-contract-fix.patch` to `.github/workflows/gates.yml` on `origin/main`
to clear the 7 `tests/test_gates_workflow.py` failures (re-proven this session: applies cleanly,
resolves all 7). Any further agent work requires one of the three maintainer authorizations above.
If deps are missing in a reset env, run `pip install -r requirements.txt` before any verification.
Do NOT re-run the 750 s baseline, do NOT add more guards, do NOT fabricate H200 — that loop is closed.