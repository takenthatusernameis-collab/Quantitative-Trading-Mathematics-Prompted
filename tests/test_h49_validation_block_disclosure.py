import json
from pathlib import Path

ARTIFACTS = Path(".experiments/artifacts")

CASES = [
    "exp_2026-10-10T17-02-22-080026Z",
    "exp_2026-10-10T17-03-39-610858Z",
    "exp_2026-10-10T17-04-21-400695Z",
]


def test_published_validation_block_disclosed():
    for name in CASES:
        art = ARTIFACTS / name
        summary = json.loads((art / "summary.json").read_text())
        v = summary["validation"]
        # published pre-guard walkforward_stability exceeds 1.0 on losing halves
        assert v["walkforward_stability"] > 1.0
        assert v["walkforward_pass"] is True or v["walkforward_pass"] == "True"
        # no param_stability key in published block (older code version)
        assert "param_stability" not in v
