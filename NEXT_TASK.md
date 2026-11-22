# Next Task

## Where to resume

Cycle 255 (2026-11-22). `src/qtr`, all runners, tests, and every completed NF experiment
(`.experiments/nf_runs/nf_*`) are complete and preserved unchanged. **Cycle 255 produced a durable
inventory-correctness fix plus a free-data source probe** (no new strategy family, no new H-ID):

- new `scripts/verify_hypothesis_inventory.py` (read-only, stdlib-only, offline) and
  `tests/test_verify_hypothesis_inventory.py` (**13 passed**) enforce the invariant that the
  `<!-- inventory-high-water-mark: H<N> -->` marker in `AGENTS.md` equals the highest `## H<N>` section
  heading in `HYPOTHESIS_SPEC.md` (currently H197). This prevents the recurring stale-inventory defect
  (Cycle 251→252 false "never executed" claims; `AGENTS.md` "H1–H196" vs executed H197).
- `AGENTS.md` now carries the authoritative marker/note and the stale "H1–H196" prose is corrected to
  "H1–H197".
- No artifact, gate, verdict, threshold, frozen number, or `src/qtr` line was touched.

## Cycle 255 (2026-11-22) — inventory high-water-mark invariant + S&P 500 index-membership source probe

- **Why.** Cycle 254 closed with a maintainer-only handoff and no agent-executable research task. Per
  the reliability rules, rather than repeat the "discovery scan → exhausted" approach that already
  failed in Cycles 96/116/251, this cycle fixes a concrete, evidence-backed defect that has repeatedly
  cost cycles: stale research-inventory claims drifting from the committed record.
- **Invariant (durable, executable).** `scripts/verify_hypothesis_inventory.py` + `tests/` assert
  `recorded_high_water_mark(AGENTS.md) == max_documented_h_id(HYPOTHESIS_SPEC.md)`. Run
  `python scripts/verify_hypothesis_inventory.py` → **IN SYNC (H197 == H197)**. When you execute a new
  hypothesis, bump the `AGENTS.md` marker and the spec together or this test fails.
- **§6 free-data probe (no H-ID executed).** The deferred S&P 500 index inclusion/deletion mechanism
  (NF-18 / NF-20261109-18, deferred on "external calendar dependency") was probed for the first time.
  Free PIT **event** data exists (Wikipedia "Historical components of the S&P 500" / "List of S&P 500
  companies" selected-changes table; third-party mirrors list "411 changes since 1976"). This refutes
  the "external calendar" blocker. The **remaining, unprobed** blocker is the **price leg**: removed
  names are frequently delisted and yfinance does not reliably serve delisted tickers; the sandbox
  Python has no direct network (web tools only), so the price leg was NOT probed. Honest status:
  mechanism is event-data-feasible, price-data-unresolved. No H198 fabricated.

## Verified this session (Cycle 255)

- **Full suite: `python -m pytest -q` → 4764 passed / 51 skipped / 7 failed.** The 7 are the
  pre-existing, agent-unreachable `tests/test_gates_workflow.py` failures (unchanged from Cycles
  250–254). Net +13 passing tests (4751→4764) from the new inventory suite.
- **`ruff check` + `ruff format --check` clean** on `src tests run_*.py scripts` (380 files formatted).
- **New suite: `tests/test_verify_hypothesis_inventory.py` → 13 passed.**
- **Coverage:** `src/qtr` untouched → the 100% source/branch coverage gate is unaffected.
- **Offline / dependency-free:** the verifier uses only the standard library and reads committed docs.

## Unresolved work (maintainer / authorization only — NOT agent-executable)

1. **Workflow contract patch (agent-unreachable, maintainer action).** `origin/main:.github/workflows/gates.yml`
   is intentionally unpatched; 7 tests in `tests/test_gates_workflow.py` expect `-W error`, explicit
   `--cov=qtr`, `--cov-branch`, `scripts/**` in ruff targets and path triggers,
   `python -m pip install -e . --no-deps`, and `python scripts/backtest_perf_regression_gate.py`.
   Agent edits to `.github/workflows/**` are discarded by `.github/scripts/kilo-controller.sh` (restore
   from `origin/main` + staging exclude) and the repo token lacks `workflows` permission.
   **Apply-ready fix: `patches/0001-gates-workflow-contract-fix.patch`** (gates.yml only), still guarded
   green by `scripts/verify_gates_workflow_patch.py`
   (`pytest tests/test_verify_gates_workflow_patch.py` → 15 passed). Apply on `origin/main`:
   `git apply --check patches/0001-gates-workflow-contract-fix.patch && git apply
   patches/0001-gates-workflow-contract-fix.patch`. Do **not** retry an in-tree workflow edit.
2. **Universe/benchmark decision (the actual research bottleneck).** Cycle 254 showed that escaping the
   REJECT streak requires a higher-dispersion universe (or formally closing the equity cross-section
   program). This is out of agent scope per directive §2. Authorize a mid/small-cap or ex-US PIT
   universe, or close the program.
3. **Authorization-gated reproducibility artifact cleanup (non-blocking).**
   `REPRODUCIBILITY_AUDIT_REPORT.md` #6 (11 artifact hash_mismatches, 24h) and #5 (rebuild-excluded
   artifacts, 7d). Safe cleanup would reduce hash_mismatches to 3 (legitimate 24h PIT recutoff
   differences). Requires explicit authorization; do not do without it. The suite is green
   (4764/51/7) without this.

## Precise next task (one bounded task)

The equity-cross-section mechanism space on the 98-name survivorship-biased universe is exhausted
(H187–H197 all REJECT; Cycle 254 quantifies why). Do **not** run another 98-name equity cross-section
and do **not** fabricate H198.

The one genuinely-distinct, never-executed candidate whose "blocked" reason was just refuted is the
**S&P 500 index-membership inclusion/deletion event-drift mechanism** (NF-18 / NF-20261109-18). Its
event calendar is free (Cycle 255). The bounded agent task, **if network access is available**:

1. **Probe the price leg.** Take the free changes list (Wikipedia / tickericons), sample ~20 removed
   tickers (M&A/bankruptcy deletions) and ~20 added tickers, and measure yfinance coverage over the
   event window. Record the coverage fraction as a durable artifact/note.
   - If coverage is adequate (say ≥60% of events have a tradable price series), **pre-register H198**
     (S&P 500 index addition/deletion event drift: long announced additions / short announced deletions
     around the effective date, with a PIT event calendar) in `HYPOTHESIS_SPEC.md`, implement a runner
     reusing the existing engine, and execute with the standard 8 gates. Bump the `AGENTS.md` marker and
     the spec together (the inventory test enforces this).
   - If coverage is inadequate (delisted removed names dominate), record the price-leg data blocker with
     evidence and leave H198 unassigned.
2. If network is unavailable (as in this sandbox), the fallback is the maintainer universe decision
   (item 2 above); do not fabricate a family.

## Approaches already tried and why they failed (do not blindly repeat)

- **"§4 discovery scan → exhausted" cycles (96, 116, 251): ruled out.** Repeating an unchanged scan is
  not a materially different approach; Cycle 255 instead fixed a concrete defect and probed a specific
  deferred source.
- **New equity cross-section on the 98-name survivorship-biased S&P 100 (H187–H197): ALL REJECT.**
  Cycle 254 shows why: no alpha against a strong passive book across the full beta spectrum
  (median train 0.690 → OOS 0.187). There is no further equity cross-section on this universe to run.
- **Re-editing `.github/workflows/gates.yml` in a commit: fails every session** (controller restores it;
  fix not agent-reachable). Capture/verify via `patches/` + `scripts/verify_gates_workflow_patch.py` only.
- **Classifying a candidate "data-blocked" without probing the named source.** FRED (Cycle 140),
  `data.binance.vision` (Cycle 213), Chinese futures SHFE/INE/CZCE/CFFEX (Cycle 214), SEC XBRL (Cycle
  230), and now the S&P 500 membership **event** calendar (Cycle 255, free) all serve data older
  registers declared unavailable. Always probe first; name the source that was probed.
- **Computing returns on the unaligned yfinance grid for a rolling-vol signal.** H195 and H197 both hit
  this. Always calendar-align ffilled closes before `pct_change` (the H191 convention).

## Session verification (2026-11-22)

- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → succeeds.
- `scripts/verify_gates_workflow_patch.py` → patch resolves all 7 violations on live `gates.yml`; maintainer must land it with workflows-scoped credentials.
- `tests/test_gates_workflow.py` → 7 failed (unchanged; expected, agent-unreachable). `tests/test_verify_gates_workflow_patch.py` + `tests/test_verify_hypothesis_inventory.py` → pass.
- `python -m ruff check` + `ruff format --check` on `src tests run_*.py scripts` → clean.
- `python scripts/backtest_perf_regression_gate.py` → PASSED (0.412s, limit 5s).
- Full suite per previous session: 4764 passed / 51 skipped / 7 failed (the 7 are this contract test).

## Commit

This session modified `scripts/verify_hypothesis_inventory.py` (new),
`tests/test_verify_hypothesis_inventory.py` (new), `AGENTS.md` (marker + stale-claim fix),
`NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 255), and this `NEXT_TASK.md`. The maintainer workflow patch
(item 1) is a separate maintainer action on `origin/main`.
## Cycle 256 price-leg probe result (2026-11-22)

Price leg probed via yfinance on 20 removed + 20 added S&P 500 tickers sampled from the Wikipedia
historical-components table. Removed coverage 11/20 = 55% (<60% threshold); added 17/20 = 85%.
Delisted removed names (M&A/bankruptcy deletions) dominate failures. Price leg remains a data blocker;
H198 NOT assigned. Artifact: `.experiments/sp500_price_leg_probe_20261122.md`.

## Cycle 256 closure (2026-11-22)

- Price-leg probe completed and recorded: `.experiments/sp500_price_leg_probe_20261122.md`.
- Removed (deletion) coverage 11/20 = 55% < 60% threshold → H198 NOT assigned. Event calendar remains free but price leg is a data blocker (delisted removed names dominate).
- No new H-ID, no runner, no artifact beyond the probe note. Inventory marker remains H197.
- Verified: ruff clean; inventory + gates-patch tests 28 passed.

## Cycle 258 baseline verification (2026-11-22)

Confirmed stable and green (modulo the known agent-unreachable contract failures):
- `python -m ruff check src tests run_*.py scripts` → clean.
- `python -m ruff format --check src tests run_*.py scripts` → clean (383 files).
- `python scripts/verify_hypothesis_inventory.py` → **IN SYNC (H197 == H197)**; `tests/test_verify_hypothesis_inventory.py` passes.
- `python scripts/backtest_perf_regression_gate.py` → **PASSED** (0.419s, limit 5s).
- `pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged, all due to unpatched `.github/workflows/gates.yml`; agent-unreachable, maintainer patch in `patches/`).
- Working tree clean; `git status --short` empty; HEAD == origin/main.
- No `src/qtr`, test, runner, artifact, hash, frozen-number, or workflow change this session. No new H-ID, no runner, no research execution.

## Cycle 257 baseline verification (2026-11-22)

Confirmed stable and green (modulo the known agent-unreachable contract failures):
- Full suite: `python -m pytest -q` → **4794 passed / 51 skipped / 7 failed**. All 7 = `tests/test_gates_workflow.py` (workflow contract; agent-unreachable, maintainer patch in `patches/`). Zero new failures vs. Cycle 256.
- `python -m ruff check src tests run_*.py scripts` → clean.
- `python -m ruff format --check src tests run_*.py scripts` → clean (382 files).
- `python scripts/verify_hypothesis_inventory.py` → **IN SYNC (H197 == H197)**; `tests/test_verify_hypothesis_inventory.py` + `tests/test_verify_gates_workflow_patch.py` → pass.
- `python scripts/backtest_perf_regression_gate.py` → PASSED (0.413s, limit 5s).
- `src/qtr` untouched → 100% source/branch coverage gate unaffected.
- Artifact `.experiments/sp500_price_leg_probe_20261122.md` recorded (removed 55% < 60% → H198 not assigned).

## Precise next task (Cycle 257+)

Agent-executable research on the 98-name survivorship-biased universe is exhausted (H187–H197 all REJECT; S&P 500 index-membership price leg blocked at 55% removed coverage). Do NOT fabricate H198 or run another 98-name equity cross-section.

The next productive work requires maintainer authorization (out of agent scope):
1. Authorize a higher-dispersion universe (mid/small-cap or ex-US PIT) OR formally close the equity cross-section program.
2. Apply `patches/0001-gates-workflow-contract-fix.patch` on origin/main (maintainer-only, workflows-scoped credentials).
3. Optionally authorize reproducibility artifact cleanup (11 hash_mismatches → 3).

Until authorization arrives, the only agent-executable items are durable-infrastructure improvements (inventory invariants, source probes, docs) — not new strategy families. Do not repeat the "discovery scan → exhausted" approach (failed Cycles 96/116/251).

## Cycle 259 (2026-11-22) — durable-infra: FRED probe tests + probe-coverage invariant + unknown-series fix

No new H-ID, no runner, no strategy family, no `src/qtr`/artifact/gate/frozen-number/workflow
change. The `<!-- inventory-high-water-mark: H197 -->` marker is unchanged and still IN SYNC
(`python scripts/verify_hypothesis_inventory.py` → H197 == H197). This cycle closes a concrete,
evidence-backed durable-infra gap (an untested free-data probe) and encodes the invariant that
prevents it recurring.

### What changed
1. **`scripts/probe_fred_availability.py`** — fixed a reproducible `KeyError` crash (1-line).
   `probe()` indexed `FRED_SERIES[series_id]` *before* its `try` block, so an unknown/typo series
   crashed the whole probe even though `main()` prints "warning: ... probing anyway". Reproduced:
   `main(["NOTREAL"])` printed the warning then raised `KeyError 'NOTREAL'`. Now
   `FRED_SERIES.get(series_id, (series_id, "unknown"))` returns a graceful `UNREACHABLE`/unknown row.
   No behaviour change for valid series ids.
2. **`tests/test_probe_fred_availability.py`** (new, 10 tests, fully offline) — closes the last
   untested durable-source probe (FRED is explicitly durable per `AGENTS.md`; 5 of 6 `probe_*.py`
   already had tests, FRED did not). Covers `fetch_fred` CSV parsing (incl. `.`/empty → dropped),
   `probe` OK / UNREACHABLE / unknown-series rows, `main` exit codes (0 all reachable / 1 any
   unreachable), the "probing anyway" warning + no-crash path, default curated-set run, and
   `FRED_SERIES` table well-formedness. Network stubbed via `monkeypatch` on `urlopen`/`fetch_fred`.
3. **`tests/test_probe_script_coverage.py`** (new, 2 tests) — invariant: every `scripts/probe_*.py`
   has a matching `tests/test_probe_*.py`. This is exactly the drift that just happened (a durable
   probe with no test); it now fails at commit time instead of a cycle later.

### What was verified (evidence)
- Full suite: `python -m pytest -q` → **4822 passed / 51 skipped / 7 failed** (was 4810; +12 new
  tests). The 7 are the unchanged, agent-unreachable `tests/test_gates_workflow.py` failures.
- New tests under CI mode: `python -m pytest -q -W error tests/test_probe_fred_availability.py
  tests/test_probe_script_coverage.py` → **12 passed**.
- `python -m ruff check` + `ruff format --check` on the 3 changed files → clean.
- `python scripts/verify_hypothesis_inventory.py` → IN SYNC (H197 == H197).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → applies cleanly;
  `python scripts/verify_gates_workflow_patch.py` → resolves all 7 violations.
- `python scripts/backtest_perf_regression_gate.py` → PASSED (0.424s, limit 5s).
- `src/qtr` untouched → 100% source/branch coverage gate unaffected.

### Not committed (this session)
Per repo policy these changes are left in the working tree (not committed). `git status`:
`M scripts/probe_fred_availability.py`, `?? tests/test_probe_fred_availability.py`,
`?? tests/test_probe_script_coverage.py`, plus this `NEXT_TASK.md`. To land:
`git add scripts/probe_fred_availability.py tests/test_probe_fred_availability.py
tests/test_probe_script_coverage.py NEXT_TASK.md && git commit -m "test(probes): cover FRED probe;
fix unknown-series KeyError; enforce probe-test coverage invariant"`.

### Unresolved (unchanged bottleneck — maintainer / authorization only, out of agent scope)
1. **Universe/benchmark decision (the real research bottleneck).** Authorize a higher-dispersion
   universe (mid/small-cap or ex-US PIT) OR formally close the equity cross-section program.
2. **Workflow contract patch.** Apply `patches/0001-gates-workflow-contract-fix.patch` on
   `origin/main` (maintainer-only, workflows-scoped credentials). Do NOT re-edit
   `.github/workflows/gates.yml` in a commit — it is restored from `origin/main`.
3. **Reproducibility artifact cleanup (non-blocking).** Optional, needs explicit authorization.

### Remaining agent-executable durable-infra gap (lower priority)
`scripts/repair_sidecar_schemas.py` still has **no dedicated test** (only a stale
`tests/__pycache__/test_sidecar_schema_contract...pyc`; the source `tests/test_sidecar_schema_contract.py`
tests the schema contract, not this repair script). It is a one-off, idempotent repair (already
applied; now a no-op), so testing it is lower value than the FRED probe was — do it only if more
durable-infra work is explicitly wanted.

## Precise next task (Cycle 259+) — supersedes the Cycle 257+ note above

The agent-executable research track is exhausted (H187–H197 REJECT; S&P 500 price leg blocked at
55% removed coverage). Do NOT fabricate H198, do NOT run another 98-name equity cross-section, do
NOT re-edit `.github/workflows/**`, and do NOT repeat the "discovery scan → exhausted" approach
(failed Cycles 96/116/251).

The one remaining bounded, agent-executable durable-infra task (only if explicitly wanted, since the
FRED gap is now closed) is to add a test for `scripts/repair_sidecar_schemas.py` using a temporary
experiments directory (it reads `.experiments/experiments.jsonl` and rewrites only disagreeing
`.meta.json` sidecars; assert idempotency and that matching sidecars are left untouched). Otherwise,
the next productive work requires the maintainer authorization in "Unresolved" above.
