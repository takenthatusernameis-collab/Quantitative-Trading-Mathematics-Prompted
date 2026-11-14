# HANDOFF — current session (2026-11-14, Cycle 122)

## What changed

**One bounded source-of-truth fix: `scripts/fetch_h182_insider_data.py` no longer
crashes on an unknown `--symbols` entry.**

The previous session's handoff listed only two "next tasks", both blocked
(maintainer-only `.github/workflows/**`; free-data research exhausted). Per the
operating rules (make durable progress; do not passively re-verify), I looked for
an evidenced, agent-actionable defect and found one in the H182 data-acquisition
script.

- **Defect (reproduced before fixing):** `main()` did `cik = UNIVERSE[sym]` inside
  the per-symbol loop, so an unknown symbol (e.g. `--symbols AAPL,TSLA`) raised a
  bare `KeyError: 'TSLA'` *mid-run* — after some caches were written but before
  the manifest was persisted, leaving a silently incomplete corpus and an opaque
  traceback. Repro: partial `AAPL.parquet` written, `manifest.json` absent,
  `KeyError 'TSLA'`.
- **Fix:** added `requested_symbols(raw)` which upper-cases/strips each token and
  validates the *whole* list against `UNIVERSE` before any fetch or cache write;
  unknown symbols raise `SystemExit` with the offending symbols and the known set.
  `main()` now calls it. `src/qtr` untouched.
- **Tests:** `tests/test_fetch_h182_insider_data.py` — 2 new cases:
  `test_unknown_symbol_fails_before_any_fetch_or_cache_write` (0 fetch calls, empty
  cache dir, `SystemExit`) and `test_requested_symbols_normalizes_case_and_whitespace`.

No `src/qtr`, gate, artifact, sidecar, hash, frozen number, or workflow change.

## What was actually verified (own evidence)

- `pytest -q tests/test_fetch_h182_insider_data.py` → **7 passed** (was 5).
- `pytest -q tests/test_sec_insider.py tests/test_nf_20261110_08_insider_signal.py
  tests/test_reproducibility_audit.py tests/test_sidecar_schema_contract.py` → **67 passed**.
- Full pinned suite `pytest -q -W error` (375s) → **3824 passed, 51 skipped, 7 failed**.
  The +2 vs. the prior 3822 is exactly the two new tests; the 7 failures are
  exclusively the maintainer-gated `tests/test_gates_workflow.py` block (unchanged).
- `ruff check src tests run_*.py scripts` → All checks passed.
- `ruff format --check src tests run_*.py scripts` → 335 files already formatted.
- Behavioral proof without network (fetch stubbed): `--symbols " aapl "` resolves and
  writes `manifest.json`; `--symbols AAPL,TSLA` raises `SystemExit: unknown symbol(s):
  TSLA. Known symbols: ...`, `fetch call_count == 0`, cache dir empty.
- `git status` → only `scripts/fetch_h182_insider_data.py` and
  `tests/test_fetch_h182_insider_data.py` modified (54 insertions, 1 deletion).
  No commit made by the agent; `.github/scripts/kilo-controller.sh` stages all but
  `.github/workflows/**` and commits with an empty message.

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials.
   Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182 executed/rejected
   (register Cycles 96/116/118). No honest free-data H183 is pre-registrable.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where
   contract/citation constraints apply.

## Approaches already failed / must not be repeated

- **Do not re-derive a "H182 is missing from the corpus" finding.** It is false
  (174 records; H182 is record 174). Count the corpus directly.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter
  coverage/frozen-contract gates.
- Do not treat delisted/spliced/unavailable free series as PIT-valid.
- Do not mass-edit runners/tests/gates or frozen artifacts to force green.
- Do not append an H182 record to `experiments.jsonl` without sidecars + coordinated
  baseline/pinned-test updates (ratchet fails).
- Do not make speculative `src/qtr` changes absent an evidenced defect.
- Do not change `log_artifact` to always write a sidecar without a coordinated
  `missing_meta_files` baseline + sidecar-schema update (an empty `{}` sidecar for a
  JSON artifact fails the `keys` contract; `test_log_artifact_without_metadata` pins
  the current falsy-metadata branch).

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative if a new evidenced defect is wanted:** the same
`UNIVERSE[...]`-style guard is worth auditing across other `scripts/` and `run_*.py`
entry points that index a dict by a CLI/argument value (a bare `KeyError` after
partial writes). Do **not** invent a free-data H183; do **not** touch the frozen
H182 runner/record.

**Constraints:** preserve gates/contracts/100% `src/qtr` coverage; do not alter
published/frozen artifacts or thresholds except a deliberate authorized
corpus/baseline update; no workflow commit from agent.