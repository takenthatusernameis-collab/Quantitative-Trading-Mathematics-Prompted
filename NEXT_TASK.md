# Next task (2026-11-20, Cycle 235 — complete)

## State

H1–H190 exhausted/rejected or data-blocked (H187 REJECT 2/8, H188 REJECT 3/8, H189
data-blocked on SEC XBRL gross profitability: 28/29 of 100 names, below 40 minimum;
H190 crypto perpetual funding/basis cross-section REJECT 1/8, Cycle 235).
The free-data point-in-time strategy-family queue is exhausted.

## Verified evidence (this session)

- `run_nf_20261120_04_crypto_funding_carry.py` executed: artifact
  `.experiments/nf_runs/nf_20261120_04_crypto_funding_carry_20261120_101548/`,
  verdict **REJECT (1/8 gates)**, runtime 450.3 s.
  Selected: feature=funding_annualized, entry_z=0.5, exit_z=0.0, k=3, vol_target=0.10;
  WF train Sharpe 0.769; OOS Sharpe 0.039, PF 1.007, maxDD −19.57%, trades 3,530,
  worst-regime −0.617, benchmark p 0.551, IR −0.349, perturbation min ratio −18.02.
- `tests/test_nf_20261120_04_crypto_funding_carry.py` exists (17 tests).
- `NEW_FAMILY_RESEARCH_REGISTER.md`: Cycle 235 entry added (H190 REJECT 1/8).
- `AGENTS.md`: H-range claim updated to H1–H190 exhausted/rejected.
- `HYPOTHESIS_SPEC.md`: H190 execution result section added (Cycle 235).
- `tests/test_experiment_artifact_schema.py`: EXPECTED_DISTINCT_KEYS corrected 152→150
  (H190 adds 1 nested top-level key `train_input_collinearity`, not 3 separate keys).
- `python -m ruff check src tests run_*.py scripts` → clean.

## One precise next task

**No further family-discovery execution remains.** The free-data PIT queue (H1–H190 on
SEC XBRL fundamentals, Binance crypto funding/basis, commodity term-structure/hedging
pressure/OI positioning) is exhausted. The next session should:

1. Run the full test suite (`python -m pytest -q`) and lint (`python -m ruff check src tests run_*.py scripts`) to confirm green.
2. Record in `NEXT_TASK.md` that the session is complete — no new runner, no new H-ID.
3. Optionally pursue auditing/infrastructure work (e.g., reproducibility restoration,
   artifact audit follow-ups) rather than new family discovery.

## Approaches already tried / do not repeat

- Do not re-declare any H-ID family as data-blocked without naming the probed source.
- Do not treat parameter/timeframe/universe/market variants of H1–H190 as new families.
- Do not modify `.github/workflows/**` (maintainer-managed; agent-unreachable).
- Do not re-run H190 as a variant; the full-window pre-registered run is the record.

## Blocked items (cannot be resolved by this agent)

- `tests/test_gates_workflow.py` is red on `origin/main` (7 failed). Fix is
  `patches/0001-gates-workflow-contract-fix.patch`, but `.github/workflows/**` is
  maintainer-managed and agent-unreachable (no `workflows` GitHub App permission;
  `.github/scripts/kilo-controller.sh` restores workflows from origin/main after each
  session). Recorded for maintainer action; do not attempt in-tree workflow edits.
