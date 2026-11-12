"""Temporary probe: discover the RECIPES entry for each H51 artifact that is
committed but not yet in the pinned PUBLISHED_INFORMATION_RATIOS table.

For each such artifact, try every (strategy_file, strategy_is_equity,
benchmark_file, benchmark_is_equity, train_end) combination that exists in
the artifact directory, and every plausible train_end (the runner's
TRAIN_END values), and report which reproduces the published information_ratio
to 1e-9.
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pandas as pd

from _utils_parquet import read_parquet_safe

ROOT = pathlib.Path(".")
INITIAL_CAPITAL = 1_000_000.0

CANDIDATE_TRAIN_ENDS = [None, "2014-12-31", "2017-12-31", "2019-12-31",
                        "2020-12-31", "2022-12-31", "2023-12-31"]


def _series(path: pathlib.Path) -> pd.Series:
    frame = read_parquet_safe(path)
    return frame[frame.columns[0]]


def _returns_from_equity(equity: pd.Series) -> pd.Series:
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] / INITIAL_CAPITAL - 1.0
    return returns


def ir_for(sfile, s_is_eq, bfile, b_is_eq, train_end, aid_dir):
    s = _series(aid_dir / sfile)
    b = _series(aid_dir / bfile)
    if s_is_eq:
        s = _returns_from_equity(s)
    if b_is_eq:
        b = _returns_from_equity(b)
    if train_end is not None:
        idx = s.index[s.index > pd.Timestamp(train_end)]
        s = s.reindex(idx)
        b = b.reindex(idx)
        if b_is_eq:
            b = b.ffill()
    left, right = s.align(b, join="inner")
    keep = ~(np.isnan(left.values) | np.isnan(right.values))
    left, right = left[keep], right[keep]
    ex = left.to_numpy() - right.to_numpy()
    if len(ex) < 2:
        return None, None
    for ddof in (0, 1):
        std = ex.std(ddof=ddof)
        if std <= 0:
            continue
        yield ddof, float(ex.mean() / std * math.sqrt(252)), len(ex)


def main() -> None:
    # Gather committed artifacts that publish an information_ratio
    published = []
    for summary_path in sorted((ROOT / ".experiments" / "artifacts").glob("*/summary.json")):
        summary = json.loads(summary_path.read_text())
        metrics = summary.get("metrics") or {}
        if isinstance(metrics, dict) and isinstance(metrics.get("information_ratio"), (int, float)):
            published.append((summary_path.parent.name, float(metrics["information_ratio"]),
                              summary.get("hypothesis"), metrics.get("benchmark_p_value")))

    # Existing pinned set
    pinned = set()
    pinned_src = (ROOT / "tests" / "test_h51_benchmark_container_invariance.py").read_text()
    for line in pinned_src.splitlines():
        if line.strip().startswith('"exp_'):
            pinned.add(line.strip().split(":")[0].strip().strip('",'))

    missing = [p for p in published if p[0] not in pinned]
    print(f"total published IR artifacts: {len(published)}; pinned: {len(pinned)}; missing: {len(missing)}")

    for aid, pub_ir, hyp, pub_p in missing:
        aid_dir = ROOT / ".experiments" / "artifacts" / aid
        files = [f.name for f in aid_dir.iterdir() if f.is_file() and f.name.endswith(".parquet")]
        strat_files = [f for f in files if f not in ("benchmark_equity.parquet", "benchmark_returns.parquet")]
        bench_files = [f for f in files if f.startswith("benchmark_")]
        found = False
        for sfile in strat_files:
            for s_is_eq in (True, False):
                for bfile in bench_files:
                    for b_is_eq in (True, False):
                        for train_end in CANDIDATE_TRAIN_ENDS:
                            try:
                                results = list(ir_for(sfile, s_is_eq, bfile, b_is_eq, train_end, aid_dir))
                            except Exception:
                                continue
                            for ddof, ir, n in results:
                                if abs(ir - pub_ir) < 1e-9:
                                    print(f"MATCH {aid} hyp={hyp} pub_ir={pub_ir} pub_p={pub_p}")
                                    print(f"   sfile={sfile} s_eq={s_is_eq} bfile={bfile} b_eq={b_is_eq} train_end={train_end} ddof={ddof} n={n}")
                                    found = True
                                    break
                            if found:
                                break
                        if found:
                            break
                if found:
                    break
            if found:
                break
        if not found:
            print(f"NO-MATCH {aid} hyp={hyp} pub_ir={pub_ir} pub_p={pub_p} files={files}")


if __name__ == "__main__":
    main()