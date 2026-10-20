"""Schema validation test for extended data feasibility probe report."""

import re
from pathlib import Path

PROBE_PATH = (
    Path(__file__).parent.parent / ".experiments" / "probes" / "extended_data_feasibility_probe.md"
)


REQUIRED_FIELDS = [
    "data_source",
    "available_bars",
    "split_feasibility",
    "estimated_power_ci_impact",
    "assumptions",
    "risks",
]


def test_probe_report_exists():
    """Probe report file exists."""
    assert PROBE_PATH.exists(), f"Missing probe report: {PROBE_PATH}"


def test_probe_report_required_fields():
    """Probe report contains all required fields (case-insensitive section headers)."""
    content = PROBE_PATH.read_text()

    # Check for required field sections (markdown headers or table rows)
    for field in REQUIRED_FIELDS:
        # Match as markdown header (### or ####) or table row
        pattern = rf"(?:^#{1, 4}\s+.*{field}.*$|^\|.*{field}.*\|$)"
        assert re.search(pattern, content, re.IGNORECASE | re.MULTILINE), (
            f"Required field '{field}' not found in probe report"
        )


def test_probe_report_structure():
    """Probe report has expected high-level structure."""
    content = PROBE_PATH.read_text()

    # Must have executive summary
    assert "Executive Summary" in content or "executive summary" in content.lower()

    # Must have verdict/conclusion
    assert "Verdict" in content or "verdict" in content.lower() or "Recommendation" in content

    # Must reference H13/H14 results
    assert "H13" in content
    assert "H14" in content

    # Must mention PF margin / CI lower bound
    assert "1.190" in content or "CI" in content or "confidence" in content.lower()

    # Must mention symbol dispensability
    assert "dispensab" in content.lower() or "indispensable" in content.lower()


def test_probe_report_no_network_fetches():
    """Probe report explicitly states no network fetches were performed."""
    content = PROBE_PATH.read_text()
    assert "no external network fetches" in content.lower() or "no network" in content.lower()


def test_probe_report_readonly():
    """Probe report states read-only / no artifact modifications."""
    content = PROBE_PATH.read_text()
    assert (
        "read-only" in content.lower()
        or "no.*modif" in content.lower()
        or "not overwrit" in content.lower()
    )


def test_probe_report_runtime_bound():
    """Probe report mentions runtime constraint."""
    content = PROBE_PATH.read_text()
    assert "0.01" in content or "cpu-h" in content.lower() or "runtime" in content.lower()
