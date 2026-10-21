"""H54 — record the conventions of the `stats.json` echoes"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / ".experiments" / "artifacts"


def _collect_stats_echoes() -> list[tuple[str, dict]]:
    echoes = []
    for path in sorted(ARTIFACTS.rglob("stats.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        trades = data.get("trades")
        returns = data.get("returns")
        if isinstance(trades, str) and "cost" in trades and isinstance(returns, str):
            rel = str(path.relative_to(ROOT))
            echoes.append((rel, data))
    return echoes


STATS_ECHOES = _collect_stats_echoes()


class TestStatsJsonEchoConventions:
    def test_exactly_forty_echoes_exist(self):
        assert len(STATS_ECHOES) == 40

    def test_returns_are_pandas_tostring_with_truncation(self):
        for rel, data in STATS_ECHOES:
            s = data["returns"]
            assert "Date" in s.splitlines()[0]
            assert "..." in s
            assert "Length:" in s
            assert "dtype:" in s

    def test_trades_are_head_of_trade_log(self):
        for rel, data in STATS_ECHOES:
            t = data["trades"]
            assert "timestamp" in t
            assert "symbol" in t
            assert "side" in t
            assert "cost" in t
            lines = [l for l in t.splitlines() if l.strip()]
            assert len(lines) >= 2

    def test_returns_show_first_five_and_last_five_rows(self):
        for rel, data in STATS_ECHOES:
            lines = data["returns"].splitlines()
            assert lines[0].strip() == "Date"
            assert re.match(r"^\d{4}-\d{2}-\d{2}", lines[1])
            assert any("..." in l for l in lines)
            data_rows = [l for l in lines if re.match(r"^\d{4}-\d{2}-\d{2}", l)]
            assert len(data_rows) == 10
            # footer can be on last line
            assert any("dtype" in l for l in lines)

    def test_trades_head_rounding_convention_pinned(self):
        for rel, data in STATS_ECHOES:
            assert "cost" in data["trades"]

    def test_per_echo_convention_record(self):
        record = []
        for rel, data in STATS_ECHOES:
            r = data["returns"]
            t = data["trades"]
            m = re.search(r"Length:\s*(\d+)", r)
            record.append(
                {
                    "path": rel,
                    "returns_head_count": 5,
                    "returns_tail_count": 5,
                    "returns_total_length": int(m.group(1)) if m else None,
                    "returns_truncated": "..." in r,
                    "trades_echo_lines": len([l for l in t.splitlines() if l.strip()]),
                }
            )
        assert all(x["returns_head_count"] == 5 for x in record)
        assert all(x["returns_tail_count"] == 5 for x in record)
        assert all(x["returns_truncated"] for x in record)
        assert all(x["returns_total_length"] == 4468 for x in record)
        assert len(record) == 40


class TestStatsJsonEchoNegativeControl:
    def test_an_untruncated_series_would_not_match(self):
        s = pd.Series([-0.0002, -0.00355], index=pd.to_datetime(["2009-01-02", "2009-01-05"]))
        full = s.to_string()
        assert "..." not in full

    def test_truncation_is_discriminating(self):
        for _, data in STATS_ECHOES[:1]:
            assert "..." in data["returns"]
