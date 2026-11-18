"""NF-20261114-02 / H183 (Cycle 213): crypto perpetual funding-rate carry.

Broad mechanism category: carry / institutional funding basis (perp premium
harvest).  Repo-new root family relative to executed H1-H182: H23 tested
directional crypto TSMOM on perpetual futures and was rejected on data; no
executed H-ID trades the *funding/basis* cash-and-carry spread.  Parameter,
timeframe, universe and market variations are explicitly not new families;
this is a different return source (funding + basis convergence), not a
directional price-trend signal.

Mechanism.  Perpetual futures have no expiry, so the exchange anchors their
price to spot with a periodic funding payment: when the perp trades at a
premium (typical when leveraged long demand is high) longs pay shorts.  A
delta-neutral book that is long spot and short the perp therefore receives
that funding while carrying no directional crypto exposure.  The premium
persists because leveraged long demand is structural (retail leverage,
basis-hungry funds are capacity-constrained) and because arbitrage capital is
limited by borrow, custody and margin constraints.  The carry is not free:
spot and perp fees, slippage, and the risk that funding flips negative.

Observable / PIT timing.  Binance publishes monthly public ZIP archives of
perpetual ``fundingRate`` prints (three per day at 00:00/08:00/16:00 UTC in
the sample) and daily spot/perp ``klines`` -- free, key-less, no REST API
(which is geo-blocked from this host).  Day-t funding prints are known at the
close of day t; the signal is a trailing mean of *past* daily funding sums;
the position is set at close t and earns day t+1 funding and
``spot_ret - perp_ret``.  No same-bar or future information is used.

Null (H0).  Timing the delta-neutral carry book on trailing funding adds
nothing over a passive always-on carry book, after fees; equivalently, trailing
funding has no predictive power for next-day funding/ basis returns.

Pre-registration (Cycle 213, before any validation/test outcome was examined).
NF-ID NF-20261114-02 (repo-new execution; registered as data-blocked in Cycles
96/116 on a REST/yfinance-only premise that the public archive probe corrects).
Hypothesis H183 (next unused after H182).  Sample 2020-01-01 -> 2026-10-31
(first/last complete public archive months).  Train 2020-01-01 ->
2023-06-30; Val 2023-07-01 -> 2024-12-31; Test protected 2025-01-01 ->
2026-10-31.  Selection: train-only 4-fold walk-forward Sharpe.  OOS gates on
Val+Test only, fail-closed.  Universe BTCUSDT/ETHUSDT/BNBUSDT/XRPUSDT/
ADAUSDT/SOLUSDT/DOGEUSDT, each eligible from its first archive month; fixed
1/7 capital weight per active symbol.  Grid (bounded, 20): trailing funding
window {7,14,28,56} x entry mean funding {0.0,0.25,0.5} bps/day x exit
{0.0,0.25} bps/day with exit <= entry.  Costs 14 bps per unit of turnover
(10 bps spot taker + 4 bps perp taker, no slippage credit).

Gates (OOS Val+Test): Sharpe>=1.0, trades>=50, PF>=1.3, maxDD<=15%, WF
stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05 with
IR>=0 against the *passive always-on carry* book, perturbation min
ratio>=0.5.

Ablations/falsifiers: passive always-on carry benchmark; random-gating
control (same active asset-days, seed 42); inverse-funding signal; OAT
perturbation (+/-20%).  No gate weakening.  Free/public data only.
``src/qtr`` unchanged.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.validation.statistics import benchmark_significance_gate

EXPERIMENT = "nf_20261114_02_crypto_funding_carry"
NF_ID = "NF-20261114-02"
HYPOTHESIS = "H183"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT"]
START_MONTH = "2020-01"
END_MONTH = "2026-10"
START = "2020-01-01"
END = "2026-10-31"
TRAIN_END = "2023-06-30"
VAL_END = "2024-12-31"
N_ASSETS = len(SYMBOLS)
COST_BPS = 14.0
SEED = 42
DAYS_PER_YEAR = 252
ARCHIVE_ROOT = "https://data.binance.vision/data"
USER_AGENT = "qtr-research/0.1 (research@example.com)"
CACHE_DIR = Path(".cache") / "binance_archive"

GRID = {
    "funding_window": [7, 14, 28, 56],
    "entry_bps": [0.0, 0.25, 0.5],
    "exit_bps": [0.0, 0.25],
}

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 50,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}


def _artifact_dir(out: str | None) -> Path:
    if out:
        path = Path(out).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = (Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{stamp}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def month_range(start: str, end: str) -> list[str]:
    """Inclusive ``YYYY-MM`` month list (shared boundary convention with the probe)."""
    start_ts = pd.Period(start, freq="M")
    end_ts = pd.Period(end, freq="M")
    if end_ts < start_ts:
        return []
    return [str(p) for p in pd.period_range(start_ts, end_ts, freq="M")]


def archive_url(kind: str, symbol: str, month: str) -> str:
    """Public-archive URL for ``funding``, ``perp`` or ``spot`` daily data."""
    if kind == "funding":
        return (
            f"{ARCHIVE_ROOT}/futures/um/monthly/fundingRate/{symbol}/"
            f"{symbol}-fundingRate-{month}.zip"
        )
    if kind == "perp":
        return f"{ARCHIVE_ROOT}/futures/um/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip"
    if kind == "spot":
        return f"{ARCHIVE_ROOT}/spot/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip"
    raise ValueError(f"unknown archive kind: {kind!r}")


def _fetch(url: str, cache_dir: Path = CACHE_DIR, timeout: float = 30.0) -> bytes | None:
    """Download one archive with an on-disk cache; ``None`` on 404 (not listed).

    The cache key is the full archive path, not the file name: the spot and
    perp daily kline archives share the same ``{SYMBOL}-1d-{YYYY-MM}.zip``
    basename, so a basename-only key silently served perp prices as spot
    prices (zero basis) on every run after the first.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = url.split("/data/", 1)[-1].replace("/", "_")
    cached = cache_dir / key
    if cached.exists():
        return cached.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    cached.write_bytes(payload)
    return payload


def _read_archive_csv(raw: bytes) -> pd.DataFrame:
    """Read a positional CSV from a ZIP; older archives carry no header row.

    Binance archive files are header-less before ~2023 and header-punctuated
    afterwards, so the format is detected per file by coercing column 0 (a
    millisecond epoch in every archive) to numeric and dropping the header row
    when it does not parse.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = archive.namelist()[0]
        frame = pd.read_csv(io.BytesIO(archive.read(name)), header=None)
    stamp = pd.to_numeric(frame.iloc[:, 0], errors="coerce")
    return frame.loc[stamp.notna()].reset_index(drop=True)


def _epoch_timestamps(values: pd.Series) -> pd.Series:
    """Convert archive epoch stamps to UTC datetimes, detecting the unit.

    Binance spot kline archives switch from milliseconds to microseconds from
    2025-01 onward while futures archives remain in milliseconds.  Treating a
    microsecond stamp as milliseconds dates it to the year ~58800, which
    silently removed every 2025+ date from the spot/perp intersection.
    """
    numeric = pd.to_numeric(values, errors="coerce")
    finite = numeric.dropna()
    median = float(finite.median()) if len(finite) else 0.0
    if median > 1e17:
        unit = "ns"
    elif median > 1e14:
        unit = "us"
    else:
        unit = "ms"
    return pd.to_datetime(numeric, unit=unit, utc=True)


def parse_funding_zip(raw: bytes) -> pd.Series:
    """Parse a fundingRate ZIP into a UTC-date-indexed series of daily sums."""
    frame = _read_archive_csv(raw)
    calc = _epoch_timestamps(frame.iloc[:, 0])
    rate = pd.to_numeric(frame.iloc[:, 2], errors="coerce")
    prints = pd.Series(rate.to_numpy(), index=pd.DatetimeIndex(calc)).dropna()
    prints = prints[prints.index.notna()]
    daily = prints.groupby(prints.index.tz_convert("UTC").normalize().tz_localize(None)).sum()
    return daily.sort_index()


def parse_kline_zip(raw: bytes) -> pd.Series:
    """Parse a daily kline ZIP into a UTC-date-indexed close series."""
    frame = _read_archive_csv(raw)
    open_ms = pd.to_numeric(frame.iloc[:, 0], errors="coerce")
    close = pd.to_numeric(frame.iloc[:, 4], errors="coerce")
    frame = pd.DataFrame({"open_time": open_ms, "close": close}).dropna()
    stamps = _epoch_timestamps(frame["open_time"]).dt.tz_localize(None)
    index = pd.DatetimeIndex(stamps).normalize()
    series = pd.Series(frame["close"].to_numpy(), index=index).sort_index()
    return series[~series.index.duplicated(keep="last")]


def _download_symbol(symbol: str, months: list[str], cache_dir: Path = CACHE_DIR) -> dict:
    """Fetch and concatenate one symbol's funding, perp-close and spot-close."""
    jobs = [(kind, month) for kind in ("funding", "perp", "spot") for month in months]
    payloads: dict[tuple[str, str], bytes | None] = {}

    def load(job: tuple[str, str]) -> None:
        kind, month = job
        payloads[job] = _fetch(archive_url(kind, symbol, month), cache_dir=cache_dir)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(load, jobs))

    funding_parts = [
        parse_funding_zip(payloads[("funding", month)])
        for month in months
        if payloads[("funding", month)]
    ]
    perp_parts = [
        parse_kline_zip(payloads[("perp", month)]) for month in months if payloads[("perp", month)]
    ]
    spot_parts = [
        parse_kline_zip(payloads[("spot", month)]) for month in months if payloads[("spot", month)]
    ]
    if not funding_parts or not perp_parts or not spot_parts:
        raise RuntimeError(f"incomplete public archive data for {symbol}")
    funding = pd.concat(funding_parts).sort_index()
    perp = pd.concat(perp_parts).sort_index()
    spot = pd.concat(spot_parts).sort_index()
    funding = funding[~funding.index.duplicated(keep="last")]
    perp = perp[~perp.index.duplicated(keep="last")]
    spot = spot[~spot.index.duplicated(keep="last")]
    return {
        "funding": funding,
        "perp": perp,
        "spot": spot,
        "first_funding_date": str(funding.index.min().date()) if len(funding) else "",
    }


def _build_panel(
    spot: pd.Series, perp: pd.Series, funding: pd.Series, start: str, end: str
) -> pd.DataFrame:
    """Align spot/perp closes and daily funding onto common dates (funding=0 if none)."""
    index = spot.index.intersection(perp.index)
    index = index[(index >= pd.Timestamp(start)) & (index <= pd.Timestamp(end))].sort_values()
    panel = pd.DataFrame(
        {
            "spot": spot.reindex(index).astype(float),
            "perp": perp.reindex(index).astype(float),
            "funding": funding.reindex(index).astype(float).fillna(0.0),
        },
        index=index,
    )
    return panel.dropna(subset=["spot", "perp"])


def _signal(panel: pd.DataFrame, window: int) -> pd.Series:
    """Trailing mean of past daily funding sums (decimal per day, known at close t)."""
    return panel["funding"].rolling(window, min_periods=window).mean()


def _weights_from_signal(
    signal: pd.Series, entry: float, exit_level: float, weight: float
) -> pd.Series:
    """Hysteresis gate: enter when mean funding >= entry, leave below exit."""
    out = pd.Series(0.0, index=signal.index, dtype=float)
    active = False
    for i, value in enumerate(signal.to_numpy(dtype=float)):
        if np.isfinite(value):
            if not active and value >= entry:
                active = True
            elif active and value <= exit_level:
                active = False
        out.iloc[i] = weight if active else 0.0
    return out


def _compute_weights(
    panels: dict[str, pd.DataFrame], funding_window: int, entry_bps: float, exit_bps: float
) -> pd.DataFrame:
    """Per-symbol 1/N weights with hysteresis on trailing mean funding."""
    weight = 1.0 / N_ASSETS
    entry = entry_bps / 1e4
    exit_level = exit_bps / 1e4
    if exit_level > entry:
        exit_level = entry
    columns = {}
    for symbol, panel in panels.items():
        signal = _signal(panel, funding_window)
        columns[symbol] = _weights_from_signal(signal, entry, exit_level, weight)
    return pd.DataFrame(columns).sort_index().fillna(0.0)


def _run_bt(
    panels: dict[str, pd.DataFrame], weights: pd.DataFrame, cost_bps: float = COST_BPS
) -> tuple[pd.Series, pd.Series, int]:
    """Delta-neutral carry book PnL with turnover costs (no directional exposure)."""
    index = weights.index
    pair_returns = {}
    for symbol, panel in panels.items():
        aligned = panel.reindex(index)
        pair_returns[symbol] = (
            aligned["spot"].pct_change() - aligned["perp"].pct_change() + aligned["funding"]
        )
    pair = pd.DataFrame(pair_returns, index=index).reindex(columns=weights.columns)
    gross = (weights.shift(1).fillna(0.0) * pair).sum(axis=1, min_count=1).fillna(0.0)
    turnover = weights.diff().abs().sum(axis=1)
    turnover.iloc[0] = weights.iloc[0].abs().sum()
    cost = turnover * (cost_bps / 1e4)
    strat = (gross - cost).astype(float).fillna(0.0)
    equity = (1.0 + strat).cumprod()
    trades = int((weights.diff().abs().fillna(weights.abs()) > 1e-12).sum().sum())
    return strat, equity, trades


def _annualized_sharpe(ret: pd.Series) -> float:
    values = ret.dropna()
    if len(values) < 20:
        return 0.0
    std = values.std(ddof=0)
    if std <= 0 or not np.isfinite(std):
        return 0.0
    return float(values.mean() / std * math.sqrt(DAYS_PER_YEAR))


def _profit_factor(ret: pd.Series) -> float:
    values = ret.dropna()
    gains = values[values > 0].sum()
    losses = -values[values < 0].sum()
    if losses <= 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _max_drawdown(equity: pd.Series) -> float:
    values = equity.dropna()
    if len(values) == 0:
        return 0.0
    peak = values.cummax()
    return float((values / peak - 1.0).min())


def _rolling_252_sharpe_worst(ret: pd.Series) -> float:
    values = ret.dropna()
    if len(values) < 252:
        return _annualized_sharpe(values)
    array = values.to_numpy(dtype=float)
    worst = float("inf")
    for i in range(251, len(array)):
        window = array[i - 251 : i + 1]
        std = window.std(ddof=0)
        if std <= 0 or not np.isfinite(std):
            continue
        sharpe = float(window.mean() / std * math.sqrt(DAYS_PER_YEAR))
        if sharpe < worst:
            worst = sharpe
    return worst if np.isfinite(worst) else _annualized_sharpe(values)


def _metrics(strat_ret: pd.Series, equity: pd.Series, trades: int) -> dict:
    return {
        "sharpe": _annualized_sharpe(strat_ret),
        "profit_factor": _profit_factor(strat_ret),
        "max_drawdown": _max_drawdown(equity),
        "trades": int(trades),
        "periods": int(len(strat_ret.dropna())),
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) > 1 else 0.0,
        "worst_regime_rolling252_sharpe": _rolling_252_sharpe_worst(strat_ret),
    }


def _wf_score(
    panels: dict[str, pd.DataFrame],
    params: dict,
    index: pd.Index,
    n_folds: int = 4,
) -> float:
    """Mean train-only fold Sharpe using weights computed on past data only."""
    if len(index) < 400:
        return -999.0
    weights = _compute_weights(
        panels, params["funding_window"], params["entry_bps"], params["exit_bps"]
    )
    fold = len(index) // n_folds
    sharpes = []
    for i in range(n_folds):
        stop = len(index) if i == n_folds - 1 else (i + 1) * fold
        block = index[i * fold : stop]
        if len(block) < 120:
            continue
        ret, _, _ = _run_bt(panels, weights.reindex(block).fillna(0.0))
        sharpes.append(_annualized_sharpe(ret))
    return float(np.mean(sharpes)) if sharpes else -999.0


def _information_ratio(strategy: pd.Series, benchmark: pd.Series) -> float:
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna()
    std = diff.std(ddof=0)
    if len(diff) < 20 or std <= 0 or not np.isfinite(std):
        return 0.0
    return float(diff.mean() / std * math.sqrt(DAYS_PER_YEAR))


def _benchmark_pvalue(strategy: pd.Series, benchmark: pd.Series, n_boot: int = 2000) -> float:
    a, b = strategy.align(benchmark, join="inner")
    diff = (a - b).dropna().to_numpy()
    if len(diff) < 20:
        return 1.0
    observed = diff.mean()
    if not np.isfinite(observed):
        return 1.0
    rng = np.random.default_rng(SEED)
    centered = diff - observed
    draws = np.array(
        [rng.choice(centered, size=len(centered), replace=True).mean() for _ in range(n_boot)]
    )
    return float((1.0 + np.sum(draws >= observed)) / (n_boot + 1.0))


def _perturbation_oos_sharpes(
    panels: dict[str, pd.DataFrame], selected: dict, index: pd.Index
) -> list[float]:
    """One-at-a-time +/-20% parameter perturbation, measured on the same OOS block."""
    windows = sorted(
        {
            max(3, int(round(selected["funding_window"] * 0.8))),
            int(selected["funding_window"]),
            int(round(selected["funding_window"] * 1.2)),
        }
    )
    entries = sorted(
        {
            round(selected["entry_bps"] * 0.8, 6),
            float(selected["entry_bps"]),
            round(selected["entry_bps"] * 1.2, 6),
        }
    )
    exits = sorted(
        {
            round(selected["exit_bps"] * 0.8, 6),
            float(selected["exit_bps"]),
            round(selected["exit_bps"] * 1.2, 6),
        }
    )
    sharpes = []
    for window in windows:
        for entry in entries:
            for exit_level in exits:
                if exit_level > entry:
                    continue
                weights = _compute_weights(panels, int(window), float(entry), float(exit_level))
                ret, _, _ = _run_bt(panels, weights.reindex(index).fillna(0.0))
                sharpes.append(_annualized_sharpe(ret))
    return [value for value in sharpes if np.isfinite(value)]


def _iter_grid():
    for funding_window in GRID["funding_window"]:
        for entry_bps in GRID["entry_bps"]:
            for exit_bps in GRID["exit_bps"]:
                if exit_bps > entry_bps:
                    continue
                yield {
                    "funding_window": int(funding_window),
                    "entry_bps": float(entry_bps),
                    "exit_bps": float(exit_bps),
                }


def _always_on_weights(panels: dict[str, pd.DataFrame], index: pd.Index) -> pd.DataFrame:
    """Passive benchmark: hold the delta-neutral carry book on every listed day."""
    columns = {
        symbol: panel.reindex(index)["spot"].notna().astype(float) / N_ASSETS
        for symbol, panel in panels.items()
    }
    return pd.DataFrame(columns, index=index).fillna(0.0)


def _random_weights(
    weights: pd.DataFrame, panels: dict[str, pd.DataFrame], seed: int = SEED
) -> pd.DataFrame:
    """Random-gating control: same active asset-days, randomly placed."""
    rng = np.random.default_rng(seed)
    out = pd.DataFrame(0.0, index=weights.index, columns=weights.columns)
    for symbol in weights.columns:
        active = weights[symbol] > 1e-12
        count = int(active.sum())
        eligible = panels[symbol].reindex(weights.index)["spot"].notna()
        candidates = np.flatnonzero(eligible.to_numpy())
        if count == 0 or len(candidates) == 0:
            continue
        chosen = rng.choice(candidates, size=min(count, len(candidates)), replace=False)
        out.iloc[chosen, out.columns.get_loc(symbol)] = 1.0 / N_ASSETS
    return out


def _download_all(symbols: list[str], cache_dir: Path = CACHE_DIR) -> tuple[dict, list[dict]]:
    """Download every symbol's archives and build its aligned panel."""
    months = month_range(START_MONTH, END_MONTH)
    panels = {}
    provenance = []
    for symbol in symbols:
        raw = _download_symbol(symbol, months, cache_dir=cache_dir)
        panel = _build_panel(raw["spot"], raw["perp"], raw["funding"], START, END)
        if len(panel) < 500:
            raise RuntimeError(f"insufficient aligned history for {symbol}: {len(panel)}")
        panels[symbol] = panel
        provenance.append(
            {
                "symbol": symbol,
                "first_funding_date": raw["first_funding_date"],
                "rows": int(len(panel)),
                "start": str(panel.index[0].date()),
                "end": str(panel.index[-1].date()),
                "mean_funding_bps_per_day": float(panel["funding"].mean() * 1e4),
                "share_negative_funding_days": float((panel["funding"] < 0).mean()),
                "source": archive_url("funding", symbol, START_MONTH).rsplit("/", 1)[0],
            }
        )
    return panels, provenance


def main(out: str | None = None, symbols: list[str] | None = None) -> dict:
    started = time.time()
    artifact = _artifact_dir(out)
    panels, provenance = _download_all(symbols or SYMBOLS)

    index = sorted(set().union(*[panel.index for panel in panels.values()]))
    index = pd.DatetimeIndex(index)
    train = index[index <= pd.Timestamp(TRAIN_END)]
    oos = index[index > pd.Timestamp(TRAIN_END)]
    val = index[(index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END))]
    test = index[index > pd.Timestamp(VAL_END)]

    rows = []
    for params in _iter_grid():
        wf = _wf_score(panels, params, train)
        weights = _compute_weights(
            panels, params["funding_window"], params["entry_bps"], params["exit_bps"]
        )
        train_ret, _, _ = _run_bt(panels, weights.reindex(train).fillna(0.0))
        rows.append(
            {**params, "wf_train_sharpe": wf, "train_sharpe": _annualized_sharpe(train_ret)}
        )
    grid = pd.DataFrame(rows).sort_values(["wf_train_sharpe", "train_sharpe"], ascending=False)
    grid.to_csv(artifact / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows")
    best = valid.iloc[0].to_dict()
    selected = {
        "funding_window": int(best["funding_window"]),
        "entry_bps": float(best["entry_bps"]),
        "exit_bps": float(best["exit_bps"]),
    }

    weights = _compute_weights(
        panels, selected["funding_window"], selected["entry_bps"], selected["exit_bps"]
    )
    oos_ret, oos_equity, oos_trades = _run_bt(panels, weights.reindex(oos).fillna(0.0))
    oos_metrics = _metrics(oos_ret, oos_equity, oos_trades)

    always_on = _always_on_weights(panels, oos)
    bench_ret, bench_equity, _ = _run_bt(panels, always_on)
    bench_metrics = _metrics(bench_ret, bench_equity, 0)

    random_w = _random_weights(weights.reindex(oos).fillna(0.0), panels)
    rand_ret, rand_equity, rand_trades = _run_bt(panels, random_w)
    random_metrics = _metrics(rand_ret, rand_equity, rand_trades)

    inverse_w = pd.DataFrame(0.0, index=weights.index, columns=weights.columns)
    for symbol, panel in panels.items():
        signal = -_signal(panel, selected["funding_window"])
        inverse_w[symbol] = _weights_from_signal(
            signal,
            selected["entry_bps"] / 1e4,
            selected["exit_bps"] / 1e4,
            1.0 / N_ASSETS,
        )
    inv_ret, inv_equity, inv_trades = _run_bt(panels, inverse_w.reindex(oos).fillna(0.0))
    inverse_metrics = _metrics(inv_ret, inv_equity, inv_trades)

    train_ret, _, _ = _run_bt(panels, weights.reindex(train).fillna(0.0))
    train_sharpe = _annualized_sharpe(train_ret)
    wf_stability = (
        float(oos_metrics["sharpe"] / train_sharpe)
        if np.isfinite(train_sharpe) and train_sharpe != 0
        else (float("inf") if oos_metrics["sharpe"] > 0 else 0.0)
    )

    perturbed = _perturbation_oos_sharpes(panels, selected, oos)
    base_sharpe = oos_metrics["sharpe"]
    min_ratio = (
        float(min(perturbed) / base_sharpe)
        if perturbed and np.isfinite(base_sharpe) and base_sharpe != 0
        else 0.0
    )
    ir = _information_ratio(oos_ret, bench_ret)
    p_value = _benchmark_pvalue(oos_ret, bench_ret)

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
            p_value, ir, GATES["max_p_value"]
        ),
        "perturbation_min_ratio_ge_0_5": bool(
            np.isfinite(min_ratio) and min_ratio >= GATES["min_perturbed_sharpe_ratio"]
        ),
    }
    gates_passed = int(sum(gates.values()))
    verdict = "ACCEPT" if gates_passed == len(gates) else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - started, 3),
        "data": {
            "source": "Binance public archives (data.binance.vision), free/key-less/PIT",
            "symbols": list(panels),
            "rows": int(len(index)),
            "start": str(index[0].date()),
            "end": str(index[-1].date()),
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "train_rows": int(len(train)),
            "val_rows": int(len(val)),
            "test_rows": int(len(test)),
            "oos_rows": int(len(oos)),
        },
        "provenance": provenance,
        "grid_size": int(len(grid)),
        "selected": selected,
        "wf_train_sharpe": float(best["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sharpe),
        "oos_val_test": oos_metrics,
        "benchmark_always_on_carry_oos": bench_metrics,
        "ablations": {
            "random_gating_oos": random_metrics,
            "inverse_funding_oos": inverse_metrics,
        },
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else wf_stability,
        "benchmark_pvalue_one_sided": float(p_value),
        "information_ratio_vs_always_on": float(ir),
        "perturbation": {
            "min_ratio": float(min_ratio) if np.isfinite(min_ratio) else min_ratio,
            "n_points": len(perturbed),
            "min_sharpe": float(min(perturbed)) if perturbed else None,
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
            "cost_bps_per_turnover": COST_BPS,
        },
    }
    (artifact / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": gates_passed,
                "artifact": str(artifact),
                "oos_sharpe": oos_metrics["sharpe"],
            },
            indent=2,
        )
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    main(args.out)
