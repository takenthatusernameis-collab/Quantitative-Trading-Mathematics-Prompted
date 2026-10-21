# HANDOFF_NEXT — H50: the package's metadata has one source of truth

## What changed (this session)

- `.gitignore` — `*.egg-info/` added.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`); the files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.

## The gap

`src/qtr.egg-info/` is a **build artifact**, not a source file: setuptools rewrites it on every
build and every install, so the committed copy could only ever be a stale snapshot of the tree —
and it was. The tracked `SOURCES.txt` held **61** entries where the current tree produces **64**
(the three test modules added between H33 and H49 were missing). Nothing noticed, because a tracked
manifest has no invariant.

## Why "regenerate and commit" is not the fix — measured

The conclusion of the two earlier sessions was right; the stated mechanism was not quite right.
Building the same tree with the **local setuptools 68.1.2** (no build isolation) gives:

```
Metadata-Version: 2.1
Requires-Dist: numpy >=1.24.0
Requires-Dist: yfinance >=0.2.0 ; extra == 'data'
```

against the committed file, built under pip's build isolation (a newer setuptools):

```
Metadata-Version: 2.4
Requires-Dist: numpy>=1.24.0
Requires-Dist: yfinance>=0.2.0; extra == "data"
```

The **same** package, two serialisations. **A correction to the earlier record:** the
`Requires-Dist` entries are *not* dropped — every base requirement and every extra's requirement
is present in both builds; they are reformatted and reordered. What is environment-dependent is
the **serialisation**, which is enough to make "regenerate and commit" irreproducible.

Reproduction (no network): `from setuptools import build_meta;
build_meta.prepare_metadata_for_build_wheel("<tmp>")`.

## The contract now pinned (11 tests)

1. **Ignored** — `.gitignore` declares the rule and `git check-ignore` agrees.
2. **Not tracked** — no tracked path lives inside a `*.egg-info/` directory.
3. **Only one declaration** — no tracked `setup.py` / `setup.cfg` / `PKG-INFO` / `requires.txt` /
   `top_level.txt`.
4. **No dependency** — no module under `src/qtr` references the generated manifest.
5. **The build agrees with the declaration** — the generated `PKG-INFO` *and* the installed
   distribution's metadata reproduce the declared version, python floor, base requirements and every
   extra's requirements (normalisation-based, so it does not depend on the setuptools version).
6. **No staleness** — a generated `SOURCES.txt` that exists must list the package's current
   modules (the modules the distribution ships; a test module is not part of it).

Two facts found while writing it:

- **`importlib.metadata` resolves the distribution to the source tree** whenever `src` is on the
  import path (the test suite puts it there): `distribution("qtr")._path` is `src/qtr.egg-info`, not
  the installed `dist-info` — so a developer's tooling reads the *generated* manifest as the
  package's metadata, which is why invariant 5 checks it.
- **A git command that ran and failed is a verdict, not an absence.** The first draft returned
  `None` for any non-zero exit, so `check-ignore` exiting 1 (nothing matched) was silently
  *skipped* instead of failing the contract. Now only a missing git executable or a checkout
  without a repository skips.

## What was actually verified

- `python -m pytest -q -W error tests/test_generated_manifest_contract.py` → **11 passed**.
- `python -m pytest -q -W error` → **1377 passed, 1 skipped** (full suite, up from 1366).
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` =
  **1054 statements, 320 branches, 0 missed, 0 partial, 100.00%** (unchanged — nothing under
  `src/qtr` was touched).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **93 files already formatted**.
- **Negative control** — the contract run against the **pre-fix** state (the manifest re-added to
  the index with `git add -f`): **3 of the 11 tests fail**, every failure behavioural — the
  detector names the offending paths, `check-ignore` exits 1 against a tracked path, and the
  "only one declaration" invariant lists the duplicate metadata files.
- The change is additive to the repository's history: the manifest files remain on disk, the
  editable install still resolves (`import qtr` → `src/qtr/__init__.py`), and the working tree is
  clean after `pip install -e .` — where it previously was not, because the tracked copy was
  rewritten by the install.

## The published record is unaffected

No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added. No module under `src/qtr` and no runner was touched.

## What a next session inherits

- **One task is assigned (H51)** — stated in full in `NEXT_TASK.md`: make `compare_to_benchmark`
  **container-independent** and disclose which published `information_ratio` /
  `excess_vol_annual` numbers are on which convention. The defect is verified: `excess.std()`
  uses ddof=1 for a Series and ddof=0 for an ndarray, so the IR differs by exactly
  `sqrt(n/(n-1))`; the published record contains **both** conventions (H9's artifact re-derives
  under ddof=1, cs_momentum's under ddof=0). **No verdict can move** — the gate reads the IR's
  sign.
- The runner-up (H52) is to extend the H47 cost-attribution disclosure to all **41** committed
  trade logs, of which every one carries the pre-fix attribution.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families
  are frozen.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict frozen.