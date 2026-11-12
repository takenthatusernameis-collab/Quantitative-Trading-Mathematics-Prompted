#!/usr/bin/env python3
"""Remediation planner for missing experiment artifacts.

Loads .experiments/experiments.jsonl, finds every referenced artifact whose
path is missing on disk, and for each one searches .experiments/artifacts for
a same-basename candidate.  A candidate is only accepted when its SHA-256
16-char prefix equals the recorded hash embedded in the artifact name.

The planner is read-only by default: without ``--apply`` it never copies,
moves, or deletes anything.  It emits a deterministic report and exits non-zero
if any planned row fails hash verification, so the plan cannot silently
recommend a corrupted restore.

``--apply`` is the explicit, opt-in write path (default off).  It re-verifies
each source hash immediately before copying and never overwrites an existing
target, so applying a plan that drifted between planning and application is
refused rather than silently corrupting the artifact store.  Applying the plan
changes the artifact store and requires explicit human authorization.
"""

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_JSONL = ROOT / ".experiments" / "experiments.jsonl"
ARTIFACTS_ROOT = ROOT / ".experiments" / "artifacts"
HASH_LEN = 16


def _hash_file(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:HASH_LEN]


def _display_path(path: Path) -> str:
    """Repo-relative path when possible so reports are machine-independent."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _load_experiments() -> list[dict]:
    experiments = []
    with open(EXPERIMENTS_JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                experiments.append(json.loads(line))
    return experiments


def _build_candidate_index() -> dict[str, list[Path]]:
    """Map basename -> list of existing artifact files (excluding sidecars)."""
    index: dict[str, list[Path]] = {}
    for f in ARTIFACTS_ROOT.rglob("*"):
        if f.is_file() and not f.name.endswith(".meta.json"):
            index.setdefault(f.name, []).append(f)
    return index


def _recorded_hash(artifact_name: str) -> str | None:
    parts = artifact_name.rsplit("_", 1)
    if len(parts) == 2 and len(parts[1]) == HASH_LEN:
        return parts[1]
    return None


def build_plan(experiments: list[dict], candidate_index: dict[str, list[Path]]):
    recoverable: list[dict] = []
    unrecoverable: list[dict] = []

    for exp in experiments:
        exp_id = exp["metadata"]["experiment_id"]
        for artifact_name, artifact_path_str in exp.get("artifacts", {}).items():
            expected_path = Path(artifact_path_str)
            if expected_path.exists():
                continue  # not missing

            recorded_hash = _recorded_hash(artifact_name)
            basename = expected_path.name
            candidates = candidate_index.get(basename, [])
            source = None
            source_hash = None
            if recorded_hash is not None:
                for c in candidates:
                    actual = _hash_file(c)
                    if actual == recorded_hash:
                        source = c
                        source_hash = actual
                        break

            row = {
                "experiment_id": exp_id,
                "artifact_name": artifact_name,
                "expected_path": str(expected_path),
                "recorded_hash": recorded_hash,
                "source_path": _display_path(source) if source else "",
                "source_hash": source_hash or "",
                "exact_match": source is not None,
            }
            if source is not None:
                recoverable.append(row)
            else:
                unrecoverable.append(row)

    # Deterministic ordering for reproducible reports.
    recoverable.sort(key=lambda r: (r["experiment_id"], r["artifact_name"]))
    unrecoverable.sort(key=lambda r: (r["experiment_id"], r["artifact_name"]))
    return recoverable, unrecoverable


def _resolve(path_str: str, root: Path) -> Path:
    """Resolve a plan path against ``root`` (paths are normally repo-relative)."""
    path = Path(path_str)
    return path if path.is_absolute() else root / path


def apply_plan(recoverable: list[dict], *, dry_run: bool = False, root: Path = ROOT) -> list[dict]:
    """Copy each hash-exact recoverable artifact into place (opt-in write path).

    For every row the source is re-hashed immediately before copying and the
    target is refused if it already exists, so a plan row whose source drifted
    or whose target appeared between planning and application raises instead of
    silently corrupting the artifact store.  With ``dry_run`` nothing is written.
    """
    applied: list[dict] = []
    for row in recoverable:
        source = _resolve(row["source_path"], root)
        target = _resolve(row["expected_path"], root)
        assert source.exists(), f"planned source missing on disk: {source}"
        actual = _hash_file(source)
        assert actual == row["recorded_hash"], (
            f"source hash changed before copy for {row['artifact_name']}: "
            f"recorded {row['recorded_hash']} != actual {actual}"
        )
        assert not target.exists(), f"refusing to overwrite existing target: {target}"
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            assert _hash_file(target) == row["recorded_hash"], (
                f"copied file failed hash verification: {target}"
            )
        applied.append({"artifact_name": row["artifact_name"], "target": str(target)})
    return applied


def write_md_report(path: Path, recoverable: list[dict], unrecoverable: list[dict]) -> None:
    lines = [
        "# Artifact Restoration Plan",
        "",
        "Plan only. No copy has been executed (applying requires the explicit `--apply` flag).",
        "",
        f"- Recoverable rows (hash-exact): {len(recoverable)}",
        f"- Unrecoverable rows: {len(unrecoverable)}",
        "",
        "## Recoverable",
        "",
        "| experiment_id | artifact_name | expected_path | source_path | recorded_hash | source_hash |",
        "|---|---|---|---|---|---|",
    ]
    for r in recoverable:
        lines.append(
            f"| {r['experiment_id']} | {r['artifact_name']} | {r['expected_path']} "
            f"| {r['source_path']} | {r['recorded_hash']} | {r['source_hash']} |"
        )
    lines += ["", "## Unrecoverable", ""]
    if unrecoverable:
        lines.append("| experiment_id | artifact_name | expected_path | recorded_hash |")
        lines.append("|---|---|---|---|")
        for r in unrecoverable:
            lines.append(
                f"| {r['experiment_id']} | {r['artifact_name']} "
                f"| {r['expected_path']} | {r['recorded_hash']} |"
            )
    else:
        lines.append("None.")
    lines += ["", "Generated by `scripts/plan_artifact_restoration.py`."]
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report", default="REPRODUCIBILITY_RESTORATION_PLAN.md", help="Markdown report path"
    )
    parser.add_argument(
        "--csv", default="REPRODUCIBILITY_RESTORATION_PLAN.csv", help="CSV plan path"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="copy hash-exact sources into place (opt-in; default off)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="with --apply, report what would be copied without writing",
    )
    args = parser.parse_args()

    experiments = _load_experiments()
    candidate_index = _build_candidate_index()
    recoverable, unrecoverable = build_plan(experiments, candidate_index)

    # Every planned row must be hash-verified; this is the safety gate.
    for r in recoverable:
        assert r["source_path"], f"recoverable row has no source: {r}"
        assert r["source_hash"] == r["recorded_hash"], (
            f"hash verification failed for {r['artifact_name']}: "
            f"recorded {r['recorded_hash']} != source {r['source_hash']}"
        )

    write_md_report(Path(args.report), recoverable, unrecoverable)

    fieldnames = [
        "experiment_id",
        "artifact_name",
        "expected_path",
        "recorded_hash",
        "source_path",
        "source_hash",
        "exact_match",
    ]
    with open(args.csv, "w", newline="") as f:
        # LF line endings so the report is byte-reproducible across platforms
        # (csv's default excel dialect emits CRLF, which would not match the
        # committed plan).
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for r in recoverable:
            writer.writerow(r)

    print(f"Recoverable rows: {len(recoverable)}")
    print(f"Unrecoverable rows: {len(unrecoverable)}")
    print(f"Markdown report: {args.report}")
    print(f"CSV plan: {args.csv}")

    if args.apply:
        applied = apply_plan(recoverable, dry_run=args.dry_run)
        if args.dry_run:
            print(f"Dry run: would copy {len(applied)} artifact(s)")
            for row in applied:
                print(f"  would copy -> {row['target']}")
        else:
            print(f"Copied {len(applied)} artifact(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
