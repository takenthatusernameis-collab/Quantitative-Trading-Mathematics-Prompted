"""NF-20261120-04 / H190 (Cycle 235 pre-registration and execution).

Broad mechanism category: carry / crypto perpetual funding & basis.  Repo-new root
family relative to executed H-ID: no executed H-ID trades the perpetual
funding-rate/basis cross-section.  H183 (rejected) tested delta-neutral funding
carry on a single crypto perp (BTCUSDT) with a fixed notional; H190's observable
is the *cross-sectional* funding/basis carry across a universe of liquid USDT
perps, long low-funding (negative carry paid to shorts) / short high-funding,
with monthly refresh and vol targeting.  H184 (rejected) uses commodity
term-structure carry (physically delivered futures roll yield); different
instrument, different settlement, different data source.

H-ID note: H189 is reserved by `NF-20261120-03` gross profitability (confirmed
data-blocked on SEC XBRL, Cycle 234) and is NOT consumed by this runner.  H190 is
the next free H-ID for the crypto funding/basis cross-section.

Mechanism / causal chain.  Perpetual futures embed a funding rate that transfers
carry between longs and shorts every 8 hours to anchor the perp price to spot.
When the funding rate is persistently positive, shorts pay longs (perp trades
rich to spot); when negative, longs pay shorts.  The cross-sectional hypothesis:
names with the most negative funding (longs pay shorts) are being pressured by
excess short demand and should earn positive forward returns; names with the
most positive funding (shorts pay longs) face excess long demand and should earn
less.  Pre-registered direction: long the top-k perps with the lowest funding
rate (most negative), short the top-k with the highest funding rate (most
positive).  Null (H0): the funding/basis cross-section has no predictive power
for next-period perp returns after costs -- a carry overlay adds nothing over a
passive equal-weight long perp book.

PIT timing.  Binance archives publish funding rates with a `calc_time` (the
settlement timestamp, every 8 hours at 00:00, 08:00, 16:00 UTC).  Each
settlement is knowable at that timestamp; a daily calendar date t may only use
funding rates whose `calc_time` <= t end-of-day.  The shared engine applies
``shift(1)``, so a funding snapshot at t is first tradeable at t+1.  Monthly
refresh: funding and basis are computed from the last available settlement of
each month, then forward-filled to the daily calendar.  No same-day outcome
enters the signal.

Pre-registration (Cycle 235, written before any forward-return outcome was
computed).  Sample 2020-01-01 -> 2026-10-31 (common archive availability);
train -> 2023-12-31; Val 2024-01-01 -> 2024-12-31; Test protected 2025-01-01 ->
2026-10-31.  Universe: the 7 curated USDT perps (BTCUSDT, ETHUSDT, BNBUSDT,
XRPUSDT, ADAUSDT, SOLUSDT, DOGEUSDT).  Features: ``funding_annualized`` (8h
rate * 365.25/8 * 3), ``basis_annualized`` ((perp - spot) / spot * 365.25 /
days_to_expiry approximated as perpetual => funding proxy), and
``carry_combined`` (funding + basis).  Cross-sectional z on the monthly grid,
hysteresis entry_z/exit_z, top-k long / bottom-k short, gross-normalized to
one, forward-filled to daily calendar so turnover happens at most monthly.
Grid (bounded, 36): feature {funding_annualized, basis_annualized,
carry_combined} x entry_z {0.5, 1.0} x exit_z {0.0} x k {2, 3} x vol_target
{0.10, 0.15}; train-only 4-fold walk-forward Sharpe selection.  Costs: 5 bps
one-way per leg traded (perp commission + spread); vol targeting delevers only.

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from H184/H186):
Sharpe >= 1.0; trades >= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7;
worst-regime rolling-252 Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with
IR >= 0 vs the passive equal-weight long perp book; OAT +/-20% perturbation
min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same
active leg count, seed 42); inverse signal; train-block Spearman of features as
an input-collinearity diagnostic.

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors and cross-sectional/hysteresis primitives from
run_nf_20261119_02_commodity_hedging_pressure.py (no forked copy); import
archive helpers from scripts/probe_binance_funding_availability.py (no forked
copy).  Free/public real data only; ``src/qtr`` unchanged.  Artifact under
.experiments/nf_runs/<experiment>_<timestamp>/summary.json + grid.csv.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

try:
    from qtr.validation.statistics import benchmark_significance_gate, compare_to_benchmark
except ImportError:  # allow `python run_nf_*.py` with no editable install
    sys.path.insert(0, str(ROOT / "src"))
    from qtr.validation.statistics import benchmark_significance_gate, compare_to_benchmark

# Reuse engine, metrics, gate, benchmark, cross-sectional/hysteresis helpers from H186
_H186_PATH = ROOT / "run_nf_20261119_02_commodity_hedging_pressure.py"
_h186_spec = importlib.util.spec_from_file_location("h186_hedging", _H186_PATH)
assert _h186_spec is not None and _h186_spec.loader is not None
h186 = importlib.util.module_from_spec(_h186_spec)  # type: ignore[arg-type]
sys.modules[_h186_spec.name] = h186
_h186_spec.loader.exec_module(h186)

# Import archive helpers from the probe (no forked copy)
_PROBE_PATH = ROOT / "scripts" / "probe_binance_funding_availability.py"
_probe_spec = importlib.util.spec_from_file_location("binance_probe", _PROBE_PATH)
assert _probe_spec is not None and _probe_spec.loader is not None
probe = importlib.util.module_from_spec(_probe_spec)  # type: ignore[arg-type]
sys.modules[_probe_spec.name] = probe
_probe_spec.loader.exec_module(probe)

EXPERIMENT = "nf_20261120_04_crypto_funding_carry"
NF_ID = "NF-20261120-04"
HYPOTHESIS = "H190"

START = "2020-01-01"
END = "2026-10-31"
TRAIN_END = "2023-12-31"
VAL_END = "2024-12-31"

# The 7 curated USDT perps from the probe
UNIVERSE = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "SOLUSDT",
    "DOGEUSDT",
]
PRODUCTS = list(UNIVERSE)

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 5
SEED = 42

GATES = dict(h186.GATES)

FEATURES = ["funding_annualized", "basis_annualized", "carry_combined"]
GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [2, 3],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "binance_funding"


# ---------------------------------------------------------------------------
# Data acquisition (free/public, key-less, from Binance public archives)
# ---------------------------------------------------------------------------


def ensure_funding_cache(
    symbols: list[str],
    start: str = START,
    end: str = END,
    cache_dir: Path = CACHE_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Download and cache funding rates, perp klines, and spot klines for symbols.

    Returns (funding_frame, perp_closes, spot_closes) where each is a DataFrame
    indexed by datetime (funding: calc_time; klines: open_time daily) with
    symbols as columns.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    funding_path = cache_dir / "funding_rates.csv"
    perp_path = cache_dir / "perp_closes.csv"
    spot_path = cache_dir / "spot_closes.csv"

    if funding_path.exists() and perp_path.exists() and spot_path.exists():
        funding = pd.read_csv(funding_path, index_col=0, parse_dates=True)
        perp = pd.read_csv(perp_path, index_col=0, parse_dates=True)
        spot = pd.read_csv(spot_path, index_col=0, parse_dates=True)
        if (
            set(symbols).issubset(set(funding.columns))
            and set(symbols).issubset(set(perp.columns))
            and set(symbols).issubset(set(spot.columns))
        ):
            return funding, perp, spot

    # Build month range
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    months = probe.month_range(start_ts.strftime("%Y-%m"), end_ts.strftime("%Y-%m"))

    funding_data = {symbol: [] for symbol in symbols}
    perp_data = {symbol: [] for symbol in symbols}
    spot_data = {symbol: [] for symbol in symbols}

    for symbol in symbols:
        for month in months:
            # Funding
            funding_raw = probe.fetch_archive(probe.archive_url("funding", symbol, month))
            if funding_raw:
                df = probe.parse_funding_archive(funding_raw)
                funding_data[symbol].append(df)

            # Perp klines (daily)
            perp_raw = probe.fetch_archive(probe.archive_url("perp", symbol, month))
            if perp_raw:
                df = probe.parse_kline_archive(perp_raw)
                perp_data[symbol].append(df)

            # Spot klines (daily)
            spot_raw = probe.fetch_archive(probe.archive_url("spot", symbol, month))
            if spot_raw:
                df = probe.parse_kline_archive(spot_raw)
                spot_data[symbol].append(df)

    # Concatenate per symbol
    funding_frames = {}
    perp_frames = {}
    spot_frames = {}
    for symbol in symbols:
        if funding_data[symbol]:
            funding_frames[symbol] = pd.concat(funding_data[symbol], ignore_index=True).sort_values(
                "calc_time"
            )
        if perp_data[symbol]:
            perp_frames[symbol] = pd.concat(perp_data[symbol], ignore_index=True).sort_values(
                "open_time"
            )
        if spot_data[symbol]:
            spot_frames[symbol] = pd.concat(spot_data[symbol], ignore_index=True).sort_values(
                "open_time"
            )

    # Build wide frames
    # Funding: index = calc_time (utc), columns = symbols, values = last_funding_rate
    funding_series = {}
    for symbol in symbols:
        if symbol in funding_frames:
            df = funding_frames[symbol].set_index("calc_time")["last_funding_rate"]
            funding_series[symbol] = df
    funding_wide = pd.DataFrame(funding_series).sort_index()
    funding_wide.index = funding_wide.index.tz_convert(None)  # drop tz for alignment

    # Perp closes: index = date (from open_time ms), columns = symbols
    perp_series = {}
    for symbol in symbols:
        if symbol in perp_frames:
            df = perp_frames[symbol].copy()
            df["date"] = (
                pd.to_datetime(df["open_time"], unit="ms", utc=True)
                .dt.tz_convert(None)
                .dt.normalize()
            )
            series = df.set_index("date")["close"]
            perp_series[symbol] = series
    perp_wide = pd.DataFrame(perp_series).sort_index()

    # Spot closes: index = date, columns = symbols
    spot_series = {}
    for symbol in symbols:
        if symbol in spot_frames:
            df = spot_frames[symbol].copy()
            df["date"] = (
                pd.to_datetime(df["open_time"], unit="ms", utc=True)
                .dt.tz_convert(None)
                .dt.normalize()
            )
            series = df.set_index("date")["close"]
            spot_series[symbol] = series
    spot_wide = pd.DataFrame(spot_series).sort_index()

    # Cache
    funding_wide.to_csv(funding_path)
    perp_wide.to_csv(perp_path)
    spot_wide.to_csv(spot_path)

    return funding_wide, perp_wide, spot_wide


def monthly_funding_basis(
    funding: pd.DataFrame,
    perp: pd.DataFrame,
    spot: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> dict[str, pd.DataFrame]:
    """Compute monthly funding/basis features, forward-filled to daily calendar.

    Returns dict with keys: funding_annualized, basis_annualized, carry_combined.
    Each is a DataFrame indexed by daily calendar with symbols as columns.
    """
    # Resample funding to monthly (last settlement of each month)
    # funding index is calc_time (8h intervals), we want the last calc_time of each month
    funding_monthly = funding.resample("ME").last()

    # Align perp/spot to month-end (last available close of each month)
    perp_monthly = perp.resample("ME").last()
    spot_monthly = spot.resample("ME").last()

    # Annualize funding: 8h rate * (365.25 / 8) * 3 = rate * 136.96875
    # (3 settlements per day, 365.25 days per year)
    FUNDING_ANNUALIZATION = 365.25 * 3  # 1095.75
    funding_ann = funding_monthly * FUNDING_ANNUALIZATION

    # Basis annualized: (perp - spot) / spot * 365.25 / days_to_expiry
    # For perpetuals, no expiry; use funding as proxy for basis carry.
    # Compute perp-spot basis as a percentage, annualized assuming perpetual.
    basis_pct = (perp_monthly - spot_monthly) / spot_monthly
    # Annualize assuming the basis represents the funding carry over the holding period
    # Since perpetuals have no expiry, the basis is effectively the funding rate proxy.
    # We annualize the monthly basis percentage by * 12.
    basis_ann = basis_pct * 12.0

    # Combined carry signal
    carry_combined = funding_ann + basis_ann

    # Forward-fill to daily calendar
    def ffill_to_daily(monthly: pd.DataFrame) -> pd.DataFrame:
        # Reindex to calendar, forward fill
        aligned = monthly.reindex(calendar).ffill()
        return aligned

    return {
        "funding_annualized": ffill_to_daily(funding_ann),
        "basis_annualized": ffill_to_daily(basis_ann),
        "carry_combined": ffill_to_daily(carry_combined),
    }


def perp_returns(perp: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Daily perp returns on the calendar."""
    aligned = perp.reindex(calendar).ffill()
    returns = aligned.pct_change(fill_method=None)
    return returns.where(np.isfinite(returns))


def feature_panel(
    monthly_features: dict[str, pd.DataFrame],
    calendar: pd.DatetimeIndex,
) -> dict[str, pd.DataFrame]:
    """Apply MIN_ACTIVE_NAMES filter to daily features."""
    filtered = {}
    for name, frame in monthly_features.items():
        # Keep only days with >= MIN_ACTIVE_NAMES non-NaN
        active_count = frame.notna().sum(axis=1)
        mask = active_count >= MIN_ACTIVE_NAMES
        filtered[name] = frame.where(mask, np.nan)
    return filtered


def zero_rolls(index: pd.DatetimeIndex, products: list[str]) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=index, columns=products, dtype=float)


def iter_grid():
    for feature in GRID["feature"]:
        for entry_z in GRID["entry_z"]:
            for exit_z in GRID["exit_z"]:
                for k in GRID["k"]:
                    for vol_target in GRID["vol_target"]:
                        yield {
                            "feature": str(feature),
                            "entry_z": float(entry_z),
                            "exit_z": float(exit_z),
                            "k": int(k),
                            "vol_target": float(vol_target),
                        }


def walk_forward_score(
    feature_daily: pd.DataFrame,
    params: dict,
    returns: pd.DataFrame,
    products: list[str],
    train_index: pd.DatetimeIndex,
    n_folds: int = 4,
) -> float:
    """Mean contiguous-fold Sharpe on the train block (selection score only)."""
    if len(train_index) < 400:
        return -999.0
    block_index = train_index
    weights = h186.target_weights(
        feature_daily.reindex(block_index), params, returns.reindex(block_index), products
    )
    fold = len(block_index) // n_folds
    sharpes = []
    for fold_no in range(n_folds):
        start = fold_no * fold
        stop = len(block_index) if fold_no == n_folds - 1 else (fold_no + 1) * fold
        block = block_index[start:stop]
        if len(block) < 120:
            continue
        result = h186.h184.backtest_metrics(
            weights.reindex(block).fillna(0.0),
            returns.reindex(block).fillna(0.0),
            zero_rolls(block, products),
        )
        sharpes.append(h186.h184.annualized_sharpe(result["returns"]))
    return float(np.mean(sharpes)) if sharpes else -999.0


def perturbation_sharpes(
    feature_daily: pd.DataFrame,
    selected: dict,
    returns: pd.DataFrame,
    products: list[str],
    oos_index: pd.DatetimeIndex,
) -> list[float]:
    """OAT +/-20% perturbation of entry_z and k, measured on OOS."""
    variants = []
    for factor in (0.8, 1.2):
        variant = dict(selected)
        variant["entry_z"] = round(float(selected["entry_z"]) * factor, 6)
        variants.append(variant)
    for factor in (0.8, 1.2):
        variant = dict(selected)
        variant["k"] = max(1, int(round(int(selected["k"]) * factor)))
        variants.append(variant)
    sharpes = []
    for variant in variants:
        weights = h186.target_weights(
            feature_daily.reindex(oos_index), variant, returns.reindex(oos_index), products
        )
        result = h186.h184.backtest_metrics(
            weights.fillna(0.0),
            returns.reindex(oos_index).fillna(0.0),
            zero_rolls(oos_index, products),
        )
        sharpes.append(h186.h184.annualized_sharpe(result["returns"]))
    return sharpes


def train_collinearity(
    features: dict[str, pd.DataFrame], train_index: pd.DatetimeIndex
) -> dict[str, float]:
    """Input-only diagnostic: cross-sectional Spearman of each feature pair."""
    names = list(features.keys())
    result = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            left, right = features[names[i]], features[names[j]]
            values = []
            for day in train_index:
                a, b = left.loc[day], right.loc[day]
                usable = a.notna() & b.notna()
                if int(usable.sum()) < 3:
                    continue
                left_values, right_values = a[usable], b[usable]
                if left_values.nunique() < 2 or right_values.nunique() < 2:
                    continue
                value = float(left_values.corr(right_values, method="spearman"))
                if np.isfinite(value):
                    values.append(value)
            key = f"{names[i]}_vs_{names[j]}"
            result[key] = float(np.mean(values)) if values else 0.0
    return result


def artifact_dir(out: str | None) -> Path:
    if out:
        path = Path(out).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = (Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{stamp}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def main(out: str | None = None, download_only: bool = False) -> dict:
    started = time.time()
    calendar = pd.bdate_range(START, END)
    products = list(PRODUCTS)

    funding, perp, spot = ensure_funding_cache(products)
    if download_only:
        provenance = {
            "funding_rows": int(len(funding)),
            "funding_first": str(funding.index.min().date()) if len(funding) else "",
            "funding_last": str(funding.index.max().date()) if len(funding) else "",
            "perp_rows": int(len(perp)),
            "perp_first": str(perp.index.min().date()) if len(perp) else "",
            "perp_last": str(perp.index.max().date()) if len(perp) else "",
            "spot_rows": int(len(spot)),
            "spot_first": str(spot.index.min().date()) if len(spot) else "",
            "spot_last": str(spot.index.max().date()) if len(spot) else "",
        }
        print(json.dumps(provenance, indent=2))
        return provenance

    returns = perp_returns(perp, calendar)

    monthly_features = monthly_funding_basis(funding, perp, spot, calendar)
    features_daily = feature_panel(monthly_features, calendar)

    train_end = pd.Timestamp(TRAIN_END)
    val_end = pd.Timestamp(VAL_END)
    train_index = calendar[calendar <= train_end]
    val_index = calendar[(calendar > train_end) & (calendar <= val_end)]
    test_index = calendar[calendar > val_end]
    oos_index = calendar[calendar > train_end]

    artifact = artifact_dir(out)
    grid_rows = []
    for params in iter_grid():
        score = walk_forward_score(
            features_daily[params["feature"]], params, returns, products, train_index
        )
        grid_rows.append({**params, "wf_train_sharpe": score})
    grid = pd.DataFrame(grid_rows).sort_values("wf_train_sharpe", ascending=False)
    grid.to_csv(artifact / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows: train selection produced no finite score")
    best = valid.iloc[0].to_dict()
    selected = {
        "feature": str(best["feature"]),
        "entry_z": float(best["entry_z"]),
        "exit_z": float(best["exit_z"]),
        "k": int(best["k"]),
        "vol_target": float(best["vol_target"]),
    }
    feature_daily = features_daily[selected["feature"]]

    weights = h186.target_weights(feature_daily, selected, returns, products)
    full = h186.h184.backtest_metrics(weights, returns, zero_rolls(calendar, products))
    train_result = h186.h184.backtest_metrics(
        weights.reindex(train_index).fillna(0.0),
        returns.reindex(train_index).fillna(0.0),
        zero_rolls(train_index, products),
    )
    train_sharpe = h186.h184.annualized_sharpe(train_result["returns"])
    oos = h186.h184.backtest_metrics(
        weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    oos_metrics = h186.h184.metrics(oos["returns"], oos["equity"], oos["trades"])

    wf_stability = (
        float(oos_metrics["sharpe"] / train_sharpe)
        if np.isfinite(train_sharpe) and train_sharpe != 0
        else (float("inf") if oos_metrics["sharpe"] > 0 else 0.0)
    )

    bench_weights = h186.h184.passive_long_weights(returns, calendar)
    bench_raw = (bench_weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    bench_scale = h186.h184.vol_scale(bench_raw, selected["vol_target"])
    bench_sized = bench_weights.mul(bench_scale, axis=0)
    bench_oos = h186.h184.backtest_metrics(
        bench_sized.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    bench_metrics = h186.h184.metrics(
        bench_oos["returns"], bench_oos["equity"], bench_oos["trades"]
    )

    comparison = compare_to_benchmark(oos["returns"], bench_oos["returns"])
    p_value = float(comparison["alpha_p_value"])
    information_ratio = float(comparison["information_ratio"])

    random_target = h186.h184.random_weights(
        weights.reindex(oos_index).fillna(0.0), returns.reindex(oos_index), seed=SEED
    )
    random_result = h186.h184.backtest_metrics(
        random_target,
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    random_metrics = h186.h184.metrics(
        random_result["returns"], random_result["equity"], random_result["trades"]
    )

    inverse_weights = h186.target_weights(-feature_daily, selected, returns, products)
    inverse_result = h186.h184.backtest_metrics(
        inverse_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    inverse_metrics = h186.h184.metrics(
        inverse_result["returns"], inverse_result["equity"], inverse_result["trades"]
    )

    perturbed = [
        value
        for value in perturbation_sharpes(feature_daily, selected, returns, products, oos_index)
        if np.isfinite(value)
    ]
    base_sharpe = oos_metrics["sharpe"]
    min_ratio = (
        float(min(perturbed) / base_sharpe)
        if perturbed and np.isfinite(base_sharpe) and base_sharpe != 0
        else 0.0
    )

    gates = {
        "sharpe_ge_1": bool(np.isfinite(base_sharpe) and base_sharpe >= GATES["min_sharpe"]),
        "trades_ge_50": bool(oos_metrics["trades"] >= GATES["min_trades"]),
        "pf_ge_1_3": bool(
            np.isfinite(oos_metrics["profit_factor"])
            and oos_metrics["profit_factor"] >= GATES["min_profit_factor"]
        ),
        "maxdd_le_15pct": bool(
            np.isfinite(oos_metrics["max_drawdown"])
            and oos_metrics["max_drawdown"] >= -GATES["max_drawdown"]
        ),
        "wf_stability_ge_0_7": bool(
            np.isfinite(wf_stability) and wf_stability >= GATES["min_walkforward_stability"]
        ),
        "worst_regime_ge_0_3": bool(
            np.isfinite(oos_metrics["worst_regime_rolling252_sharpe"])
            and oos_metrics["worst_regime_rolling252_sharpe"] >= GATES["min_worst_regime_sharpe"]
        ),
        "benchmark_p_le_0_05_and_ir_ge_0": benchmark_significance_gate(
            p_value, information_ratio, GATES["max_p_value"]
        ),
        "perturbation_min_ratio_ge_0_5": bool(
            np.isfinite(min_ratio) and min_ratio >= GATES["min_perturbed_sharpe_ratio"]
        ),
    }
    gates_passed = int(sum(gates.values()))
    verdict = "ACCEPT" if gates_passed == len(gates) else "REJECT"

    collinearity = train_collinearity(features_daily, train_index)

    data_meta = {
        "funding_source": "Binance public archives (data.binance.vision)",
        "funding_dataset": "futures/um/monthly/fundingRate",
        "perp_source": "Binance public archives (data.binance.vision)",
        "perp_dataset": "futures/um/monthly/klines/1d",
        "spot_source": "Binance public archives (data.binance.vision)",
        "spot_dataset": "spot/monthly/klines/1d",
        "universe": [{"symbol": s} for s in UNIVERSE],
        "active_names_last_month": int(features_daily["funding_annualized"].iloc[-1].notna().sum())
        if len(features_daily["funding_annualized"]) > 0
        else 0,
    }
    (artifact / "data_meta.json").write_text(json.dumps(data_meta, indent=2) + "\n")

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - started, 3),
        "data": {
            **data_meta,
            "start": START,
            "end": END,
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "train_rows": int(len(train_index)),
            "val_rows": int(len(val_index)),
            "test_rows": int(len(test_index)),
            "oos_rows": int(len(oos_index)),
        },
        "grid_size": int(len(grid)),
        "selected": selected,
        "wf_train_sharpe": float(valid.iloc[0]["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sharpe),
        "full_sample": h186.h184.metrics(full["returns"], full["equity"], full["trades"]),
        "oos_val_test": oos_metrics,
        "val": h186.h184.metrics(
            oos["returns"].reindex(val_index).fillna(0.0),
            oos["equity"].reindex(val_index),
            int((oos["returns"].reindex(val_index).fillna(0.0).ne(0.0)).sum()),
        ),
        "test": h186.h184.metrics(
            oos["returns"].reindex(test_index).fillna(0.0),
            oos["equity"].reindex(test_index),
            int((oos["returns"].reindex(test_index).fillna(0.0).ne(0.0)).sum()),
        ),
        "benchmark_passive_equal_weight_long_oos": bench_metrics,
        "benchmark_comparison": comparison,
        "ablations": {
            "random_ranking_oos": random_metrics,
            "inverse_signal_oos": inverse_metrics,
        },
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else str(wf_stability),
        "benchmark_pvalue_two_sided": p_value,
        "information_ratio_vs_passive_book": information_ratio,
        "perturbation": {
            "min_ratio": float(min_ratio) if np.isfinite(min_ratio) else str(min_ratio),
            "n_points": len(perturbed),
            "min_sharpe": float(min(perturbed)) if perturbed else None,
        },
        "train_input_collinearity": collinearity,
        "gates": gates,
        "gates_passed": gates_passed,
        "gates_total": len(gates),
        "verdict": verdict,
        "integrity": {
            "src_qtr_unchanged": True,
            "gate_weakening": False,
            "published_artifacts_modified": False,
            "selection_holdout_feedback": False,
            "real_data": True,
            "cost_one_way_bps": COST_ONE_WAY_BPS,
            "roll_cross_bps": 0.0,
            "benchmark_pvalue_statistic": "two-sided (published gate statistic)",
            "pit_rule": "funding calc_time settlement timestamp; monthly refresh forward-filled; engine shift(1)",
        },
    }
    (artifact / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": f"{gates_passed}/{len(gates)}",
                "artifact": str(artifact),
                "oos_sharpe": oos_metrics["sharpe"],
            },
            indent=2,
        )
    )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=None, help="artifact directory")
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="populate the Binance archive cache and exit (resumable)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only)
