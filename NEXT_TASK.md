# Next Task

## AUTHORITATIVE STATUS — Cycle 324 (2026-11-26): program CLOSED; both items maintainer-blocked. No agent-executable work.

### Cycle 324 — short handoff (no re-measure; no authorization landed)
HEAD is still the Cycle 323 handoff commit `21c557a`; working tree clean; `origin/main...HEAD` → `0 1`
(local ahead by the unpushed handoff commit only). Cheap re-confirmation (seconds, NOT a suite re-run):
`verify_gates_workflow_patch.py` exit 0 (7 violations, maintainer must land); `verify_hypothesis_inventory.py`
IN SYNC (H201 == H201). No paid/consensus-source or workflows-scope authorization is present in the repo
(grep hits are the handoff docs *describing* the pending authorization, not granting it). The Cycle 321
full-suite evidence (**5029 passed / 51 skipped**, `-W error` gate **344 passed** at baseline `277d49d`)
remains the current ground truth; the code baseline is unchanged since `277d49d`, so re-running the 750 s
suite would be make-work. **No bounded, high-value, non-make-work task is agent-executable.** Do NOT fabricate
H202, re-run the suite, add a guard test, re-probe N-CEN, or re-declare 13F/FINRA/FRED/CBOE/N-CEN blocked.

## AUTHORITATIVE STATUS — Cycle 323 (2026-11-26): program CLOSED; both items maintainer-blocked. No agent-executable work.

### Cycle 323 — new evidence (gap reconciliation, not a re-measure)
HEAD advanced 4 commits past the Cycle 321/322 verified baseline `277d49d`
(`766d633`, `4889b1f`, `b51101f`, `6fa19c7`), which could have masked code drift.
Reconciled cheaply (seconds, NOT a suite re-run): `git diff --stat 277d49d..HEAD` shows
those commits touch **only** `HANDOFF_*.md` + `NEXT_TASK.md` — **no code change**. The code
baseline is byte-identical to the green `277d49d`, so the **5029 passed / 51 skipped** full-suite
result and the `-W error` CI gate (344 passed) still hold; re-running the 750 s suite is make-work.
Re-confirmed blockers (cheap): `verify_gates_workflow_patch.py` exit 0 (7 violations, maintainer
must land); `verify_hypothesis_inventory.py` IN SYNC (H201 == H201); `origin/main...HEAD` → `0 0`.
No maintainer authorization (paid/consensus source, workflows scope) present in the repo.

**Conclusion:** no bounded, high-value, non-make-work task is agent-executable. The two items below
require maintainer action. Do NOT fabricate H202, re-run the suite/baseline, add a guard test,
re-probe N-CEN, or re-declare 13F/FINRA/FRED/CBOE/N-CEN blocked.

### Cycle 321 — full-suite + CI-gate ground truth (prior session, still authoritative)

### Cycle 321 — new evidence (full-suite + CI-gate ground truth, not a re-assertion)
Prior cycles (incl. 320) only ran *focused* tests. This session ran the **whole** suite and the **actual CI `-W error` gate**, which prior handoffs did not:
- **Full suite green:** `python -m pytest -q --ignore=tests/test_gates_workflow.py` → **5029 passed, 51 skipped, 0 failed** in 765 s (the 51 skips are all legitimate artifact-conditional / container-convention skips; the excluded file is red by design, see below). This is the current 2026-11-26 baseline at `277d49d`.
- **CI `-W error` contract holds:** `pytest -W error tests/test_runner_import_contract.py tests/test_verify_hypothesis_inventory.py` → **344 passed** (the Cycle-278 `google.protobuf` DeprecationWarning escape stays fixed).
- **Fast invariants re-confirmed:** `ruff check` + `ruff format --check` clean (407 files); `verify_hypothesis_inventory.py` IN SYNC (H201==H201); `verify_gates_workflow_patch.py` exit 0 (resolves all 7 violations, maintainer must land); `git rev-list --left-right --count origin/main...HEAD` → `0 0`; no TODO/FIXME/XXX/HACK in `src/`/`scripts/`/`run_*.py`.
- Coverage gate remains `fail_under = 100` (`pyproject.toml`); not re-measured this session (frozen numerical core, ~13 min, no change to `src/qtr`).

**Conclusion (unchanged, now with full-suite evidence):** no bounded, high-value, non-make-work task is agent-executable. The two items below require maintainer action. Do NOT fabricate H202, re-run the suite/baseline as the deliverable, add a guard test, re-probe N-CEN, or re-declare 13F/FINRA/FRED/CBOE/N-CEN blocked.

### Cycle 320 — independent audit (prior session)
A fresh session independently re-checked the Cycle 319 handoff rather than trusting it. New evidence gathered this session (not in prior handoffs):
- **No source TODO/FIXME/XXX/HACK** anywhere in `src/`, `scripts/`, `run_*.py` (grep clean) — no latent defect markers to action.
- **No enableable skipped tests:** the only `skipif` in `tests/` is `test_verify_gates_workflow_patch.py:29` (legitimate conditional — skips when the patch cannot apply). Nothing to un-skip.
- **No remote divergence:** `git rev-list --left-right --count origin/main...HEAD` → `0  0` (local main == origin/main).
- **Inventory IN SYNC:** `scripts/verify_hypothesis_inventory.py` → H201 == H201 (exit 0).
- **Patch still applies:** `scripts/verify_gates_workflow_patch.py` → exit 0, "resolves all 7 violation(s); a maintainer must land it with workflows-scoped credentials."
- **Focused tests green:** `tests/test_verify_hypothesis_inventory.py` + `tests/test_probe_remaining_family_sources.py` → 49 passed.
- **Frontier closure re-read in full** (register Cycles 308→319): N-CEN multi-exhibit path evidenced a false premise (no data exhibit, no flow field); no remaining free candidate.
- Recent commits `d3ea9fe`/`a8852ae` carry real diffs (Cycle 319 work + committed `.cache` parquet for reproducibility per `.gitignore`); **not** control-marker-only.

**Conclusion:** no bounded, high-value, non-make-work task is agent-executable this session. The two items below require maintainer action. Do NOT fabricate H202, re-run the 750 s baseline, add a guard test, re-probe N-CEN, or re-declare 13F/FINRA/FRED/CBOE blocked.

### Cycle 319 (prior session) — resolved the last free-data candidate (N-CEN "heavier multi-exhibit parser").
- Extended `scripts/probe_remaining_family_sources.py::probe_sec_ncen` to enumerate **every** document in the N-CEN filing directory (new `list_filing_documents` helper via the filing `index.json`) and scan **all** `.xml` exhibits — not just `primary_doc.xml` — for shareholder-flow fields. Added `tests/test_probe_remaining_family_sources.py` cases (18 → 21). Live probe (free, read-only) confirms: BlackRock Funds and Vanguard World Fund N-CEN filings each carry **exactly one XML document (`primary_doc.xml`)**, **no additional data exhibit**, and **no shareholder sales/redemptions flow field** (the only purchase/sale-like tags are ETF creation/redemption *units* and broker-dealer *principal* securities-lending transactions). **The "heavier multi-exhibit parser" path (handoff option (a)) is a false premise; the fund-flow family is not free-sourceable from N-CEN.** No H202 fabricated; high-water mark stays H201.
- **Verification (this session):** `tests/test_probe_remaining_family_sources.py` 21 passed; `test_probe_script_coverage` + `test_script_test_coverage` 5 passed; `test_experiment_artifact_schema` 124 passed (committed artifact inventory untouched — probe writes to git-ignored `.cache/`); combined probe/inventory/schema sweep 184 passed under `-W error`; `scripts/verify_hypothesis_inventory.py` IN SYNC (H201 == H201); `ruff check` + `ruff format --check` clean on both changed files; `git status --short` shows only the two intended files modified.

### Unresolved (maintainer / next-session)
1. **Workflow contract patch — still unlanded.** `patches/0001-gates-workflow-contract-fix.patch` applies cleanly; `python scripts/verify_gates_workflow_patch.py` → exit 0, "PATCH VERIFIED ... resolves all 7 violation(s)". Agent cannot land: `.github/workflows/**` is controller-restored and the token lacks `workflows` scope. Awaits maintainer: `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`.
2. **Paid/consensus source authorization for H202 — pending maintainer.** The free-data frontier is now evidenced exhausted (see above); opening a genuinely-distinct family requires a paid/consensus source (options chains, analyst revisions, macro consensus).

### Approaches already failed — do NOT repeat
- Re-running the fast invariants / 750 s baseline as the deliverable; appending another "verified, nothing to do" block; adding another guard test; reconciling a doc — make-work.
- Fabricating H202 or running another equity cross-section / discovery scan on the exhausted universe (directive §2).
- Editing `.github/workflows/**` in a commit — controller-restored; token lacks `workflows` scope.
- Re-declaring SEC 13F / FINRA / FRED / CBOE / N-CEN "data-blocked" without the named-source probe (all probed). **New:** do NOT re-attempt the N-CEN "heavier multi-exhibit parser" — evidenced a false premise (no data exhibit, no flow field).
- Chasing the `src/qtr` audit candidates as "bugs" — verified documented conventions / frozen numerical core.

### Precise next task (choose ONE, in priority order)
**Await maintainer action on the two blocked items above, then:**
- If paid/consensus source authorized: bump H-ID to H202 in `AGENTS.md` and `HYPOTHESIS_SPEC.md` (bump together per the AGENTS.md contract), open the new family per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 313/319, and execute H202 on the paid source.
- If not authorized: the free-data research frontier is evidenced exhausted; no further free-data family search is warranted. Confirm the program remains closed.

**Loop-breaking instruction for the next agent:** the "re-verify invariants + re-declare closure" cycle has now run many times (through Cycle 321) and is itself the make-work failure mode. Do NOT repeat it. The full suite is green (5029 passed) and the `-W error` CI gate passes at `277d49d` — re-running either as the deliverable is explicitly make-work. If no maintainer authorization has landed by the time you run, the correct action is a SHORT handoff that (a) states the program is closed, (b) cites the Cycle 321 full-suite evidence rather than re-measuring, and (c) stops — do not add guards, do not re-probe, do not fabricate H202.
Do NOT re-run the 750 s baseline, do NOT add more guards, do NOT re-declare 13F/FINRA/FRED/CBOE/N-CEN blocked, do NOT re-probe N-CEN, do NOT fabricate H202.

(End of file)