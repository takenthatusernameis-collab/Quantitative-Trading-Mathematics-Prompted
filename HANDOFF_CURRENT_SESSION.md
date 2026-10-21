# HANDOFF_CURRENT_SESSION — H50: the package's metadata has one source of truth

## What changed

- `.gitignore` — `*.egg-info/` added: the setuptools-generated metadata is ignored.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`); the files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.

### The gap

`src/qtr.egg-info/` is a **build artifact**, not a source file: setuptools rewrites it on every
build and every install, so the committed copy could only ever be a stale snapshot of the tree —
and it was. The tracked `SOURCES.txt` held **61** entries where the current tree produces **64**
(the three test modules added between H33 and H49 were missing). Nothing noticed, because a tracked
manifest has no invariant.

### Why "regenerate and commit" is not the fix — measured

The conclusion of the two earlier sessions was right; the stated mechanism was not quite right.
Building the same tree with the **local setuptools 68.1.2** (no build isolation):

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

The **same** package, two serialisations: the metadata version drops `2.4 → 2.1`, the requirement
markers are re-spaced and re-quoted, the entries are reordered. **A correction to the earlier
record:** the `Requires-Dist` entries are *not* dropped — every base requirement and every extra's
requirement is present in both builds; they are reformatted. What is environment-dependent is the
**serialisation**, which is enough to make "regenerate and commit" irreproducible: the committed
bytes would freeze whichever setuptools happened to build them last.

Reproduction (no network): `from setuptools import build_meta;
build_meta.prepare_metadata_for_build_wheel("<tmp>")`.

### The contract now pinned (11 tests)

1. **Ignored** — `.gitignore` declares the rule and `git check-ignore` agrees.
2. **Not tracked** — no tracked path lives inside a `*.egg-info/` directory.
3. **Only one declaration** — no tracked `setup.py` / `setup.cfg` / `PKG-INFO` / `requires.txt` /
   `top_level.txt`.
4. **No dependency** — no module under `src/qtr` references the generated manifest (the package
   imports from a bare clone with no install step).
5. **The build agrees with the declaration** — the generated `PKG-INFO` *and* the installed
   distribution's metadata reproduce the declared version, python floor, base requirements and every
   extra's requirements. The comparison is normalisation-based, so it does not depend on which
   setuptools built the metadata.
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
  "only one declaration" invariant lists the duplicate metadata files. No failure is an error, a
  skip, or a missing keyword.
- The change is additive to the repository's history: the manifest files remain on disk, the
  editable install still resolves (`import qtr` → `src/qtr/__init__.py`), and the working tree is
  clean after `pip install -e .` — where it previously was not, because the tracked copy was
  rewritten by the install.

## What remains unresolved

- The **H47 cost-attribution disclosure** (the `cost` column of the committed trade logs) is
  unchanged — the artifact files are frozen.
- **H9's published OOS Sharpe** is on the sample convention; disclosed and pinned, verdict frozen.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.