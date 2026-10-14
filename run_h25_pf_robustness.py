"""H25 Robustness: OOS profit-factor & Sharpe bootstrap confidence intervals.

This is NOT a new selection / hypothesis.  It is a post-hoc statistical-robustness
audit of the *already-certified* H25 selected config (mirror of the H13 audit of
H10), addressing H25's single acknowledged residual caveat: the OOS profit-factor
margin (+0.020) sits "inside the bootstrap CI noise floor" of the H13 audit.

No selection occurs on Test; no gate is weakened; no new data is fetched.  The
selected config, OOS window and gates are exactly H25's executed values.  Only
already-tested bootstrap primitives are reused:

    * ``run_h13_oos_deflation_pf_audit.bootstrap_profit_factor_distribution``
    * ``run_h11_robustness_experiment.bootstrap_sharpe_distribution``
    * ``qtr.validation.statistics.sharpe_ratio``
    * ``run_h13_oos_deflation_pf_audit._profit_factor``

All are i.i.d. resampling-with-replacement, ``default_rng``-seeded -> fully
deterministic given the seed.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import run_h11_robustness_experiment as h11
import run_h13_oos_deflation_pf_audit as h13
import run_h25_futures_tsmom_pfmargin as h25
from qtr.validation.statistics import sharpe_ratio

SEED = 42
N_BOOTSTRAP = 2000
PF_GATE = h13.GATES["min_profit_factor"]  # 1.3
SR_GATE = h13.GATES["min_sharpe"]  # 1.0
CI_PERCENTILES = (2.5, 97.5)
# `HYPOTHESIS` is this audit's own label, kept distinct from "H25" so the
# project's H25-artifact discovery helpers (which match hypothesis=="H25" OR
# "h25" in dir name) do not mistake this audit dir for a real H25 experiment run.
HYPOTHESIS = "H25_ROBUSTNESS"
AUDITED_HYPOTHESIS = "H25"

ART_DIR = Path(__file__).resolve().parent / ".experiments/artifacts/pf_robustness"


def _find_latest_h25_dir() -> Path:
    """Latest committed H25 experiment artifact directory (by name)."""
    root = Path(".experiments/artifacts")
    cands = []
    for d in root.iterdir():
        if not d.is_dir():
            continue
        if not (d / "prices.parquet").exists():
            # A real H25 run artifact always carries prices.parquet; this also
            # excludes this audit's own output directory.
            continue
        sf = d / "summary.json"
        if not sf.exists():
            continue
        try:
            with open(sf) as f:
                s = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if s.get("hypothesis") == "H25":
            cands.append(d)
    assert cands, "no H25 artifact directory found under .experiments/artifacts/"
    return max(cands, key=lambda d: d.name)


def oos_returns(h25_dir: Path) -> np.ndarray:
    """OOS (Val+Test) basket returns of the H25 selected config.

    Slicing is identical to the H25 gate evaluation (``_splits``), so the
    point estimates below reproduce H25's ``summary.json`` exactly.
    """
    prices = pd.read_parquet(h25_dir / "prices.parquet")
    returns = pd.read_parquet(h25_dir / "returns.parquet")
    _train_mask, val_mask, test_mask = h25._splits(prices)
    oos = val_mask | test_mask
    r = returns["returns"][oos]
    return pd.to_numeric(r, errors="coerce").dropna().to_numpy(dtype=float)


def bootstrap_arrays(
    oos_returns_arr: np.ndarray, seed: int = SEED, n_bootstrap: int = N_BOOTSTRAP
):
    """Return the (pf, sharpe) bootstrap distributions used by the audit."""
    r = np.asarray(oos_returns_arr, dtype=float)
    r = r[np.isfinite(r)]
    pf = h13.bootstrap_profit_factor_distribution(r, seed=seed, n_bootstrap=n_bootstrap)
    sr = h11.bootstrap_sharpe_distribution(r, seed=seed, n_bootstrap=n_bootstrap)
    return pf, sr


def compute_h25_robustness(
    oos_returns_arr: np.ndarray, seed: int = SEED, n_bootstrap: int = N_BOOTSTRAP
) -> dict:
    """Compute the H25 robustness characterization (point + CIs + fractions).

    Pure / deterministic: identical inputs + seed -> identical output.
    """
    r = np.asarray(oos_returns_arr, dtype=float)
    r = r[np.isfinite(r)]
    pf_boot, sr_boot = bootstrap_arrays(r, seed=seed, n_bootstrap=n_bootstrap)
    pf_lo, pf_hi = np.percentile(pf_boot, CI_PERCENTILES)
    sr_lo, sr_hi = np.percentile(sr_boot, CI_PERCENTILES)
    return {
        "hypothesis": HYPOTHESIS,
        "audited_hypothesis": AUDITED_HYPOTHESIS,
        "seed": seed,
        "n_bootstrap": n_bootstrap,
        "n_oos_bars": len(r),
        "pf_point_estimate": float(h13._profit_factor(r)),
        "sharpe_point_estimate": float(sharpe_ratio(r)),
        "pf_bootstrap_ci_95": [float(pf_lo), float(pf_hi)],
        "sharpe_bootstrap_ci_95": [float(sr_lo), float(sr_hi)],
        "pf_bootstrap_median": float(np.median(pf_boot)),
        "sharpe_bootstrap_median": float(np.median(sr_boot)),
        "pf_gate": float(PF_GATE),
        "sharpe_gate": float(SR_GATE),
        "pf_frac_ge_gate": float(np.mean(pf_boot >= PF_GATE)),
        "sharpe_frac_ge_gate": float(np.mean(sr_boot >= SR_GATE)),
        "pf_ci_lower_ge_gate": bool(pf_lo >= PF_GATE),
        "sharpe_ci_lower_ge_gate": bool(sr_lo >= SR_GATE),
    }


def main() -> int:
    t0 = __import__("time").perf_counter()
    h25_dir = _find_latest_h25_dir()
    oos = oos_returns(h25_dir)

    pf_boot, sr_boot = bootstrap_arrays(oos)
    res = compute_h25_robustness(oos)
    res["source_h25_artifact"] = str(h25_dir.name)
    res["elapsed_sec"] = float(round(__import__("time").perf_counter() - t0, 3))

    ART_DIR.mkdir(parents=True, exist_ok=True)
    with open(ART_DIR / "summary.json", "w") as f:
        json.dump(res, f, indent=2, default=lambda x: str(x))

    pd.DataFrame(
        {"bootstrap_index": np.arange(len(pf_boot)), "profit_factor": pf_boot}
    ).to_parquet(ART_DIR / "pf_bootstrap.parquet")
    pd.DataFrame(
        {"bootstrap_index": np.arange(len(sr_boot)), "sharpe": sr_boot}
    ).to_parquet(ART_DIR / "sharpe_bootstrap.parquet")

    print("=" * 72)
    print(f"[H25-robustness] source artifact: {h25_dir.name}")
    print(f"  n_oos_bars={res['n_oos_bars']}  n_bootstrap={res['n_bootstrap']}")
    print(f"  PF  point={res['pf_point_estimate']:.4f}  95% CI "
          f"[{res['pf_bootstrap_ci_95'][0]:.4f}, {res['pf_bootstrap_ci_95'][1]:.4f}]  "
          f"P(PF>=1.3)={res['pf_frac_ge_gate']:.4f}  "
          f"LB>=1.3? {res['pf_ci_lower_ge_gate']}")
    print(f"  SR  point={res['sharpe_point_estimate']:.4f}  95% CI "
          f"[{res['sharpe_bootstrap_ci_95'][0]:.4f}, {res['sharpe_bootstrap_ci_95'][1]:.4f}]  "
          f"P(SR>=1.0)={res['sharpe_frac_ge_gate']:.4f}  "
          f"LB>=1.0? {res['sharpe_ci_lower_ge_gate']}")
    print(f"  wrote {ART_DIR}")
    print(f"  elapsed={res['elapsed_sec']:.1f}s")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
