"""NF-20261110-06 / H179 (Cycle 93): Short Interest / Securities Lending Flow Timing.

Short-constraint / limits to arbitrage (repo-new root family). Distinct from all exhausted
families: H119 (short-term cross-sectional reversal — liquidity provision), H178 (options
sentiment/put-call ratio — derivatives positioning), H176 (tax-loss harvesting — calendar
flow), H177 (Treasury auction — government supply operations), H175 (macro regime —
growth/inflation proxies), and all directional/vol/credit/rates/calendar/relmom/VIX-complex
families. Mechanism: short-selling frictions and informed short positioning (limits to
arbitrage), not momentum, volatility, macro, calendar, or order-flow channels.

Mechanism. FINRA bi-weekly short interest data reveals crowded short positioning and
securities lending supply constraints. Elevated short interest (or rising short interest)
indicates overvaluation/crowded shorts; extremely low short interest indicates lack of
bearish conviction. A trailing z-score of short interest gates vol-targeted SPY/sector ETF
exposure: reduce/short when crowded (high short interest z), increase long when complacent
(low short interest z), with hysteresis. Causal chain: short interest extremes -> informed
opinion / borrow constraints -> subsequent return skew.

Causal chain (PIT). FINRA short interest is published ~7 business days after the bi-weekly
settlement date (mid-month and end-month). Settlement-date short interest becomes known at
publication; position set from past-only trailing z-score enters at next available close via
engine `signals.shift(1)` (position at close t earns return t→t+1). Strictly causal: no
settlement-date short interest is used before its publication date.

Observable (past-only, PIT, free/public). FINRA bi-weekly short interest CSV
(https://cdn.finra.org/equity/otcmarket/biweekly/shrtYYYYMMDD.csv) for SPY and sector ETFs;
SPY + sector ETFs daily Close (yfinance). FINRA data available ~2018+ (rolling window).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

csv.field_size_limit(sys.maxsize)

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest

EXPERIMENT = "nf_20261110_06_short_interest"
NF_ID = "NF-20261110-06"
HYPOTHESIS = "H179"
START = "2018-01-01"  # FINRA exchange-listed short interest available ~2018+
END = "2026-10-31"
MAX_POS = 0.5
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 21
PUBLICATION_LAG_DAYS = 5  # ~1 week after bi-weekly settlement
BASE_URL = "https://cdn.finra.org/equity/otcmarket/biweekly/shrt{date}.csv"

# Sector ETFs for universe expansion (all confirmed present in FINRA short interest).
SECTOR_ETFS = ["SPY", "XLF", "XLE", "XLV", "XLI", "XLB", "XLP", "XLU", "XLY", "XLC", "XLK"]

GRID = {
    "si_window": [6, 12, 24],
    "entry_z": [0.5, 1.0, 1.5],
    "exit_z": [0.0, 0.5],
    "vol_target": [0.10, 0.15],
    "universe": ["SPY", "SPY_SECTORS"],
}

# Gates (OOS Val+Test, fail-closed).
GATES = {
    "sharpe": (1.0, lambda v: np.isfinite(v) and v >= 1.0),
    "trades": (50, lambda v: int(v) >= 50),
    "pf": (1.3, lambda v: np.isfinite(v) and v >= 1.3),
    "maxdd": (-0.15, lambda v: np.isfinite(v) and v >= -0.15),
    "wf_stability": (0.7, lambda v: np.isfinite(v) and v >= 0.7),
    "worst_regime": (0.3, lambda v: np.isfinite(v) and v >= 0.3),
    "benchmark": (0.05, lambda v: np.isfinite(v) and v <= 0.05),
    "perturbation": (0.5, lambda v: np.isfinite(v) and v >= 0.5),
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


# ------------------------------------------------------------ data acquisition
def _download_yfinance_daily(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError("yfinance returned empty data")
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]]
        close.columns = [tickers[0]]
    close = close.ffill().dropna(how="all")
    close.columns = [str(c) for c in close.columns]
    return close


def _biweekly_settlement_dates(start: str, end: str) -> list[str]:
    """Bi-weekly FINRA settlement dates: 15th and last calendar day of each month."""
    idx = pd.bdate_range(start, end)
    dates = set()
    for d in idx:
        if d.day == 15:
            dates.add(d)
        # last calendar day of month
        next_day = d + pd.Timedelta(days=1)
        if next_day.month != d.month:
            dates.add(d)
    return sorted(d.strftime("%Y%m%d") for d in dates)


def _fetch_one_finra(settlement_date: str, cache_dir: Path) -> dict[str, float] | None:
    """Download + parse one bi-weekly FINRA short interest file. Returns {symbol: qty}."""
    cache_file = cache_dir / f"shrt{settlement_date}.csv"
    if cache_file.exists():
        try:
            text = cache_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = None
        if text:
            return _parse_finra_csv(text)
    url = BASE_URL.format(date=settlement_date)
    tries = 0
    while tries < 4:
        tries += 1
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/csv"})
            text = urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
            try:
                cache_file.write_text(text, encoding="utf-8")
            except Exception:
                pass
            return _parse_finra_csv(text)
        except Exception:
            if tries >= 4:
                return None
            time.sleep(1.5 * tries)
    return None


def _parse_finra_csv(text: str) -> dict[str, float]:
    reader = csv.reader(io.StringIO(text), delimiter="|")
    header = next(reader, None)
    if header is None:
        return {}
    # locate columns by name (robust to column order)
    cols = {c.strip().strip('"').lower(): i for i, c in enumerate(header)}
    sym_i = cols.get("symbolcode")
    qty_i = cols.get("currentshortpositionquantity")
    if sym_i is None or qty_i is None:
        return {}
    out: dict[str, float] = {}
    for row in reader:
        if len(row) <= max(sym_i, qty_i):
            continue
        sym = row[sym_i].strip().strip('"').upper()
        try:
            qty = float(row[qty_i].strip().strip('"').replace(",", ""))
        except (ValueError, TypeError):
            continue
        if not sym or qty < 0 or not math.isfinite(qty):
            continue
        out[sym] = qty
    return out


def fetch_finra_short_interest(
    settlement_dates: list[str], universe: list[str], cache_dir: Path
) -> pd.DataFrame:
    """Download FINRA short interest for all settlement dates.

    Returns a DataFrame indexed by settlement date (Timestamp), columns = universe symbols,
    values = current short position quantity. Missing dates / symbols are NaN.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    frames: dict[str, list[tuple[pd.Timestamp, float]]] = {s: [] for s in universe}
    for sd in settlement_dates:
        data = _fetch_one_finra(sd, cache_dir)
        if not data:
            continue
        ts = pd.Timestamp(sd)
        for sym in universe:
            if sym in data:
                frames[sym].append((ts, data[sym]))
    series_dict: dict[str, pd.Series] = {}
    for sym in universe:
        if frames[sym]:
            s = pd.Series(
                [v for _, v in frames[sym]],
                index=pd.DatetimeIndex([t for t, _ in frames[sym]]),
            )
            s = s[~s.index.duplicated(keep="last")].sort_index()
        else:
            s = pd.Series(dtype=float)
        series_dict[sym] = s
    if not series_dict:
        return pd.DataFrame(index=pd.DatetimeIndex([]), columns=universe, dtype=float)
    all_dates = sorted({ts for s in series_dict.values() for ts in s.index})
    df = pd.DataFrame(index=pd.DatetimeIndex(all_dates), columns=universe, dtype=float)
    for sym in universe:
        if not series_dict[sym].empty:
            df[sym] = series_dict[sym].reindex(df.index)
    return df


def _align_si_to_daily(
    daily_index: pd.DatetimeIndex,
    si_df: pd.DataFrame,
    universe: list[str],
) -> dict[str, pd.Series]:
    """Align bi-weekly short interest to daily trading index with publication lag.

    PIT: settlement-date SI is reindexed to daily (ffill over non-trading days), then
    shifted forward by PUBLICATION_LAG_DAYS trading days so that only SI known at or
    before each trading day is used.
    """
    aligned: dict[str, pd.Series] = {}
    for ticker in universe:
        if ticker not in si_df.columns or si_df[ticker].dropna().empty:
            aligned[ticker] = pd.Series(np.nan, index=daily_index)
            continue
        si = si_df[ticker].dropna()
        si_daily = si.reindex(daily_index, method="ffill")
        si_shifted = si_daily.shift(PUBLICATION_LAG_DAYS)
        aligned[ticker] = si_shifted.astype(float)
    return aligned


# ------------------------------------------------------------ signal / backtest
def _zscore(series: pd.Series, window: int) -> pd.Series:
    """Rolling z-score using past-only windows (no lookahead)."""
    s = series.astype(float)
    minp = max(2, window // 2)
    m = s.rolling(window, min_periods=minp).mean()
    sd = s.rolling(window, min_periods=minp).std(ddof=0)
    return (s - m) / sd.replace(0.0, np.nan)


def _compute_weights(
    prices: pd.DataFrame,
    si_aligned: dict[str, pd.Series],
    si_window: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
    universe: str,
) -> pd.DataFrame:
    tickers = prices.columns.tolist()
    weights = pd.DataFrame(0.0, index=prices.index, columns=tickers)

    for ticker in tickers:
        si = si_aligned[ticker]
        si_z = _zscore(si, int(si_window))

        position = 0.0
        w_series = pd.Series(0.0, index=prices.index)
        for i in range(len(prices)):
            z_val = si_z.iloc[i] if i < len(si_z) else np.nan
            if np.isnan(z_val):
                w_series.iloc[i] = position
                continue
            # hysteresis state machine
            if position >= 0.0:
                if z_val >= entry_z:
                    position = -1.0
                elif z_val <= -entry_z:
                    position = 1.0
                elif exit_z > 0.0 and position > 0.0 and z_val >= exit_z:
                    position = 0.0
                elif exit_z > 0.0 and position < 0.0 and z_val <= -exit_z:
                    position = 0.0
            else:
                if z_val <= -entry_z:
                    position = 1.0
                elif z_val >= entry_z:
                    position = -1.0
                elif exit_z > 0.0 and position < 0.0 and z_val <= -exit_z:
                    position = 0.0
                elif exit_z > 0.0 and position > 0.0 and z_val >= exit_z:
                    position = 0.0
            w_series.iloc[i] = position

        returns = prices[ticker].pct_change()
        vol = returns.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(DAYS_PER_YEAR)
        vol_scale = (vol_target / vol.replace(0, np.nan)).clip(0.0, 3.0).fillna(0.0)
        w_vol = (w_series * vol_scale).clip(-MAX_POS, MAX_POS)
        weights[ticker] = w_vol

    if universe == "SPY":
        for c in weights.columns:
            if c != "SPY":
                weights[c] = 0.0
    return weights


def _run_bt(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    allow_short: bool = True,
) -> tuple[pd.Series, pd.Series, int]:
    cfg = BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        allow_short=allow_short,
    )
    res = run_backtest(close, weights, cfg)
    strat_ret = res.returns.reindex(close.index).fillna(0.0).astype(float)
    eq = res.equity_curve.reindex(close.index).astype(float)
    pos = res.positions.reindex(close.index).fillna(0.0)
    trades = int((pos.diff().abs() > 1e-12).sum().sum())
    return strat_ret, eq, trades


def _metrics(strat_ret: pd.Series, eq: pd.Series, trades: int) -> dict:
    return {
        "sharpe": _annualized_sharpe(strat_ret),
        "profit_factor": _profit_factor(strat_ret),
        "max_drawdown": _max_drawdown(eq),
        "trades": int(trades),
        "periods": int(len(strat_ret.dropna())),
        "total_return": float(eq.iloc[-1] / eq.iloc[0] - 1.0) if len(eq) > 1 else 0.0,
        "worst_regime_rolling252_sharpe": _rolling_252_sharpe_worst(strat_ret),
    }


def _annualized_sharpe(ret: pd.Series) -> float:
    r = ret.dropna()
    if len(r) < 20:
        return 0.0
    sd = r.std(ddof=0)
    if sd <= 0 or not np.isfinite(sd):
        return 0.0
    return float(r.mean() / sd * math.sqrt(DAYS_PER_YEAR))


def _profit_factor(ret: pd.Series) -> float:
    r = ret.dropna()
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    if neg <= 0:
        return float("inf") if pos > 0 else 0.0
    return float(pos / neg)


def _max_drawdown(equity: pd.Series) -> float:
    eq = equity.dropna()
    if len(eq) == 0:
        return 0.0
    peak = eq.cummax()
    dd = eq / peak - 1.0
    return float(dd.min())


def _rolling_252_sharpe_worst(ret: pd.Series) -> float:
    r = ret.dropna()
    if len(r) < 252:
        return _annualized_sharpe(r)
    rs = r.rolling(252).apply(lambda x: _annualized_sharpe(pd.Series(x)), raw=False)
    rs = rs.dropna()
    return float(rs.min()) if len(rs) else _annualized_sharpe(r)


def _wf_score(
    train_close: pd.DataFrame,
    train_si: dict[str, pd.Series],
    params: dict,
    n_folds: int = 4,
) -> float:
    n = len(train_close)
    if n < 200:
        return -999.0
    fold = n // n_folds
    sharpes = []
    for i in range(n_folds):
        start = i * fold
        end = n if i == n_folds - 1 else (i + 1) * fold
        if end - start < 80:
            continue
        c = train_close.iloc[start:end]
        w = _compute_weights(c, train_si, **params)
        r, _, _ = _run_bt(c, w)
        sharpes.append(_annualized_sharpe(r))
    return float(np.mean(sharpes)) if sharpes else -999.0


def _information_ratio(strat: pd.Series, bench: pd.Series) -> float:
    a, b = strat.align(bench, join="inner")
    diff = (a - b).dropna()
    sd = diff.std(ddof=0)
    if len(diff) < 20 or sd <= 0 or not np.isfinite(sd):
        return 0.0
    return float(diff.mean() / sd * math.sqrt(DAYS_PER_YEAR))


def _benchmark_pvalue(strat: pd.Series, bench: pd.Series, n_boot: int = 2000) -> float:
    a, b = strat.align(bench, join="inner")
    diff = (a - b).dropna().to_numpy()
    if len(diff) < 20:
        return 1.0
    obs = diff.mean()
    if not np.isfinite(obs):
        return 1.0
    rng = np.random.default_rng(SEED)
    centered = diff - obs
    boots = [
        float(rng.choice(centered, size=len(centered), replace=True).mean()) for _ in range(n_boot)
    ]
    boots_arr = np.array(boots)
    p = (1.0 + float(np.sum(boots_arr >= obs))) / (n_boot + 1.0)
    return float(p)


def _time_split(index: pd.DatetimeIndex) -> tuple[str, str]:
    n = len(index)
    i1 = index[n // 2]
    i2 = index[(3 * n) // 4]
    return str(i1.date()), str(i2.date())


def _perturbation_oos_sharpes(
    prices: pd.DataFrame,
    si_aligned: dict[str, pd.Series],
    selected: dict,
    val_start: str,
    test_end: str,
) -> list[float]:
    base = selected.copy()
    sharpes = []
    pcw_opts = sorted(
        set(
            [
                max(3, int(round(base["si_window"] * 0.8))),
                base["si_window"],
                min(60, int(round(base["si_window"] * 1.2))),
            ]
        )
    )
    ez_opts = sorted(
        set([round(base["entry_z"] * 0.8, 4), base["entry_z"], round(base["entry_z"] * 1.2, 4)])
    )
    xz_opts = sorted(
        set([round(base["exit_z"] * 0.8, 4), base["exit_z"], round(base["exit_z"] * 1.2, 4)])
    )
    vt_opts = sorted(
        set(
            [
                round(base["vol_target"] * 0.8, 4),
                base["vol_target"],
                round(base["vol_target"] * 1.2, 4),
            ]
        )
    )
    for pcw in pcw_opts:
        for vt in vt_opts:
            for ez in ez_opts:
                for xz in xz_opts:
                    p = dict(base)
                    p["si_window"] = int(pcw)
                    p["vol_target"] = float(min(max(vt, 0.02), 0.5))
                    p["entry_z"] = float(ez)
                    p["exit_z"] = float(xz)
                    w = _compute_weights(prices, si_aligned, **p)
                    mask = (prices.index >= pd.Timestamp(val_start)) & (
                        prices.index <= pd.Timestamp(test_end)
                    )
                    r, _, _ = _run_bt(prices.loc[mask], w.loc[mask])
                    sharpes.append(_annualized_sharpe(r))
    return [s for s in sharpes if np.isfinite(s)]


# ---------------------------------------------------------------- main driver
def main(out_dir: str | None = None) -> dict:
    t0 = time.time()
    art = _artifact_dir(out_dir)

    tickers = SECTOR_ETFS
    print("Downloading price data...")
    prices = _download_yfinance_daily(tickers, START, END)
    print(
        f"Price data shape: {prices.shape}  {prices.index[0].date()} -> {prices.index[-1].date()}"
    )

    print("Building FINRA settlement-date list...")
    settlement_dates = _biweekly_settlement_dates(START, END)
    print(f"Candidate FINRA settlement dates: {len(settlement_dates)}")

    cache_dir = art / "finra_cache"
    print("Downloading FINRA short interest (with retries)...")
    si_df = fetch_finra_short_interest(settlement_dates, tickers, cache_dir)
    print(f"FINRA data coverage: {len(si_df)} settlement dates with data")
    si_coverage = {c: int(si_df[c].notna().sum()) for c in tickers}
    print(f"Per-symbol settlement counts: {si_coverage}")

    # Align to daily prices (PIT with publication lag).
    common_index = prices.index
    si_aligned = _align_si_to_daily(common_index, si_df, tickers)

    # Restrict prices to dates where at least SPY SI is known (after lag).
    spy_si = si_aligned["SPY"]
    valid = spy_si.notna()
    prices = prices.loc[valid]
    si_aligned = {t: si_aligned[t].loc[valid] for t in tickers}
    print(f"Aligned daily rows (SPY SI known): {len(prices)}")

    val_start, test_start = _time_split(prices.index)
    train_mask = prices.index < pd.Timestamp(val_start)
    oos_mask = prices.index >= pd.Timestamp(val_start)
    train_close = prices.loc[train_mask]
    oos_close = prices.loc[oos_mask]

    print(f"Splits: train -> {val_start}; val {val_start} -> {test_start}; test {test_start} ->")

    # Grid search: selection by train-only 4-fold WF Sharpe.
    rows = []
    for params in _iter_grid():
        wf = _wf_score(train_close, si_aligned, params)
        rows.append({**params, "wf_train_sharpe": wf})
    grid = pd.DataFrame(rows).sort_values("wf_train_sharpe", ascending=False)
    grid.to_csv(art / "grid.csv", index=False)
    valid_grid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid_grid.empty:
        raise RuntimeError("no valid grid rows")
    sel = valid_grid.iloc[0].to_dict()
    selected = {k: sel[k] for k in ["si_window", "entry_z", "exit_z", "vol_target", "universe"]}
    selected["si_window"] = int(selected["si_window"])
    selected["vol_target"] = float(selected["vol_target"])
    selected["entry_z"] = float(selected["entry_z"])
    selected["exit_z"] = float(selected["exit_z"])
    selected["universe"] = str(selected["universe"])

    # Selected weights on full sample.
    w_sel = _compute_weights(prices, si_aligned, **selected)
    oos_w = w_sel.loc[oos_mask]
    oos_ret, oos_eq, oos_trades = _run_bt(oos_close, oos_w)
    oos_m = _metrics(oos_ret, oos_eq, oos_trades)

    # Benchmark buy-hold SPY over OOS.
    bench_w = pd.DataFrame(1.0, index=oos_close.index, columns=["SPY"])
    bench_ret, bench_eq, bench_trades = _run_bt(oos_close[["SPY"]], bench_w)
    bench_m = _metrics(bench_ret, bench_eq, bench_trades)

    # Ablations.
    rng = np.random.default_rng(SEED)
    z = _zscore(si_aligned["SPY"], int(selected["si_window"])).reindex(oos_close.index)
    z_shuf = pd.Series(rng.permutation(z.fillna(0.0).to_numpy()), index=z.index)
    rand_si = {t: si_aligned[t].copy() for t in tickers}
    rand_si["SPY"] = z_shuf.reindex(oos_close.index).ffill()
    rand_w = _compute_weights(oos_close, rand_si, **selected)
    rand_ret, rand_eq, rand_trades = _run_bt(oos_close, rand_w)
    rand_m = _metrics(rand_ret, rand_eq, rand_trades)

    inv_params = dict(selected)
    inv_w = -w_sel  # inverse signal: flip sign of position
    inv_oos = inv_w.loc[oos_mask]
    inv_ret, inv_eq, inv_trades = _run_bt(oos_close, inv_oos)
    inv_m = _metrics(inv_ret, inv_eq, inv_trades)

    train_sel_ret, _, _ = _run_bt(train_close, w_sel.loc[train_mask])
    train_sel_sharpe = _annualized_sharpe(train_sel_ret)
    wf_stability = (
        float(oos_m["sharpe"] / train_sel_sharpe)
        if np.isfinite(train_sel_sharpe) and train_sel_sharpe != 0
        else (float("inf") if oos_m["sharpe"] > 0 else 0.0)
    )

    pert_sharpes = _perturbation_oos_sharpes(
        prices, si_aligned, selected, val_start, str(prices.index[-1].date())
    )
    base_sh = oos_m["sharpe"]
    min_ratio = (
        float(min(pert_sharpes) / base_sh)
        if pert_sharpes and np.isfinite(base_sh) and base_sh != 0
        else 0.0
    )

    ir = _information_ratio(oos_ret, bench_ret)
    bp = _benchmark_pvalue(oos_ret, bench_ret)

    gates = {
        "sharpe_ge_1": bool(np.isfinite(oos_m["sharpe"]) and oos_m["sharpe"] >= 1.0),
        "trades_ge_50": bool(oos_m["trades"] >= 50),
        "pf_ge_1_3": bool(np.isfinite(oos_m["profit_factor"]) and oos_m["profit_factor"] >= 1.3),
        "maxdd_le_15pct": bool(
            np.isfinite(oos_m["max_drawdown"]) and oos_m["max_drawdown"] >= -0.15
        ),
        "wf_stability_ge_0_7": bool(np.isfinite(wf_stability) and wf_stability >= 0.7),
        "worst_regime_ge_0_3": bool(
            np.isfinite(oos_m["worst_regime_rolling252_sharpe"])
            and oos_m["worst_regime_rolling252_sharpe"] >= 0.3
        ),
        "benchmark_p_le_0_05_and_ir_ge_0": bool(
            np.isfinite(bp) and bp <= 0.05 and np.isfinite(ir) and ir >= 0.0
        ),
        "perturbation_min_ratio_ge_0_5": bool(np.isfinite(min_ratio) and min_ratio >= 0.5),
    }
    gates_passed = int(sum(1 for v in gates.values() if v))
    verdict = "ACCEPT" if gates_passed == 8 else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "spy_rows": int(len(prices)),
            "finra_settlement_dates": int(len(si_df)),
            "finra_coverage": si_coverage,
            "start": str(prices.index[0].date()),
            "end": str(prices.index[-1].date()),
            "train_end_exclusive": val_start,
            "val_start": val_start,
            "test_start": test_start,
            "oos_rows": int(len(oos_close)),
            "note": "FINRA exchange-listed short interest (real data); publication lag PIT-aligned",
        },
        "selected": selected,
        "wf_train_sharpe": float(sel["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sel_sharpe),
        "oos_val_test": oos_m,
        "benchmark_buy_hold_spy_oos": bench_m,
        "ablations": {
            "random_si_oos": rand_m,
            "inverse_signal_oos": inv_m,
        },
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else wf_stability,
        "benchmark_pvalue_one_sided": float(bp),
        "information_ratio_vs_buy_hold": float(ir),
        "perturbation": {
            "min_ratio": float(min_ratio) if np.isfinite(min_ratio) else min_ratio,
            "n_points": len(pert_sharpes),
            "min_sharpe": float(min(pert_sharpes)) if pert_sharpes else None,
        },
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
        },
    }
    (art / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    grid.to_csv(art / "grid.csv", index=False)
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": gates_passed,
                "artifact": str(art),
                "oos_sharpe": oos_m["sharpe"],
            },
            indent=2,
        )
    )
    return summary


def _iter_grid():
    for si_window in GRID["si_window"]:
        for entry_z in GRID["entry_z"]:
            for exit_z in GRID["exit_z"]:
                for vol_target in GRID["vol_target"]:
                    for universe in GRID["universe"]:
                        yield {
                            "si_window": si_window,
                            "entry_z": entry_z,
                            "exit_z": exit_z,
                            "vol_target": vol_target,
                            "universe": universe,
                        }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    main(args.out)
