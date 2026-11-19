# Next task (2026-11-19, Cycle 216)

## What changed this session
- **H185 (NF-20261119-01, commodity open-interest positioning) was already committed in HEAD
  `29c5ac0`: runner `run_nf_20261119_01_commodity_oi_positioning.py`,
  `tests/test_nf_20261119_01_commodity_oi_positioning.py`, artifact
  `.experiments/nf_runs/nf_20261119_01_commodity_oi_positioning_20261119_cycle216/`
  (summary.json + grid.csv, 72 combos), and `HYPOTHESIS_SPEC.md` H185 section. The session's
  own work **reconciled the durable record to the real execution:**
- **HYPOTHESIS_SPEC.md:** H185 section status `PRE-REGISTERED` → **EXECUTED — REJECT (1/8)**,
  with measured results (selected `oi_growth_63, entry_z=0.5, exit_z=0.0, k=2, vol_target=0.10`;
  OOS Sharpe 0.097, PF 1.020, maxDD −21.54%, trades 1,101, worst regime −2.564; benchmark p
  0.183 / IR −0.712; perturbation 0.353; only trades ≥ 50 passes), gate table, benchmark /
  ablations vs the passive front-month long book (Sharpe 1.004), root-cause attribution, and
  lineage map row updated to REJECT.
- **`tests/test_experiment_artifact_schema.py`:** inventory pins bumped
  `EXPECTED_TOTAL_DIRS 111→112`, `EXPECTED_SUMMARY_COUNT 103→104` (the H185 artifact directory
  was committed without a pin bump; distinct keys unchanged at 139).
- **`AGENTS.md`:** H-range note now reads **H1–H185 exhausted/rejected** (was "H185 unassigned").
- **`NEW_FAMILY_RESEARCH_REGISTER.md`:** new Cycle 216 section recording H185 executed REJECT
  1/8 and the free-data family-discovery-exhausted conclusion.
- **`HANDOFF.md`:** Cycle 216 banner prepended (this session).
- **No change** to `src/qtr`, gates, other artifacts/sidecars/hashes, frozen numbers, or
  `.github/workflows/**`. Artifact-schema pins are now at 112 dirs / 104 summaries / 139 keys.

## H185 result (own evidence, artifact committed at HEAD 29c5ac0)
| Slice | Sharpe | PF | maxDD | trades | worst roll-252 |
|---|---|---|---|---|---|
| OOS Val+Test | **0.097** | 1.020 | −21.54% | 1,101 | −2.564 |
| Val | 0.523 | 1.097 | −4.14% | 340 | −0.229 |
| Test (protected) | −0.087 | 0.983 | −21.54% | 437 | −2.564 |
| Passive front-month long (OOS) | **1.004** | 1.215 | −12.65% | 2,493 | −0.482 |

- Gates PASS only **trades ≥ 50** → **REJECT (1/8)**. FAIL: Sharpe (0.097 < 1.0), PF
  (1.020 < 1.3), maxDD (21.54% > 15%), worst-regime (−2.564 < 0.3), benchmark **p 0.183 /
  IR −0.712**, perturbation **0.353**.
- Train-block collinearity vs H184 slope: oi_growth_21 −0.026, oi_growth_63 +0.014,
  front_share +0.144 → the mechanism argument (quantity vs price-ratio signal) holds, but the
  **edge is absent**: OI positioning predicts nothing after CNY costs; the passive front-month
  book dominates. Null not rejected.

## What was actually verified (own evidence, 2026-11-19)
- `python -m pytest -q tests/test_nf_20261119_01_commodity_oi_positioning.py
  tests/test_experiment_artifact_schema.py` → **120 passed** (after pin bump).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → formatted.
- Determinism: re-ran `python run_nf_20261119_01_commodity_oi_positioning.py --out
  /tmp/h185_repro` → identical `summary.json` fields except `timestamp_utc`/`runtime_sec` and
  byte-identical `grid.csv`.

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials, then
  `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **H1–H185 exhausted/rejected; H186 unassigned with no free-data source pending.** Per
  directive §6 the free-data point-in-time strategy-family queue is exhausted: every executed
  family is rejected, and the remaining candidate classes (options dealer GEX, PIT analyst
  revisions, index reconstitution/splits, relmom/calendar/vol-complex adjacency) are blocked
  or adjacency-recycled with no free PIT history. No further H-ID should be pre-registered
  without a newly authorized data source.
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197,
  hash_mismatches=11, orphaned_files=528, missing_meta_files=0.

## One precise next task
**Maintainer:** `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am
"fix(ci): satisfy gates workflow contract" && git push origin main`, then
`python scripts/verify_gates_workflow_patch.py` (expect `CONTRACT SATISFIED`) and
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).

**Agent:** there is no remaining free-data research task: H1–H185 are all executed and
rejected, the mechanism-distinction argument for the last candidate (H185 OI positioning) was
written in `HYPOTHESIS_SPEC.md` before any outcome and the run confirmed REJECT (1/8), and
the free-data queue is exhausted per directive §6 with named, probed, still-blocked sources.
Do not invent H186, do not recycle H184/H185 parameter/window/universe variants, do not
re-declare probed data sources as blocked. If the maintainer applies the workflow patch, the
session deliverable is complete: verify baseline (`ruff check/format`, focused tests, full
pinned suite with 100% `src/qtr` coverage, `python scripts/backtest_perf_regression_gate.py`)
and leave this handoff. Any future research cycle requires a newly authorized data source
first.

## Approaches already tried and why they should not be repeated
- Do not re-run H184 or H185 or any parameter/universe/window variant (REJECT 2/8 and REJECT
  1/8 are family-level results; the mechanisms failed, not the data).
- Do not classify commodity per-contract roll/contango, crypto funding rates, or breakeven
  inflation as data-blocked (Cycle 214 probe 4/4 usable; FRED and binance archives also
  usable where stated).
- Do not re-probe CHRIS/CME/Yahoo/stooq/LME/DCE as "maybe free" (all probed and blocked).
- Do not treat parameter/timeframe/universe/indicator variations as new families.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py`.
- Do not trust handoff counts — re-run the gates.

## HEAD
- `29c5ac0` (contains H185 runner, test, artifact, and HYPOTHESIS_SPEC.md H185 section). This
  session reconciles the durable record to that committed execution and bumps the artifact
  schema pins; the controller checkpoints it with `.github/workflows/**` excluded from staging.
