"""H54 — enumeration of the summaries that publish no `metrics` block.

The gap
-------
§H53 closed the `metrics` block (37 summaries, 450 values). The record's
other 43 summaries publish no `metrics` block at all and carry 24 distinct
top-level shapes, 164 distinct top-level keys and 7785 leaf values. None of
these keys has ever been re-derived from the artifact that published it.

This module pins the *enumeration* of that set: how many summaries, how many
shapes, how many keys, how many publish no parquet artifact at all. It is
the first step of §H54; full per-key re-derivation follows.
"""

import glob
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ART = os.path.join(ROOT, ".experiments", "artifacts")


def _summaries_without_metrics():
    out = []
    for path in sorted(glob.glob(os.path.join(ART, "*", "summary.json"))):
        with open(path) as fh:
            d = json.load(fh)
        if "metrics" not in d or not d.get("metrics"):
            out.append((path, d))
    return out


def test_h54_enumeration_counts():
    rows = _summaries_without_metrics()
    assert len(rows) == 43, len(rows)
    keys = set()
    shapes = set()
    noparq = 0
    for path, d in rows:
        keys.update(d.keys())
        shapes.add(tuple(sorted(d.keys())))
        dr = os.path.dirname(path)
        if not glob.glob(os.path.join(dr, "*.parquet")):
            noparq += 1
    assert len(keys) == 164, len(keys)
    assert len(shapes) == 24, len(shapes)
    assert noparq == 3, noparq


def test_h54_negative_control_counts_move():
    # A mis-count (off by one) must fail the pin.
    rows = _summaries_without_metrics()
    assert len(rows) != 42
    assert len(rows) != 44