"""NF-20261110-08 / H182 (Cycle 115): Insider Net-Buy Ratio Signal.
Institutional flow / informed trading family (repo-new root family; distinct from
all directional, vol, macro, calendar, dispersion, relmom, carry, and microstructure
families tested in H1-H181).

Mechanism. Corporate insiders (officers, directors, 10% owners) file Form 4 within
two business days of a transaction. Their open-market purchases (code P) and sales
(code S) are aggregated daily by the filing's SEC acceptance timestamp
(`available_at`, point-in-time). The daily net-buy ratio = P / (P + S) measures
insider conviction. A ratio > 0.5 signals net buying; < 0.5 signals net selling.
This is an informed-trading / information-asymmetry mechanism, distinct from all
prior families.

Causal chain (PIT). Form 4 accepted by SEC at `available_at` (UTC, tz-naive);
signal computed on that date; engine applies `shift(1)`, so position at close t
earns return t->t+1. No look-ahead: the transaction date is up to two business
days earlier and is never used for availability.

Observable (past-only, PIT, free/public). SEC EDGAR Form 4 filings via
`src/qtr/data/insider.py`; daily Close prices for universe via yfinance.
Data window 2024-06-01 -> 2026-11-14 (pre-registered in fetch script).

Null (H0). Insider net-buy ratio has no predictive power for next-period
returns of the same issuer beyond random chance after costs.

Pre-registration (Cycle 115, decision-ready before validation outcomes).
NF-ID NF-20261110-08. Hypothesis H182 (next unused after H181; H24/H68-H73/H76-H79
unassigned, not recycled). Universe: 10 pre-registered symbols
(AAPL, MSFT, GOOGL, AMZN, NVDA, META, JPM, XOM, JNJ, WMT). Train 2024-06-01 ->
2025-02-28; Val 2025-03-01 -> 2025-10-31; Test protected 2025-11-01 -> 2026-11-14.
Signal: daily net-buy ratio per symbol on `available_at`, shifted by engine.
Grid: entry_threshold {0.5, 0.6, 0.7} x exit_threshold {0.4, 0.5} x
vol_target {0.10, 0.15, 0.20} x max_pos {0.5, 1.0} = 54 combos. Train-only
4-fold WF selection; Test protected.

Gates (OOS Val+Test, fail-closed): Sharpe>=1.0, trades>=50, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05 with IR>=0,
perturbation min ratio>=0.5.

Ablations: buy-hold equal-weight portfolio benchmark; random-insider control
(same number of signal days, randomly chosen); inverse-signal (fade net buying,
long net selling - direction falsifier); OAT perturbation (+/-20% on numeric
params); Val/Test subperiods; worst-regime rolling-252 Sharpe. No gate weakening.
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
from qtr.data.insider import load_cached_transactions

EXPERIMENT = "nf_20261110_08_insider_signal"
NF_ID = "NF-20261110-08"
HYPOTHESIS = "H182"
START = "2024-06-01"
END = "2026-11-14"
TRAIN_END = "2025-02-28"
VAL_END = "2025-10-31"
MAX_POS = 1.0
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 21

UNIVERSE = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "JPM",
    "XOM",
    "JNJ",
    "WMT",
]

CACHE_DIR = Path(".cache/insider")

GRID = {
    "entry_threshold": [0.5, 0.6, 0.7],
    "exit_threshold": [0.4, 0.5],
    "vol_target": [0.10, 0.15, 0.20],
    "max_pos": [0.5, 1.0],
}


def _artifact_dir(out: str | None) -> Path:
    if out:
        p = Path(out).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    ts = time.strftime("%Y%m%d_%H%M%S")
    p = (Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{ts}").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _download_prices_daily(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """Download daily close prices for symbols."""
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        symbols,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError("yfinance returned empty data")

    # Extract close prices
    if isinstance(raw.columns, pd.MultiIndex):
        closes = {}
        for sym in symbols:
            if sym in raw.columns.levels[0]:
                df = raw[sym]
                if "Close" in df.columns:
                    closes[sym] = df["Close"]
    else:
        # Single symbol case
        closes = {"Close": raw["Close"]} if "Close" in raw.columns else {}

    if not closes:
        raise RuntimeError("no valid close data for any symbol")

    df = pd.DataFrame(closes)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df.dropna(how="all")
    return df


def _load_insider_corpus(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Load cached insider transactions for all symbols."""
    corpus = {}
    for sym in symbols:
        cache_path = CACHE_DIR / f"{sym}.parquet"
        if cache_path.exists():
            tx = load_cached_transactions(cache_path)
            if len(tx) > 0:
                corpus[sym] = tx
    return corpus


def _effective_signal_days(prices: pd.DataFrame, accepted_at: pd.Series) -> pd.Series:
    """Map each filing acceptance instant to the trading day it may first move.

    A Form 4 is public at ``acceptance_datetime`` (UTC), not at midnight of its
    date.  Truncating the timestamp to a calendar date -- which is what
    ``insider_net_buy_ratio`` does, because it aggregates on the *date* -- lets a
    filing accepted after the cash close act on that same session's close, and
    one accepted on a Saturday act on Friday.  Both read the future.

    The mapping is therefore the first trading day whose regular-session close
    (16:00 America/New_York) is at or after the acceptance instant.  A filing
    accepted at 09:00 ET on day *t* is actionable at day *t*'s close; one
    accepted at 18:58 ET on day *t* is actionable at day *t+1*'s close; a
    weekend filing is actionable at the next session's close.

    Rows whose acceptance falls after the last available close cannot be acted
    on and are dropped (``NaN``).

    Args:
        prices: Price panel whose index is the trading-day calendar.
        accepted_at: Filing acceptance instants.  Timezone-naive values are
            interpreted as UTC (the EDGAR convention).

    Returns:
        A UTC-naive ``datetime64`` Series aligned to ``accepted_at``, holding the
        effective trading day (normalised to midnight) or ``NaT``.
    """
    days = pd.DatetimeIndex(prices.index)
    if len(days) == 0 or len(accepted_at) == 0:
        return pd.Series(pd.NaT, index=accepted_at.index, dtype="datetime64[ns]")

    stamps = pd.DatetimeIndex(pd.to_datetime(accepted_at))
    if stamps.tz is None:
        stamps = stamps.tz_localize("UTC")
    else:
        stamps = stamps.tz_convert("UTC")
    closes = days.tz_localize("America/New_York") + pd.Timedelta(hours=16)
    positions = closes.searchsorted(stamps.to_numpy(), side="left")
    effective = pd.Series(pd.NaT, index=accepted_at.index, dtype="datetime64[ns]")
    in_range = positions < len(days)
    if in_range.any():
        effective.iloc[np.flatnonzero(in_range)] = days[positions[in_range]]
    return effective


def _net_buy_ratio_by_signal_day(prices: pd.DataFrame, tx: pd.DataFrame) -> pd.Series:
    """Open-market net-buy ratio per *effective* trading day for one symbol.

    Only Form 4 open-market rows (code ``P`` purchase, ``S`` sale) are counted,
    matching ``insider_net_buy_ratio``; the difference is the day each row is
    attributed to (see :func:`_effective_signal_days`).  Several filings can map
    to one trading day (a weekend batch), so the ratio is recomputed from the
    pooled buy/sell counts rather than averaging daily ratios.

    Returns:
        A float Series indexed by effective trading day, ascending.  Empty when
        no open-market row is actionable within the price window.
    """
    open_market = tx[tx["transaction_code"].isin(["P", "S"])].copy()
    open_market["available_at"] = pd.to_datetime(open_market["available_at"])
    open_market = open_market[open_market["available_at"].notna()]
    if len(open_market) == 0:
        return pd.Series(dtype=float)

    open_market["effective_day"] = _effective_signal_days(prices, open_market["available_at"])
    open_market = open_market[open_market["effective_day"].notna()]
    if len(open_market) == 0:
        return pd.Series(dtype=float)

    grouped = open_market.groupby("effective_day")["transaction_code"].agg(
        rows="size", buys=lambda codes: int((codes == "P").sum())
    )
    grouped = grouped.sort_index()
    return grouped["buys"] / grouped["rows"]


def _hysteresis(signal: pd.Series, entry_threshold: float, exit_threshold: float) -> pd.Series:
    """Long-only hysteresis on a signal series: enter at/above entry, exit at/below exit."""
    current_pos = 0.0
    positions = pd.Series(0.0, index=signal.index)
    for i, (date, value) in enumerate(signal.items()):
        if current_pos == 0.0:
            if value >= entry_threshold:
                current_pos = 1.0
        elif current_pos == 1.0:
            if value <= exit_threshold:
                current_pos = 0.0
        positions.iloc[i] = current_pos
    return positions


def _compute_daily_signals(
    prices: pd.DataFrame,
    corpus: dict[str, pd.DataFrame],
    entry_threshold: float,
    exit_threshold: float,
) -> pd.DataFrame:
    """Compute daily target weights from insider net-buy ratio.

    A filing's net-buy ratio is attributed to the first trading day whose close
    is at or after its EDGAR acceptance instant (see
    :func:`_effective_signal_days`), then forward-filled until the next filing.
    Days before a symbol's first actionable filing carry **no** ratio: the
    hysteresis input is ``NaN``, which is treated as "no signal" and holds the
    position flat.  Filling that warm-up with a neutral constant instead would
    be a silent look-ahead for any entry threshold at or below the constant
    (the pre-registered ``entry_threshold`` grid includes exactly 0.5).
    """
    signal = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    for sym in prices.columns:
        if sym not in corpus:
            continue
        ratios = _net_buy_ratio_by_signal_day(prices, corpus[sym])
        if len(ratios) == 0:
            continue

        # Forward-fill the ratio across trading days; the leading NaNs are the
        # pre-first-filing warm-up and stay NaN on purpose.
        aligned = ratios.reindex(prices.index).ffill()
        signal[sym] = _hysteresis(aligned, entry_threshold, exit_threshold)

    return signal


def _apply_vol_targeting(
    signal: pd.DataFrame,
    prices: pd.DataFrame,
    vol_target: float,
    vol_window: int,
    max_pos: float,
) -> pd.DataFrame:
    """Scale positions by inverse realized volatility to target annualized vol."""
    if vol_target <= 0:
        return signal.clip(-max_pos, max_pos).fillna(0.0)

    # Compute portfolio returns if fully invested (equal weight across active positions)
    # For per-symbol vol targeting, scale each symbol independently
    ret = prices.pct_change().fillna(0.0)
    daily_vol_target = vol_target / math.sqrt(DAYS_PER_YEAR)

    scaled_signal = signal.copy()
    for sym in signal.columns:
        sym_ret = ret[sym] if sym in ret.columns else pd.Series(0.0, index=prices.index)
        realized_vol = sym_ret.rolling(vol_window, min_periods=vol_window).std(ddof=0)
        vol_scale = (daily_vol_target / realized_vol.replace(0, np.nan)).clip(0.0, 3.0)
        scaled_signal[sym] = (signal[sym] * vol_scale).clip(-max_pos, max_pos).fillna(0.0)

    return scaled_signal


def _cfg(max_pos: float) -> BacktestConfig:
    return BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=max_pos,
        max_leverage=1.0,
        allow_short=False,
    )


def _run_backtest_daily(prices: pd.DataFrame, signal: pd.DataFrame, max_pos: float) -> dict:
    res = run_backtest(prices=prices, signals=signal, config=_cfg(max_pos))
    m = res.metrics
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
        "equity_end": float(res.equity_curve.iloc[-1]) if len(res.equity_curve) else float("nan"),
    }
    return {
        "metrics": out,
        "equity": res.equity_curve,
        "daily": res.equity_curve.pct_change().dropna(),
        "returns": res.returns,
        "trades": res.trades,
    }


def _slice_metrics(
    prices: pd.DataFrame,
    signal: pd.DataFrame,
    start: str,
    end: str,
    max_pos: float,
) -> dict:
    idx = prices.index[(prices.index >= pd.Timestamp(start)) & (prices.index <= pd.Timestamp(end))]
    if len(idx) < 30:
        return {
            "metrics": {"sharpe": float("nan"), "trades": 0},
            "equity": pd.Series(dtype=float),
            "daily": pd.Series(dtype=float),
        }
    return _run_backtest_daily(prices.loc[idx], signal.loc[idx], max_pos)


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
    corpus: dict[str, pd.DataFrame],
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
        if key not in ("entry_threshold", "exit_threshold", "vol_target", "max_pos"):
            continue
        for delta in [-0.2, 0.2]:
            if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
                nv = int(round(val * (1 + delta)))
                nv = max(1, nv)
            else:
                nv = float(val * (1 + delta))
            np_ = dict(params)
            np_[key] = nv

            sig = _compute_daily_signals(
                prices, corpus, np_["entry_threshold"], np_["exit_threshold"]
            )
            sig = _apply_vol_targeting(sig, prices, np_["vol_target"], VOL_WINDOW, np_["max_pos"])
            sig = sig.reindex(index=prices.loc[oos_idx].index).fillna(0.0)

            m = _run_backtest_daily(prices.loc[oos_idx], sig, np_["max_pos"])["metrics"]["sharpe"]
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
    prices: pd.DataFrame, signal: pd.DataFrame, train_end: str, max_pos: float, n_folds: int = 4
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
        m = _run_backtest_daily(prices.loc[idx], sig_df, max_pos)["metrics"]
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

    # Download price data
    prices = _download_prices_daily(UNIVERSE, START, END)

    # Load insider corpus
    corpus = _load_insider_corpus(UNIVERSE)

    # Save corpus info for transparency
    corpus_info = {sym: len(tx) for sym, tx in corpus.items()}
    (art / "corpus_info.json").write_text(json.dumps(corpus_info, indent=2) + "\n")

    # Grid
    grid = {k: (v[:1] if args.smoke else v) for k, v in GRID.items()}
    combos = []
    for et in grid["entry_threshold"]:
        for ex in grid["exit_threshold"]:
            for vt in grid["vol_target"]:
                for mp in grid["max_pos"]:
                    combos.append(
                        {
                            "entry_threshold": et,
                            "exit_threshold": ex,
                            "vol_target": vt,
                            "max_pos": mp,
                        }
                    )

    # Train/Val/Test splits by time
    train_end = TRAIN_END
    val_end = VAL_END
    oos_start = TRAIN_END  # OOS = Val + Test

    rows = []
    for p in combos:
        sig = _compute_daily_signals(prices, corpus, p["entry_threshold"], p["exit_threshold"])
        sig = _apply_vol_targeting(sig, prices, p["vol_target"], VOL_WINDOW, p["max_pos"])
        sig = sig.reindex(index=prices.index).fillna(0.0)

        # WF train Sharpe
        wf = _wf_train_sharpe_simple(prices, sig, train_end, p["max_pos"])

        # Train metrics
        tr = _run_backtest_daily(
            prices[prices.index <= pd.Timestamp(train_end)],
            sig.loc[prices.index <= pd.Timestamp(train_end)],
            p["max_pos"],
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

    # Rebuild selected signal on full sample
    sig = _compute_daily_signals(
        prices, corpus, selected["entry_threshold"], selected["exit_threshold"]
    )
    sig = _apply_vol_targeting(sig, prices, selected["vol_target"], VOL_WINDOW, selected["max_pos"])
    sig = sig.reindex(index=prices.index).fillna(0.0)

    # OOS (Val+Test)
    oos = _slice_metrics(prices, sig, oos_start, END, selected["max_pos"])

    # Benchmark: equal-weight buy-hold portfolio
    bench_sig = pd.DataFrame(1.0 / len(prices.columns), index=prices.index, columns=prices.columns)
    bench_oos = _slice_metrics(prices, bench_sig, oos_start, END, 1.0)

    # Ablations
    rng = np.random.default_rng(SEED)

    # Random-insider control: same number of active signal days, randomly chosen
    oos_mask = prices.index > pd.Timestamp(oos_start)
    active_mask = sig.abs().sum(axis=1) > 0
    active_dates = prices.index[oos_mask & active_mask]
    n_active = len(active_dates)
    all_dates = prices.index[oos_mask]

    if n_active > 0 and len(all_dates) > n_active:
        rand_dates = rng.choice(all_dates, size=n_active, replace=False)
        rand_sig = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        # Randomize: same number of active days, random dates, then the same
        # hysteresis. The random series is a synthetic control, so it is drawn
        # directly on trading days (no filing timestamps to align).
        rand_aligned = pd.Series(np.nan, index=prices.index)
        rand_aligned.loc[rand_dates] = rng.uniform(0.0, 1.0, size=n_active)
        rand_aligned = rand_aligned.ffill()
        rand_pos = _hysteresis(rand_aligned, selected["entry_threshold"], selected["exit_threshold"])
        for sym in prices.columns:
            if sym in corpus:
                rand_sig[sym] = rand_pos

        rand_sig = _apply_vol_targeting(
            rand_sig, prices, selected["vol_target"], VOL_WINDOW, selected["max_pos"]
        )
        rand_oos = _slice_metrics(prices, rand_sig, oos_start, END, selected["max_pos"])
    else:
        rand_oos = {
            "metrics": {
                "sharpe": float("nan"),
                "trades": 0,
                "profit_factor": float("nan"),
                "max_drawdown": float("nan"),
            }
        }

    # Inverse-signal: fade net buying, long net selling (direction falsifier)
    inv_sig = _compute_daily_signals(
        prices,
        corpus,
        1.0 - selected["exit_threshold"],  # Inverted thresholds
        1.0 - selected["entry_threshold"],
    )
    inv_sig = _apply_vol_targeting(
        inv_sig, prices, selected["vol_target"], VOL_WINDOW, selected["max_pos"]
    )
    inv_sig = inv_sig.reindex(index=prices.index).fillna(0.0)
    inv_oos = _slice_metrics(prices, inv_sig, oos_start, END, selected["max_pos"])

    oos_m = oos["metrics"]
    ir = _information_ratio(oos["daily"], bench_oos["daily"])
    bp = _benchmark_pvalue(oos["daily"], bench_oos["daily"])
    pert = _perturbation_check(prices, corpus, dict(selected), oos_m["sharpe"], oos_start)
    worst = _worst_regime(oos["daily"])
    wf = _wf_train_sharpe_simple(prices, sig, train_end, selected["max_pos"])
    tr_ref = _slice_metrics(prices, sig, START, train_end, selected["max_pos"])["metrics"]["sharpe"]
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
            "corpus_rows": {k: int(v) for k, v in corpus_info.items()},
        },
        "grid_n": len(combos),
        "selected": {
            k: (int(v) if k in ("max_pos",) and v == int(v) else float(v) if k != "max_pos" else v)
            for k, v in selected.items()
            if k in ("entry_threshold", "exit_threshold", "vol_target", "max_pos")
        },
        "wf_train_sharpe": wf,
        "train_ref_sharpe": tr_ref,
        "oos_val_test": oos_m,
        "benchmark_equal_weight_oos": bench_oos["metrics"],
        "ablations": {
            "random_insider_oos": rand_oos["metrics"],
            "inverse_signal_oos": inv_oos["metrics"],
        },
        "information_ratio_vs_equal_weight": ir,
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
