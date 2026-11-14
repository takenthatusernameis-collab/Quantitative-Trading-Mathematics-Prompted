# NEXT_TASK.md

## Latest session (2026-11-14, Cycle 119) — reproducibility audit re-verification + H182 lineage reconciliation; no src change

### What changed

- Documentation only: refreshed `REPRODUCIBILITY_AUDIT_REPORT.md` (re-verification banner + H182 lineage reconciliation), `NEXT_TASK.md`, and `HANDOFF_CURRENT_SESSION.md` with this session's own evidence. No `src/qtr`, runner, test, artifact, sidecar, hash, gate, or frozen number modified. No commit/push.

### What was actually verified (own evidence)

- `python -m pytest -q tests/test_reproducibility_audit.py` — **7 passed** (0.22s). Baseline counts unchanged (`missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`); the baseline ratchet held in both directions.
- `python -m pytest -q tests/test_gates_workflow.py` — **7 failed** (expected, unchanged). Contract requires `scripts/**` path triggers, editable install, `ruff ... scripts`, and perf-gate step in `.github/workflows/gates.yml`; fix remains `patches/0001-gates-workflow-contract-fix.patch` (agent-unreachable: `.github/workflows/**` maintainer-managed/restored, no workflow-scoped token).
- `python -m ruff check src tests run_*.py scripts` — **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` — **335 files already formatted**.
- **H182 lineage reconciliation (new finding, read-only):** the H182 experiment (`NF-20261110-08` insider net-buy signal, Cycle 115) is **absent from the reproducibility corpus**. `.experiments/experiments.jsonl` (173 records) contains **0** `insider` records; `EXPERIMENT_LINEAGE_REPORT.md` (173 experiments) cites none. The 5 committed H182 runs live under `.experiments/nf_runs/nf_20261110_08_insider_signal_*/` (all `REJECT`, 3/8 gates; OOS Sharpe 0.421/0.458, PF 1.11, WF 0.42/0.47, worst-regime −0.18/−0.22, IR −1.45/−1.39, p 0.97/0.97, perturbation 1.17/1.10, trades 142/257, maxDD −9.4%) and were never appended to `experiments.jsonl`. This is a lineage-completeness gap, **not** a reproducibility regression: the audit's four baseline counts are unaffected because those artifacts are outside `.experiments/artifacts/` and unrecorded. Documented in `REPRODUCIBILITY_AUDIT_REPORT.md`; closing it requires either appending an H182 record (then `.meta.json` sidecars + re-derived baseline) or registering the nf_runs dir in the audit's corpus scope.

### What remains unresolved

1. **Maintainer-only:** apply `patches/0001-gates-workflow-contract-fix.patch` to `.github/workflows/gates.yml` and push with workflow scope (per patch header / AGENTS.md). Do not attempt to land workflow edits from the agent.
2. **Free-data strategy-family queue exhausted:** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 96/116, H1–H182 are executed/rejected and remaining repo-new mechanisms are data-blocked, underpowered, or mechanism/calendar-adjacent under free/public PIT data. No H183 can be honestly pre-registered without a data-gap resolution.
3. **H182 lineage gap (new):** the Cycle 115 H182 experiment is not in `experiments.jsonl` / `EXPERIMENT_LINEAGE_REPORT.md`. Requires authorization to append or to extend the audit's corpus scope.

### Approaches already tried and why they should not be repeated

- Do not run another discovery-only cycle that re-confirms exhaustion without new data authorization or a §6 shift (Cycles 96 and 116).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT data (OVX, VIX9D, ^RVX; spliced `=F` carry proxy; no free crypto funding history).
- Do not mass-edit runners/tests/gates or frozen artifacts to chase green; the 528 orphans and other reproducibility backlog items are intentionally baseline-frozen where contract/citation/authority constraints apply (`REPRODUCIBILITY_AUDIT_REPORT.md`).
- Do not append an H182 record to `experiments.jsonl` without also generating `.meta.json` sidecars and re-deriving the audit baseline, or the ratchet will fail.

### One precise next task

**Maintainer action (preferred, unblocks CI contract):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then re-run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) and the full pinned gate if desired. **If/when authorized to resume research:** obtain explicit authorization for one paid/PIT data gap (commodity futures per-contract roll/contango term structure, crypto perpetual funding rates, or historical options chain/GEX) and run the smallest decisive pre-registered test for that single mechanism. Do **not** invent a free-data H183 or run another exhaustion-only discovery cycle. Alternatively, authorize closing the H182 lineage gap (append H182 to `experiments.jsonl` + sidecars + baseline re-derivation, or extend the audit's corpus scope to `.experiments/nf_runs/`).

**Constraints:** no gate weakening; no published/frozen artifact, verdict, threshold, or frozen number modified; no commit/push of `.github/workflows/**`; `src/qtr` changes require 100% coverage.

(End of file - total 48 lines)