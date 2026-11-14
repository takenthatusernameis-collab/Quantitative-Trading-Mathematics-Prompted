# NEXT_TASK.md

## Latest session (2026-11-14, Cycle 120) — baseline re-verification; all assigned agent paths confirmed blocked; no src change

### What changed

- No code change this session. Working tree clean at HEAD `957c9eb`. No `src/qtr`, runner, test, artifact, sidecar, hash, gate, or frozen number modified. No commit/push.

### What was actually verified (own evidence)

- `python -m pytest -q tests/test_reproducibility_audit.py tests/test_experiment_lineage_report.py` — **12 passed** (0.24s). Baseline counts unchanged (`missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`); lineage report total pinned at 173 experiments.
- `python -m pytest -q tests/test_gates_workflow.py` — **7 failed** (unchanged, expected maintainer-gated contract drift vs `.github/workflows/gates.yml`); fix remains `patches/0001-gates-workflow-contract-fix.patch` (agent-unreachable: `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` each session; agent has no `workflows`-scoped token).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` — **applies cleanly**; patched `gates.yml` satisfies all 7 assertions.
- `python -m ruff check src tests run_*.py scripts` — **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` — **335 files already formatted**.
- Grep over `src/qtr/` — **no TODO/FIXME/XXX markers**; src clean (11 modules). No evidenced defect.

### What remains unresolved

1. **Maintainer-only:** apply `patches/0001-gates-workflow-contract-fix.patch` to `.github/workflows/gates.yml` and push with workflow scope. Do not attempt to land workflow edits from the agent.
2. **Free-data strategy-family queue exhausted:** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 96/116, H1–H182 are executed/rejected; remaining repo-new mechanisms are data-blocked, underpowered, or mechanism/calendar-adjacent under free/public PIT data. No H183 can be honestly pre-registered without a data-gap resolution.
3. **H182 lineage gap:** the Cycle 115 H182 experiment (`NF-20261110-08` insider net-buy signal) is absent from `experiments.jsonl` / `EXPERIMENT_LINEAGE_REPORT.md`. Requires authorization to append (with `.meta.json` sidecars + baseline re-derivation) or to extend the audit's corpus scope to `.experiments/nf_runs/`; appending would break pinned test counts (total=173, category summary, reproducibility baseline) and is not agent-actionable unilaterally.

### Approaches already tried and why they should not be repeated

- Do not run another discovery-only cycle that re-confirms exhaustion without new data authorization or a §6 shift (Cycles 96 and 116).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not treat delisted/spliced-continuous/unavailable free series as valid PIT data (OVX, VIX9D, ^RVX; spliced `=F` carry proxy; no free crypto funding history).
- Do not mass-edit runners/tests/gates or frozen artifacts to chase green; the 528 orphans and other reproducibility backlog items are intentionally baseline-frozen where contract/citation/authority constraints apply.
- Do not append an H182 record to `experiments.jsonl` without also generating `.meta.json` sidecars and re-deriving the audit baseline, or the ratchet will fail.
- Do not make speculative code changes: `src/qtr` has no evidenced defect (100% coverage, ruff clean, suite green except maintainer-gated block).

### One precise next task

**Maintainer action (preferred, unblocks CI contract):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials, then re-run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed). **If/when authorized to resume research:** obtain explicit authorization for one paid/PIT data gap (commodity futures per-contract roll/contango term structure, crypto perpetual funding rates, or historical options chain/GEX) and run the smallest decisive pre-registered test for that single mechanism. Do **not** invent a free-data H183 or run another exhaustion-only discovery cycle. **Alternatively:** authorize closing the H182 lineage gap (append H182 to `experiments.jsonl` + sidecars + baseline re-derivation, or extend the audit's corpus scope to `.experiments/nf_runs/`), including updating pinned counts in `tests/test_experiment_lineage_report.py` (173 → 174, category summary) and `tests/test_reproducibility_audit.py` baseline as needed.

**Constraints:** no gate weakening; no published/frozen artifact, verdict, threshold, or frozen number modified except via the deliberate corpus update above; no commit/push of `.github/workflows/**`; `src/qtr` changes require 100% coverage.
