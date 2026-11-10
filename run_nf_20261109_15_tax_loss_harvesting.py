"""NF-20261109-15 / H176 (Cycle 90): Tax-Loss Harvesting / Year-End Selling Pressure.
Institutional/behavioral constraint (repo-new root family; distinct from calendar families
H91/H140/H142/H168 which test generic seasonal windows without the tax-mandated structural
mechanism).

Mechanism. Tax-loss harvesting is a structurally mandated institutional flow (US tax code
requires realization of capital losses by year-end). The interaction of calendar (December)
+ YTD performance rank (tax-loss eligibility) creates a distinct structural flow mechanism:
YTD losers face concentrated selling in late December; buying pressure returns in January
(the "January effect" root cause).

Causal chain (PIT). At each November month-end, YTD total returns are known (past-only).
Universe ranked by YTD return (ascending = biggest losers). During the last `n_days`
trading days of December (ex-ante calendar rule), go long the bottom `k` YTD losers.
Hold through `hold_days` trading days into January; then flat. Vol-targeted off trailing
21-day basket realized vol. 1-bar delay via engine `signals.shift(1)`.

Observable (past-only, PIT, free yfinance). Liquid sector ETFs + SPY daily adjusted close.
YTD return computed at November close. December calendar window known ex-ante.

Null (H0). The tax-loss harvesting flow has no predictive power for next-period returns
of YTD losers beyond random chance after costs.

Pre-registration (Cycle 90, decision-ready before validation outcomes).
NF-ID NF-20261109-15. Hypothesis H176 (next unused after H175; H24/H68-H73/H76-H79
unassigned, not recycled). Universe: XLF, XLE, XLV, XLI, XLB, XLP, XLU, XLY, XLC, XLK,
SPY. Data: yfinance daily 2010-01-01 -> 2026-10-31. Train 2010-01-01 -> 2018-12-31;
Val 2019-01-01 -> 2022-12-31; Test protected 2023-01-01 -> 2026-10-31. Signal: see above.
Grid: n_days {5,10} x k {1,3,5} x hold_days {3,5,10} x vol_target {0.10,0.15} = 36 combos.
Train-only 4-fold WF selection; Test protected.

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=50, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05 with IR>=0,
perturbation min ratio>=0.5.

Ablations: buy-hold SPY benchmark; equal-weight universe benchmark; random-year control;
inverse-signal (long YTD winners in December); OAT perturbation (+/-20% on n_days, k,
hold_days, vol_target); Val/Test subperiods; worst-regime rolling-252 Sharpe. No gate
weakening.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest

EXPERIMENT = "nf_20261109_15_tax_loss_harvesting"
NF_ID = "NF-20261109-15"
HYPOTHESIS = "H176"
START = "2010-01-01"
END = "2026-10-31"
MAX_POS = 0.5
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 21  # Fixed realized-vol window for vol targeting (not a grid param).

# Bounded grid (pre-registered).
GRID = {
    "n_days": [5, 10],
    "k": [1, 3, 5],
    "hold_days": [3, 5, 10],
    "vol_target": [0.10, 0.15],
}

UNIVERSE = ["XLF", "XLE", "XLV", "XLI", "XLB", "XLP", "XLU", "XLY", "XLC", "XLK", "SPY"]


def _artifact_dir(out: str | None) -> Path:
    if out:
        p = Path(out).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    ts = time.strftime("%Y%m%d_%H%M%S")
    p = (Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{ts}").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _download_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError(f"yfinance returned empty data for {symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        df = raw.xs("Close", level=0, axis=1)
        if symbol in df.columns:
            df = df[[symbol]].rename(columns={symbol: "Close"})
        else:
            df = df.iloc[:, [0]].rename(columns={df.columns[0]: "Close"})
    else:
        df = raw[["Close"]].copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df.dropna()
    if df.empty:
        raise RuntimeError(f"no valid daily data for {symbol}")
    return df


def _get_trading_days(prices: pd.DataFrame, year: int) -> pd.DatetimeIndex:
    """Get trading days for a specific year from the price index."""
    year_mask = prices.index.year == year
    return prices.index[year_mask]


def _get_december_window(prices: pd.DataFrame, year: int, n_days: int) -> pd.DatetimeIndex:
    """Get the last n_days trading days of December for a given year."""
    dec_mask = (prices.index.year == year) & (prices.index.month == 12)
    dec_days = prices.index[dec_mask]
    if len(dec_days) < n_days:
        return pd.DatetimeIndex([])
    return dec_days[-n_days:]


def _get_january_hold_days(prices: pd.DataFrame, year: int, hold_days: int) -> pd.DatetimeIndex:
    """Get the first hold_days trading days of January for a given year (year+1)."""
    jan_mask = (prices.index.year == year + 1) & (prices.index.month == 1)
    jan_days = prices.index[jan_mask]
    if len(jan_days) < hold_days:
        return pd.DatetimeIndex([])
    return jan_days[:hold_days]


def _compute_ytd_returns(prices: pd.DataFrame, november_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute YTD total returns at each November month-end for all assets."""
    ytd_returns = pd.DataFrame(index=november_dates, columns=prices.columns, dtype=float)

    for nov_date in november_dates:
        year = nov_date.year
        # Find the first trading day of the year
        year_mask = prices.index.year == year
        year_prices = prices[year_mask]
        if len(year_prices) == 0:
            continue
        first_price = year_prices.iloc[0]
        # Price at November month-end (or closest prior)
        nov_price = prices.loc[:nov_date].iloc[-1]
        # Total return (simple)
        ytd_ret = (nov_price / first_price) - 1.0
        ytd_returns.loc[nov_date] = ytd_ret

    return ytd_returns


def _build_tax_loss_signal(
    prices: pd.DataFrame,
    ytd_returns: pd.DataFrame,
    n_days: int,
    k: int,
    hold_days: int,
    vol_target: float,
    vol_window: int,
) -> pd.DataFrame:
    """Build daily signal DataFrame from the tax-loss harvesting strategy."""
    # Initialize signal DataFrame (all zeros)
    signal = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    # Get unique years from november dates
    years = sorted(ytd_returns.index.year.unique())

    for year in years:
        # November month-end for this year (last trading day of November)
        nov_mask = (ytd_returns.index.year == year) & (ytd_returns.index.month == 11)
        nov_dates = ytd_returns.index[nov_mask]
        if len(nov_dates) == 0:
            continue
        nov_date = nov_dates[-1]  # Last trading day of November

        # YTD returns at November close
        ytd = ytd_returns.loc[nov_date].dropna()
        if len(ytd) < k:
            continue

        # Rank by YTD return (ascending = biggest losers first)
        ranked = ytd.sort_values()
        losers = ranked.index[:k].tolist()

        # December window: last n_days of December
        dec_window = _get_december_window(prices, year, n_days)
        if len(dec_window) == 0:
            continue

        # January hold window: first hold_days of January (year+1)
        jan_window = _get_january_hold_days(prices, year, hold_days)
        if len(jan_window) == 0:
            continue

        # Active trading days: December window + January hold window
        active_days = dec_window.union(jan_window)

        # Set signal to 1.0 for losers on active days (before vol targeting)
        for day in active_days:
            if day in signal.index:
                for asset in losers:
                    signal.loc[day, asset] = 1.0

    # Equal-weight across selected losers
    signal = signal.div(signal.sum(axis=1), axis=0).fillna(0.0)

    # Vol targeting off trailing basket realized vol
    # Compute basket returns first (equal-weight of universe)
    basket_ret = prices.pct_change().fillna(0.0).mean(axis=1)
    daily_vol_target = vol_target / math.sqrt(DAYS_PER_YEAR)
    realized_vol = basket_ret.rolling(vol_window, min_periods=vol_window).std(ddof=0)
    vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)

    # Apply vol scaling to all positions
    signal = signal.mul(vol_scale, axis=0)
    signal = signal.clip(0.0, MAX_POS).fillna(0.0)

    return signal


def _cfg() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=False,
    )


def _run_backtest_daily(prices: pd.DataFrame, signal: pd.DataFrame) -> dict:
    res = run_backtest(prices=prices, signals=signal, config=_cfg())
    m = res.metrics
    if isinstance(m, dict):
        out = {
            "total_return": float(m.get("total_return", float("nan"))),
            "sharpe": float(m.get("sharpe", float("nan"))),
            "sortino": float(m.get("sortino", float("nan"))),
            "max_drawdown": float(m.get("max_drawdown", float("nan"))),
            "calmar": float(m.get("calmar", float("nan"))),
            "profit_factor": float(m.get("profit_factor", float("nan"))),
            "trades": int(m.get("num_trades", 0)),
            "volatility": float(m.get("annualized_volatility", float("nan"))),
            "cagr": float(m.get("annualized_return", float("nan"))),
            "equity_end": float(res.equity_curve.iloc[-1])
            if len(res.equity_curve)
            else float("nan"),
        }
    else:
        out = {
            "total_return": float(m.total_return),
            "sharpe": float(getattr(m, "sharpe_ratio", getattr(m, "sharpe", float("nan")))),
            "sortino": float(getattr(m, "sortino_ratio", getattr(m, "sortino", float("nan")))),
            "max_drawdown": float(m.max_drawdown),
            "calmar": float(m.calmar_ratio),
            "profit_factor": float(m.profit_factor)
            if math.isfinite(float(m.profit_factor))
            else float("nan"),
            "trades": int(getattr(m, "trades_count", getattr(m, "num_trades", 0))),
            "volatility": float(
                getattr(m, "volatility", getattr(m, "annualized_volatility", float("nan")))
            ),
            "cagr": float(getattr(m, "cagr", getattr(m, "annualized_return", float("nan")))),
            "equity_end": float(res.equity_curve.iloc[-1])
            if len(res.equity_curve)
            else float("nan"),
        }
    return {
        "metrics": out,
        "equity": res.equity_curve,
        "daily": res.equity_curve.pct_change().dropna(),
    }


def _slice_metrics(prices: pd.DataFrame, signal: pd.DataFrame, start: str, end: str) -> dict:
    idx = prices.index[(prices.index >= pd.Timestamp(start)) & (prices.index <= pd.Timestamp(end))]
    if len(idx) < 30:
        return {
            "metrics": {"sharpe": float("nan"), "trades": 0},
            "equity": pd.Series(dtype=float),
            "daily": pd.Series(dtype=float),
        }
    return _run_backtest_daily(prices.loc[idx], signal.loc[idx])


def _information_ratio(strategy: pd.Series, benchmark: pd.Series) -> float:
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna()
    if len(diff) < 30 or diff.std(ddof=0) == 0:
        return float("nan")
    return float(diff.mean() / diff.std(ddof=0) * math.sqrt(DAYS_PER_YEAR))


def _benchmark_pvalue(strategy: pd.Series, benchmark: pd.Series) -> float:
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna()
    if len(diff) < 30:
        return float("nan")
    mu = diff.mean()
    se = diff.std(ddof=0) / math.sqrt(len(diff))
    if se == 0 or not math.isfinite(se):
        return float("nan")
    z = mu / se
    try:
        from math import erf

        p = 1.0 - 0.5 * (1.0 + erf(z / math.sqrt(2.0)))
    except Exception:
        p = float("nan")
    return float(p)


def _perturbation_check(
    prices: pd.DataFrame,
    ytd_returns: pd.DataFrame,
    params: dict,
    base_sharpe: float,
    oos_start: str,
) -> dict:
    if not math.isfinite(base_sharpe) or abs(base_sharpe) < 1e-12:
        return {"min_ratio": float("nan"), "details": []}
    oos_idx = prices.index[prices.index > pd.Timestamp(oos_start)]
    ratios = []
    details = []
    for key, val in params.items():
        for delta in [-0.2, 0.2]:
            if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
                nv = int(round(val * (1 + delta)))
                nv = max(1, nv)
            else:
                nv = float(val * (1 + delta))
            np_ = dict(params)
            np_[key] = nv
            sig = _build_tax_loss_signal(
                prices,
                ytd_returns,
                int(np_["n_days"]),
                int(np_["k"]),
                int(np_["hold_days"]),
                float(np_["vol_target"]),
                VOL_WINDOW,
            )
            sig = sig.reindex(index=prices.loc[oos_idx].index).fillna(0.0)
            m = _run_backtest_daily(prices.loc[oos_idx], sig)["metrics"]["sharpe"]
            ratio = float(m / base_sharpe) if math.isfinite(m) else float("nan")
            ratios.append(ratio)
            details.append({"param": key, "delta": delta, "value": nv, "sharpe": m, "ratio": ratio})
    arr = np.array(ratios, dtype=float)
    arr = arr[np.isfinite(arr)]
    return {"min_ratio": float(arr.min()) if len(arr) else float("nan"), "details": details}


def _worst_regime(daily: pd.Series, window: int = 252) -> float:
    if daily is None or len(daily) < window + 10:
        return float("nan")
    roll = daily.rolling(window).apply(
        lambda x: (
            (x.mean() / x.std(ddof=0) * math.sqrt(DAYS_PER_YEAR)) if x.std(ddof=0) > 0 else np.nan
        ),
        raw=False,
    )
    v = roll.dropna()
    return float(v.min()) if len(v) else float("nan")


def _wf_train_sharpe_simple(
    prices: pd.DataFrame, signal: pd.DataFrame, train_end: str, n_folds: int = 4
) -> float:
    train_idx = prices.index[prices.index <= pd.Timestamp(train_end)]
    if len(train_idx) < n_folds * 30:
        n_folds = 2
    fold_size = len(train_idx) // n_folds
    sharpes = []
    for i in range(n_folds):
        s = i * fold_size
        e = len(train_idx) if i == n_folds - 1 else (i + 1) * fold_size
        idx = train_idx[s:e]
        sig_df = signal.loc[idx].reindex(index=prices.loc[idx].index).fillna(0.0)
        m = _run_backtest_daily(prices.loc[idx], sig_df)["metrics"]
        sharpes.append(m["sharpe"])
    arr = np.array(sharpes, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if len(arr) else float("nan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true", help="tiny grid for local check")
    args = ap.parse_args(argv)

    t0 = time.time()
    art = _artifact_dir(args.out)

    # Download daily price data.
    price_data = {}
    for sym in UNIVERSE:
        price_data[sym] = _download_daily(sym, START, END)

    # Align on common index.
    common_idx = price_data[UNIVERSE[0]].index
    for sym in UNIVERSE[1:]:
        common_idx = common_idx.intersection(price_data[sym].index)
    for sym in UNIVERSE:
        price_data[sym] = price_data[sym].loc[common_idx]

    prices = pd.DataFrame({sym: price_data[sym]["Close"] for sym in UNIVERSE}, index=common_idx)
    prices = prices.dropna()

    # Compute YTD returns at each November month-end.
    november_mask = prices.index.month == 11
    november_dates = prices.index[november_mask]
    # Keep only last trading day of each November
    november_month_ends = []
    for year in sorted(november_dates.year.unique()):
        year_nov = november_dates[november_dates.year == year]
        if len(year_nov) > 0:
            november_month_ends.append(year_nov[-1])
    november_month_ends = pd.DatetimeIndex(november_month_ends)

    ytd_returns = _compute_ytd_returns(prices, november_month_ends)

    # Grid.
    grid = {k: (v[:1] if args.smoke else v) for k, v in GRID.items()}
    combos = []
    for nd in grid["n_days"]:
        for kk in grid["k"]:
            for hd in grid["hold_days"]:
                for vt in grid["vol_target"]:
                    combos.append(
                        {
                            "n_days": nd,
                            "k": kk,
                            "hold_days": hd,
                            "vol_target": vt,
                        }
                    )

    # Train/Val/Test splits by time (50/25/25).
    n = len(prices)
    train_end_idx = n // 2
    val_end_idx = train_end_idx + n // 4
    train_end = str(prices.index[train_end_idx].date())
    val_end = str(prices.index[val_end_idx].date())
    oos_start = str(prices.index[train_end_idx].date())

    rows = []
    for p in combos:
        sig = _build_tax_loss_signal(
            prices,
            ytd_returns,
            int(p["n_days"]),
            int(p["k"]),
            int(p["hold_days"]),
            float(p["vol_target"]),
            VOL_WINDOW,
        )
        sig = sig.reindex(index=prices.index).fillna(0.0)

        # WF train Sharpe.
        wf = _wf_train_sharpe_simple(prices, sig, train_end)

        # Train metrics.
        tr = _run_backtest_daily(
            prices[prices.index <= pd.Timestamp(train_end)],
            sig.loc[prices.index <= pd.Timestamp(train_end)],
        )["metrics"]

        rows.append(
            {**p, "wf_train_sharpe": wf, "train_sharpe": tr["sharpe"], "train_trades": tr["trades"]}
        )

    grid_df = pd.DataFrame(rows).sort_values("wf_train_sharpe", ascending=False)
    grid_df.to_csv(art / "grid.csv", index=False)
    valid = grid_df[np.isfinite(grid_df["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows")
    selected = valid.iloc[0].to_dict()

    # Rebuild selected signal on full sample.
    sig = _build_tax_loss_signal(
        prices,
        ytd_returns,
        int(selected["n_days"]),
        int(selected["k"]),
        int(selected["hold_days"]),
        float(selected["vol_target"]),
        VOL_WINDOW,
    )
    sig = sig.reindex(index=prices.index).fillna(0.0)

    # OOS (Val+Test).
    oos = _slice_metrics(prices, sig, oos_start, END)

    # Benchmark: buy-hold SPY.
    bench_sig = pd.DataFrame({"SPY": 1.0}, index=prices.index)
    bench_oos = _slice_metrics(prices, bench_sig, oos_start, END)

    # Benchmark: equal-weight universe.
    ew_sig = pd.DataFrame({sym: 1.0 / len(UNIVERSE) for sym in UNIVERSE}, index=prices.index)
    ew_oos = _slice_metrics(prices, ew_sig, oos_start, END)

    # Ablations.
    rng = np.random.default_rng(SEED)

    # Random-year control: same calendar window, random years
    oos_mask = prices.index > pd.Timestamp(oos_start)
    active_mask = sig.abs().sum(axis=1) > 0
    n_active_years = int(active_mask[oos_mask].resample("YE").sum().gt(0).sum())
    all_years = prices.index[oos_mask].year.unique()
    if n_active_years > 0 and len(all_years) > 0:
        rand_years = rng.choice(all_years, size=min(n_active_years, len(all_years)), replace=False)
        rand_sig = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        for year in rand_years:
            dec_window = _get_december_window(prices, year, int(selected["n_days"]))
            jan_window = _get_january_hold_days(prices, year, int(selected["hold_days"]))
            active_days = dec_window.union(jan_window)
            for day in active_days:
                if day in rand_sig.index:
                    # Pick random k assets
                    rand_assets = rng.choice(UNIVERSE, size=int(selected["k"]), replace=False)
                    for asset in rand_assets:
                        rand_sig.loc[day, asset] = 1.0
        rand_sig = rand_sig.div(rand_sig.sum(axis=1), axis=0).fillna(0.0)
        # Vol targeting
        basket_ret = prices.pct_change().fillna(0.0).mean(axis=1)
        daily_vol_target = float(selected["vol_target"]) / math.sqrt(DAYS_PER_YEAR)
        realized_vol = basket_ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=0)
        vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)
        rand_sig = rand_sig.mul(vol_scale, axis=0)
        rand_sig = rand_sig.clip(0.0, MAX_POS).fillna(0.0)
        rand_oos = _slice_metrics(prices, rand_sig, oos_start, END)
    else:
        rand_oos = {
            "metrics": {
                "sharpe": float("nan"),
                "trades": 0,
                "profit_factor": float("nan"),
                "max_drawdown": float("nan"),
            }
        }

    # Inverse-signal: long YTD winners in December (direction falsifier)
    inv_sig = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for year in sorted(ytd_returns.index.year.unique()):
        nov_mask = (ytd_returns.index.year == year) & (ytd_returns.index.month == 11)
        nov_dates = ytd_returns.index[nov_mask]
        if len(nov_dates) == 0:
            continue
        nov_date = nov_dates[-1]
        ytd = ytd_returns.loc[nov_date].dropna()
        if len(ytd) < int(selected["k"]):
            continue
        # Rank descending = biggest winners first
        ranked = ytd.sort_values(ascending=False)
        winners = ranked.index[: int(selected["k"])].tolist()

        dec_window = _get_december_window(prices, year, int(selected["n_days"]))
        jan_window = _get_january_hold_days(prices, year, int(selected["hold_days"]))
        active_days = dec_window.union(jan_window)
        for day in active_days:
            if day in inv_sig.index:
                for asset in winners:
                    inv_sig.loc[day, asset] = 1.0

    inv_sig = inv_sig.div(inv_sig.sum(axis=1), axis=0).fillna(0.0)
    # Vol targeting
    basket_ret = prices.pct_change().fillna(0.0).mean(axis=1)
    daily_vol_target = float(selected["vol_target"]) / math.sqrt(DAYS_PER_YEAR)
    realized_vol = basket_ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=0)
    vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)
    inv_sig = inv_sig.mul(vol_scale, axis=0)
    inv_sig = inv_sig.clip(0.0, MAX_POS).fillna(0.0)
    inv_oos = _slice_metrics(prices, inv_sig, oos_start, END)

    oos_m = oos["metrics"]
    ir = _information_ratio(oos["daily"], bench_oos["daily"])
    bp = _benchmark_pvalue(oos["daily"], bench_oos["daily"])
    pert = _perturbation_check(prices, ytd_returns, dict(selected), oos_m["sharpe"], oos_start)
    worst = _worst_regime(oos["daily"])
    wf = _wf_train_sharpe_simple(prices, sig, train_end)
    tr_ref = _slice_metrics(prices, sig, START, train_end)["metrics"]["sharpe"]
    stability = (
        float(oos_m["sharpe"] / tr_ref) if math.isfinite(tr_ref) and tr_ref > 0 else float("nan")
    )

    gates = {
        "sharpe_ge_1": bool(math.isfinite(oos_m["sharpe"]) and oos_m["sharpe"] >= 1.0),
        "trades_ge_50": bool(oos_m["trades"] >= 50),
        "pf_ge_1_3": bool(math.isfinite(oos_m["profit_factor"]) and oos_m["profit_factor"] >= 1.3),
        "maxdd_le_15pct": bool(
            math.isfinite(oos_m["max_drawdown"]) and abs(oos_m["max_drawdown"]) <= 0.15
        ),
        "wf_stability_ge_0_7": bool(math.isfinite(stability) and stability >= 0.7),
        "worst_regime_ge_0_3": bool(math.isfinite(worst) and worst >= 0.3),
        "benchmark_p_le_0_05_and_ir_ge_0": bool(
            math.isfinite(bp) and math.isfinite(ir) and bp <= 0.05 and ir >= 0.0
        ),
        "perturbation_min_ratio_ge_0_5": bool(
            math.isfinite(pert["min_ratio"]) and pert["min_ratio"] >= 0.5
        ),
    }
    verdict = "PASS" if all(gates.values()) else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "symbols": UNIVERSE,
            "start": START,
            "end": END,
            "rows": int(len(prices)),
            "train_end": train_end,
            "val_end": val_end,
        },
        "grid_n": len(combos),
        "selected": {
            k: (int(v) if k in ("n_days", "k", "hold_days") else float(v))
            for k, v in selected.items()
            if k in ("n_days", "k", "hold_days", "vol_target")
        },
        "wf_train_sharpe": wf,
        "train_ref_sharpe": tr_ref,
        "oos_val_test": oos_m,
        "benchmark_buy_hold_oos": bench_oos["metrics"],
        "benchmark_equal_weight_oos": ew_oos["metrics"],
        "ablations": {
            "random_year_oos": rand_oos["metrics"],
            "inverse_signal_oos": inv_oos["metrics"],
        },
        "information_ratio_vs_buy_hold": ir,
        "benchmark_pvalue_one_sided": bp,
        "worst_regime_rolling252_sharpe": worst,
        "wf_stability_oos_over_train": stability,
        "perturbation": {"min_ratio": pert["min_ratio"]},
        "gates": gates,
        "gates_passed": int(sum(1 for v in gates.values() if v)),
        "verdict": verdict,
    }
    (art / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": summary["gates_passed"],
                "selected": summary["selected"],
                "oos_sharpe": oos_m["sharpe"],
                "artifact": str(art),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
