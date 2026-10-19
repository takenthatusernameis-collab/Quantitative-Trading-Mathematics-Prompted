"""H26: Sharpe annualization-scale audit of the intraday (1h) family.

Pre-registered in ``HYPOTHESIS_SPEC.md`` §H26 (2026-10-19, BEFORE execution).
This is NOT a new hypothesis and NOT a new selection: it is a post-hoc
characterization of already-certified results that asks a single question --

    Is the published "OOS Sharpe" an *annualized* Sharpe for every family,
    or is it the per-bar Sharpe scaled by a hard-coded sqrt(252) that only
    annualizes a *daily* series?

The published metric is ``sharpe_ratio(returns)`` with the default
``periods_per_year=252`` -- the per-bar mean/vol ratio times ``sqrt(252)``.
For the daily families the bar is a trading day, so ``sqrt(252)`` *is* the
calendar annualization.  For the intraday (1h) families the bar is one hour
and the same multiplier annualizes neither the trading year
(``sqrt(252 x 6.5)``, the convention the intraday vol-target code itself
uses) nor the calendar year (``sqrt(bars_per_year)`` implied by the bar
index).  The published intraday Sharpe is therefore not on the same scale as
the daily rows of the FINAL_REPORT results table.

Method (frozen by the pre-registration):

  * Reproduction anchor: recompute each artifact's OOS Sharpe from the frozen
    ``returns.parquet`` using the canonical 55/25/20 index split and require
    ``|recomputed - published| <= 1e-9``.  Nothing is re-run, re-selected or
    re-derived; an artifact that fails to reproduce is excluded with a reason.
  * Scale factors: ``as_published`` (sqrt(252)), ``repo_vol_convention``
    (sqrt(252 x 6.5)), ``empirical_calendar`` (sqrt(bars_per_year) from the
    artifact's own bar index) and ``daily_aggregated`` (Sharpe of
    non-overlapping calendar-day returns, x sqrt(252) and x sqrt(365)).
  * Bootstrap: the H11 i.i.d. percentile bootstrap (seed 42, 2,000 resamples)
    on the OOS slice.  The per-bar distribution is computed once; the CI at
    scale ``k`` is exactly ``k x`` the per-bar CI.  The gate fraction
    ``P(Sharpe >= 1.0)`` is *recomputed* at every scale, never rescaled.
  * Dependence check: lag-1..24 autocorrelations and Newey-West long-run
    variance, to test whether square-root scaling is valid for the series.

No gate, threshold, or certified number is changed by this audit.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import run_h11_robustness_experiment as h11
from qtr.validation.statistics import bars_per_year, sharpe_ratio

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / ".experiments" / "artifacts"
ART_DIR = ARTIFACTS / "h26_sharpe_scale"

HYPOTHESIS = "H26"
SEED = 42
N_BOOTSTRAP = 2000
SR_GATE = 1.0
CI_PERCENTILES = (2.5, 97.5)
REPRODUCTION_TOL = 1e-9

# The project-wide annualization multiplier used by every published Sharpe.
AS_PUBLISHED_FACTOR = float(np.sqrt(252))
# The annualization the intraday vol-target code itself applies to hourly
# returns (run_h9...vol_scaled_tsmom_hourly: `std * np.sqrt(252 * 6.5)`).
REPO_VOL_FACTOR = float(np.sqrt(252 * 6.5))

# Audited intraday artifacts (frozen ids, pre-registration §H26 step 1).
AUDITED = [
    {
        "family": "H9",
        "artifact": "exp_2026-10-11T16-52-38-694559Z",
        "published_verdict": "REJECT",
    },
    {
        "family": "H10",
        "artifact": "exp_2026-10-11T17-41-18-169363Z",
        "published_verdict": "PASS",
    },
    {
        "family": "H21",
        "artifact": "exp_2026-10-13T23-27-52-101656Z",
        "published_verdict": "REJECT",
    },
    {
        "family": "H22",
        "artifact": "exp_2026-10-14T18-52-08-943792Z",
        "published_verdict": "PASS",
    },
    {
        "family": "H23",
        "artifact": "exp_2026-10-14T18-13-09-457781Z",
        "published_verdict": "REJECT",
    },
    {
        "family": "H25",
        "artifact": "exp_2026-10-14T20-08-34-613690Z",
        "published_verdict": "PASS",
    },
]

# Daily control (bar index only -- used to show the daily family was already
# correctly annualized and is therefore unaffected by the mis-scaling).
DAILY_CONTROL = {
    "family": "H16",
    "artifact": "exp_2026-10-13T21-22-02-751156Z",
    "interval": "1d",
}


def oos_mask(index: pd.DatetimeIndex) -> np.ndarray:
    """Canonical 55/25/20 index split; the OOS window is Val + Test.

    Identical to the split used by the intraday runners (``_splits`` in
    run_h10 / run_h23): the train/val/test boundaries are index positions
    (55% / 80%), and the OOS window is Val + Test.
    """
    n = len(index)
    train_end = index[int(n * 0.55)]
    val_end = index[int(n * 0.8)]
    val = (index > train_end) & (index <= val_end)
    test = index > val_end
    return np.asarray(val | test)


def scale_report(
    per_bar_sharpe: float, factor: float, boot_per_bar: np.ndarray
) -> dict:
    """Sharpe/CI/gate-fraction at one annualization scale.

    The Sharpe and its CI scale linearly with the annualization factor; the
    gate fraction is recomputed because the gate (1.0) is scale-fixed.
    """
    boot = boot_per_bar * factor
    lo, hi = np.percentile(boot, CI_PERCENTILES)
    return {
        "factor": float(factor),
        "sharpe": float(per_bar_sharpe * factor),
        "ci_95": [float(lo), float(hi)],
        "frac_ge_gate": float(np.mean(boot >= SR_GATE)),
        "ci_lower_ge_gate": bool(lo >= SR_GATE),
    }


def dependence_checks(r: np.ndarray) -> dict:
    """Autocorrelation and Newey-West long-run-variance diagnostics."""
    x = np.asarray(r, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    acf = {}
    for lag in (1, 2, 6, 12, 24):
        if n > lag:
            acf[f"lag_{lag}"] = float(np.corrcoef(x[:-lag], x[lag:])[0, 1])

    def nw_lrv(lag: int) -> float:
        y = x - x.mean()
        lrv = float(np.sum(y**2) / n)
        for l in range(1, lag + 1):
            w = 1.0 - l / (lag + 1.0)
            lrv += 2.0 * w * float(np.sum(y[l:] * y[:-l]) / n)
        return lrv

    var = float(np.var(x, ddof=1))
    lrv = {f"lag_{lag}": nw_lrv(lag) for lag in (1, 12, 24, 48)}
    return {
        "autocorrelation": acf,
        "max_abs_autocorrelation_lag1_24": float(
            max(
                abs(np.corrcoef(x[:-lag], x[lag:])[0, 1])
                for lag in range(1, 25)
                if n > lag
            )
        ),
        "variance_iid": var,
        "newey_west_lrv": lrv,
        "lrv_ratio_vs_iid": {k: float(v / var) for k, v in lrv.items()},
    }


def sharpe_convention_check(oos: np.ndarray, published: float) -> dict:
    """Which standard-deviation convention reproduces the published Sharpe?

    ``qtr.validation.statistics.sharpe_ratio`` converts to a numpy array
    before taking the standard deviation, i.e. it uses the *population*
    (ddof=0) estimator.  An artifact produced before that conversion
    inherited the *sample* (ddof=1) estimator of ``pandas.Series.std()``.
    The two differ by a factor ``sqrt(n / (n - 1))`` -- immaterial in
    magnitude, but it makes the older artifact non-reproducible with the
    current library, so the audit records which convention each artifact
    was published under.
    """
    x = np.asarray(oos, dtype=float)
    sr_ddof0 = float(x.mean() / x.std(ddof=0) * np.sqrt(252))
    sr_ddof1 = float(x.mean() / x.std(ddof=1) * np.sqrt(252))
    d0 = abs(sr_ddof0 - published)
    d1 = abs(sr_ddof1 - published)
    if d0 <= REPRODUCTION_TOL:
        convention = "population_ddof0"
    elif d1 <= REPRODUCTION_TOL:
        convention = "sample_ddof1"
    else:
        convention = "neither"
    return {
        "published_oos_sharpe": float(published),
        "sharpe_population_ddof0": sr_ddof0,
        "sharpe_sample_ddof1": sr_ddof1,
        "abs_diff_ddof0": float(d0),
        "abs_diff_ddof1": float(d1),
        "published_convention": convention,
    }


def profit_factor(x: np.ndarray) -> float:
    """Gross-profit / gross-loss ratio of a return series."""
    v = np.asarray(x, dtype=float)
    gross_profit = float(v[v > 0].sum())
    gross_loss = float(abs(v[v < 0].sum()))
    return gross_profit / gross_loss if gross_loss > 0 else float("inf")


def pf_window_check(returns: pd.Series, oos: np.ndarray, published_pf: float) -> dict:
    """Was the published profit factor computed on the OOS window or the full sample?

    A profit factor is a ratio of gross sums and is therefore *scale*-free,
    but it is *not* window-free: evaluating the PF gate over the full sample
    (train + val + test) would let the training window into a gate that is
    supposed to be out-of-sample.  This check records which window the
    published number actually came from.
    """
    full = returns.dropna().to_numpy(dtype=float)
    oos_pf = profit_factor(oos)
    full_pf = profit_factor(full)
    d_oos = abs(oos_pf - published_pf)
    d_full = abs(full_pf - published_pf)
    if d_oos <= REPRODUCTION_TOL and d_full > REPRODUCTION_TOL:
        window = "oos_window"
    elif d_full <= REPRODUCTION_TOL and d_oos > REPRODUCTION_TOL:
        window = "full_sample"
    elif d_oos <= REPRODUCTION_TOL and d_full <= REPRODUCTION_TOL:
        window = "ambiguous_both_match"
    else:
        window = "neither"
    return {
        "published_profit_factor": float(published_pf),
        "oos_window_profit_factor": float(oos_pf),
        "full_sample_profit_factor": float(full_pf),
        "abs_diff_oos_window": float(d_oos),
        "abs_diff_full_sample": float(d_full),
        "published_pf_window": window,
    }


def audit_artifact(spec: dict) -> dict:
    """Audit one frozen artifact: reproduce, then characterize the scale."""
    art_dir = ARTIFACTS / spec["artifact"]
    prices = pd.read_parquet(art_dir / "prices.parquet")
    returns = pd.read_parquet(art_dir / "returns.parquet")
    with open(art_dir / "summary.json") as f:
        summary = json.load(f)

    published = float(summary["metrics"]["oos_sharpe"])
    published_pf = float(summary["metrics"]["profit_factor"])
    mask = oos_mask(prices.index)
    oos_series = (
        pd.to_numeric(returns["returns"], errors="coerce")
        .iloc[np.flatnonzero(mask)]
        .dropna()
    )
    oos = oos_series.to_numpy(dtype=float)
    oos_index = oos_series.index
    recomputed = float(sharpe_ratio(oos))
    abs_diff = abs(recomputed - published)

    out = {
        "family": spec["family"],
        "artifact": spec["artifact"],
        "published_verdict": spec["published_verdict"],
        "n_oos_bars": len(oos),
        "oos_start": str(oos_index[0]),
        "oos_end": str(oos_index[-1]),
        "oos_span_days": float(
            (oos_index[-1] - oos_index[0]).total_seconds() / 86400.0
        ),
        "published_oos_sharpe": published,
        "recomputed_oos_sharpe": recomputed,
        "reproduction_abs_diff": float(abs_diff),
        "reproduced": bool(abs_diff <= REPRODUCTION_TOL),
    }
    out["bars_per_day"] = float(len(oos) / out["oos_span_days"])
    out["bars_per_year_empirical"] = float(bars_per_year(oos_index))
    out["sharpe_convention_check"] = sharpe_convention_check(oos, published)
    out["pf_window_check"] = pf_window_check(returns, oos, published_pf)

    if not out["reproduced"]:
        out["excluded_reason"] = (
            f"reproduction failed: |recomputed - published| = {abs_diff:.3e} "
            f"> {REPRODUCTION_TOL:.0e}"
        )
        out["exclusion_diagnosis"] = out["sharpe_convention_check"]
        return out

    per_bar_sharpe = recomputed / AS_PUBLISHED_FACTOR
    boot = h11.bootstrap_sharpe_distribution(oos, seed=SEED, n_bootstrap=N_BOOTSTRAP)
    boot_per_bar = boot / AS_PUBLISHED_FACTOR

    # Daily aggregation: compound the hourly returns inside each calendar day.
    daily = (1.0 + oos_series).resample("1D").prod() - 1.0
    daily = daily.dropna()
    daily_sharpe = (
        float(daily.mean() / daily.std() * np.sqrt(252)) if len(daily) > 1 else 0.0
    )

    scales = {
        "as_published": scale_report(per_bar_sharpe, AS_PUBLISHED_FACTOR, boot_per_bar),
        "repo_vol_convention": scale_report(
            per_bar_sharpe, REPO_VOL_FACTOR, boot_per_bar
        ),
        "empirical_calendar": scale_report(
            per_bar_sharpe,
            float(np.sqrt(out["bars_per_year_empirical"])),
            boot_per_bar,
        ),
        "daily_aggregated_sqrt252": {
            "factor": float(np.sqrt(252)),
            "sharpe": float(daily_sharpe),
            "ci_95": None,
            "frac_ge_gate": None,
            "ci_lower_ge_gate": None,
            "note": (
                "Point estimate only: non-overlapping calendar-day returns "
                "(compounded), annualized by sqrt(252). The bootstrap CI is not "
                "recomputed on the aggregated series, so the gate fraction is "
                "not reported for this scale."
            ),
        },
    }

    out["scales"] = scales
    out["scale_ratio_empirical_over_published"] = float(
        scales["empirical_calendar"]["factor"] / AS_PUBLISHED_FACTOR
    )
    out["scale_ratio_repo_vol_over_published"] = float(
        scales["repo_vol_convention"]["factor"] / AS_PUBLISHED_FACTOR
    )
    out["scale_ratio_daily_agg_over_published"] = float(
        daily_sharpe / published if published else float("nan")
    )
    out["dependence"] = dependence_checks(oos)
    out["gate_impact"] = {
        "gate": SR_GATE,
        "point_pass_as_published": bool(published >= SR_GATE),
        "point_pass_repo_vol_convention": bool(
            scales["repo_vol_convention"]["sharpe"] >= SR_GATE
        ),
        "ci_lower_pass_as_published": bool(scales["as_published"]["ci_lower_ge_gate"]),
        "ci_lower_pass_repo_vol_convention": bool(
            scales["repo_vol_convention"]["ci_lower_ge_gate"]
        ),
        "note": (
            "Reported, never applied: this audit may not re-certify or "
            "de-certify any hypothesis."
        ),
    }
    return out


def audit_daily_control(spec: dict) -> dict:
    """Daily control: the index-implied annualization factor is ~sqrt(252)."""
    art_dir = ARTIFACTS / spec["artifact"]
    prices = pd.read_parquet(art_dir / "prices.parquet")
    bpy = float(bars_per_year(prices.index))
    factor = float(np.sqrt(bpy))
    return {
        "family": spec["family"],
        "artifact": spec["artifact"],
        "interval": spec["interval"],
        "n_bars": len(prices.index),
        "bars_per_year_empirical": bpy,
        "factor_empirical": factor,
        "factor_as_published": AS_PUBLISHED_FACTOR,
        "scale_ratio_empirical_over_published": float(factor / AS_PUBLISHED_FACTOR),
        "is_correctly_annualized": bool(
            abs(factor / AS_PUBLISHED_FACTOR - 1.0) <= 0.01
        ),
    }


def build_report() -> dict:
    """Run the full audit (deterministic given the frozen artifacts)."""
    artifacts = [audit_artifact(spec) for spec in AUDITED]
    audited = [a for a in artifacts if a["reproduced"]]
    excluded = [a for a in artifacts if not a["reproduced"]]
    control = audit_daily_control(DAILY_CONTROL)

    hourly_ratios = [a["scale_ratio_empirical_over_published"] for a in audited]
    scale_confirmed = bool(audited and all(abs(r - 1.0) > 0.01 for r in hourly_ratios))
    control_ok = bool(control["is_correctly_annualized"])

    return {
        "hypothesis": HYPOTHESIS,
        "kind": "audit",
        "seed": SEED,
        "n_bootstrap": N_BOOTSTRAP,
        "sharpe_gate": SR_GATE,
        "as_published_factor": AS_PUBLISHED_FACTOR,
        "repo_vol_factor": REPO_VOL_FACTOR,
        "reproduction_tolerance": REPRODUCTION_TOL,
        "audited": audited,
        "excluded": excluded,
        "daily_control": control,
        "verdict": {
            "scale_confirmed": scale_confirmed,
            "control_ok": control_ok,
            "note": (
                "scale_confirmed: the published intraday metric is materially "
                "not an annualized Sharpe. control_ok: the daily family was "
                "already correctly annualized and is unaffected. No gate, "
                "threshold or certified number is changed by this audit."
            ),
        },
    }


def main() -> int:
    report = build_report()

    ART_DIR.mkdir(parents=True, exist_ok=True)
    with open(ART_DIR / "summary.json", "w") as f:
        json.dump(report, f, indent=2, default=lambda x: str(x))

    rows = []
    for a in report["audited"]:
        for name, s in a["scales"].items():
            rows.append(
                {
                    "family": a["family"],
                    "artifact": a["artifact"],
                    "published_verdict": a["published_verdict"],
                    "scale": name,
                    "factor": s["factor"],
                    "sharpe": s["sharpe"],
                    "ci_lo": s["ci_95"][0] if s["ci_95"] else None,
                    "ci_hi": s["ci_95"][1] if s["ci_95"] else None,
                    "frac_ge_gate": s["frac_ge_gate"],
                    "ci_lower_ge_gate": s["ci_lower_ge_gate"],
                    "n_oos_bars": a["n_oos_bars"],
                }
            )
    pd.DataFrame(rows).to_parquet(ART_DIR / "scale_table.parquet")

    print("=" * 100)
    print("[H26] Sharpe annualization-scale audit (pre-registered; no gate changed)")
    for a in report["audited"]:
        pub = a["published_oos_sharpe"]
        print(
            f"  {a['family']:<4} n={a['n_oos_bars']:>5} bars/day={a['bars_per_day']:5.2f} "
            f"published={pub:8.4f}  x{REPO_VOL_FACTOR / AS_PUBLISHED_FACTOR:.4f}="
            f"{a['scales']['repo_vol_convention']['sharpe']:8.4f}  "
            f"x{a['scale_ratio_empirical_over_published']:.4f}="
            f"{a['scales']['empirical_calendar']['sharpe']:8.4f}  "
            f"daily-agg={a['scales']['daily_aggregated_sqrt252']['sharpe']:8.4f}  "
            f"[{a['published_verdict']}]"
        )
    c = report["daily_control"]
    print(
        f"  CONTROL {c['family']} (daily): bars/yr={c['bars_per_year_empirical']:.2f} "
        f"ratio={c['scale_ratio_empirical_over_published']:.4f} "
        f"correctly_annualized={c['is_correctly_annualized']}"
    )
    v = report["verdict"]
    print(
        f"  verdict: scale_confirmed={v['scale_confirmed']} control_ok={v['control_ok']}"
    )
    print(f"  wrote {ART_DIR}")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
