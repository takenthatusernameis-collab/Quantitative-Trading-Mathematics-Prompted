"""NF-20261125-02 / H201 (Cycle 310 pre-registration and execution).

Broad mechanism category: short-selling pressure / short-interest cross-section.
Repo-new root family relative to executed H1-H200: no executed H-ID uses
point-in-time short-selling pressure as a cross-sectional equity signal. The
closest prior families are the continuous equity cross-sections H187-H198
(fundamental/price/characteristic sorts) and H199 (size premium); H179
(``run_nf_20261110_06_short_interest.py``) is a *market-timing* SPY/sector-ETF
short-interest gate, not a cross-section. Short-selling pressure is a distinct
return-generating mechanism -- the "smart money / informed trading" channel where
aggregate short interest predicts negative subsequent returns (high
short-interest stocks underperform). Not a parameter/universe/timeframe variant
of any exhausted family.

Mechanism / causal chain. Informed investors and arbitrageurs sell short stocks
they judge overpriced; aggregate short-selling pressure therefore reflects
negative information. Stocks with high short interest relative to trading
activity are subsequently overpriced and underperform; low short-interest stocks
comparatively outperform. Prediction (directional): **short the top-k names by
cross-sectional short-pressure z-score, long the bottom-k.** Null (H0): aggregate
short-selling pressure carries no cross-sectional predictive power for
next-period equity returns after costs -- a short-pressure tilt adds nothing over
a passive equal-weight book of the same universe.

PIT timing. FINRA Reg SHO daily short-volume files
(``CNMSshvol{YYYYMMDD}.txt``, free, no key, published ~2010->) carry ``Symbol``,
``ShortVolume``, ``TotalVolume`` per trade date. A daily file may enter the
signal only when its trade date ``<= t``; the shared engine applies
``shift(1)``, so a position formed at the close of month-end m earns m -> m+1.
Short pressure per symbol per month = mean of daily ``ShortVolume / TotalVolume``
over the month (days-to-cover requires monthly shares outstanding, which is not
available PIT for the broad universe, so the short-volume ratio is used as the
pressure proxy). The panel refreshes monthly (first business day) using the
latest complete month, forward-filled so turnover happens at most monthly.
Reg SHO uses ``BRK/B`` slash class-share symbols; the broad-universe yfinance
tickers (``BRK-B``) are mapped with ``-`` -> ``/`` for the Reg SHO lookup.

Pre-registration (Cycle 309, written before any forward-return outcome is
computed). Sample 2015-01-01 -> 2026-11-25; Train -> 2021-12-31; Val
2022-01-01 -> 2023-12-31; Test protected 2024-01-01 -> 2026-11-25. Universe:
broad S&P 500/400/600 names with >=4 months of Reg SHO coverage and yfinance
daily Close coverage (feasibility confirmed:
``scripts/probe_finra_regsho_availability.py`` reachable with a normal
User-Agent, 49/50 curated S&P-100 symbols usable; broad-universe price coverage
confirmed by ``scripts/probe_broad_universe_availability.py``, 1502 tickers, 100%
sampled coverage). Features: ``short_pressure_z`` = cross-sectional z-score of
monthly mean short-volume ratio; the signal fed to the long-top/short-bottom
hysteresis sorter is ``-short_pressure_z`` (high pressure -> short, low ->
long). Grid (bounded, 16): entry_z {0.5, 1.0} x exit_z {0.0} x k {10, 20} x
vol_target {0.10, 0.15}; train-only 4-fold walk-forward Sharpe selection. Costs:
5 bps one-way per leg traded (equity commission + spread); short-borrow cost not
modelled (disclosed optimistic; borrow is typically the dominant cost for
short-interest strategies).

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from H187/H190-H200):
Sharpe >= 1.0; trades >= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7;
worst-regime rolling-252 Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with
IR >= 0 vs the passive equal-weight long book of the same universe; OAT +/-20%
perturbation min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same
active leg count, seed 42); inverse signal (anti-pressure); coverage / universe
diagnostics.

Implementation constraints: reuse the gate dict from
run_nf_20261114_01_commodity_termstructure_carry.py (H184) and the statistics
helpers from ``qtr.validation.statistics``; the Reg SHO loader helpers come from
``scripts/probe_finra_regsho_availability.py`` and the broad universe from
``scripts/probe_broad_universe_availability.py`` (no forked copy). Only the Reg
SHO monthly aggregation, symbol mapping, monthly signal refresh and price
alignment are new code. Free/public real data only; ``src/qtr`` unchanged.
Artifact under
``.experiments/nf_runs/nf_20261125_02_short_interest_<timestamp>/summary.json`` +
grid.csv.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
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

# Reuse the H184 gate dict (standard 8 gates, unchanged).
_H184_PATH = ROOT / "run_nf_20261114_01_commodity_termstructure_carry.py"
_h184_spec = importlib.util.spec_from_file_location("h184_carry", _H184_PATH)
assert _h184_spec is not None and _h184_spec.loader is not None
h184 = importlib.util.module_from_spec(_h184_spec)  # type: ignore[arg-type]
sys.modules[_h184_spec.name] = h184
_h184_spec.loader.exec_module(h184)

# Import the FINRA Reg SHO probe functions (no forked copy).
_PROBE_PATH = ROOT / "scripts" / "probe_finra_regsho_availability.py"
_probe_spec = importlib.util.spec_from_file_location("probe_regsho", _PROBE_PATH)
assert _probe_spec is not None and _probe_spec.loader is not None
probe_regsho = importlib.util.module_from_spec(_probe_spec)  # type: ignore[arg-type]
sys.modules[_probe_spec.name] = probe_regsho
_probe_spec.loader.exec_module(probe_regsho)

# Import broad universe probe for S&P 500/400/600 tickers.
_BROAD_PROBE_PATH = ROOT / "scripts" / "probe_broad_universe_availability.py"
_broad_spec = importlib.util.spec_from_file_location("broad_probe", _BROAD_PROBE_PATH)
assert _broad_spec is not None and _broad_spec.loader is not None
broad_probe = importlib.util.module_from_spec(_broad_spec)  # type: ignore[arg-type]
sys.modules[_broad_spec.name] = broad_probe
_broad_spec.loader.exec_module(broad_probe)

EXPERIMENT = "nf_20261125_02_short_interest"
NF_ID = "NF-20261125-02"
HYPOTHESIS = "H201"

START = "2015-01-01"
END = "2026-11-25"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 40
MIN_MONTHS = 4
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252

GATES = dict(h184.GATES)

GRID = {
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [10, 20],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "short_interest"
MONTHLY_CACHE_DIR = CACHE_DIR / "monthly"
PRICE_CACHE_DIR = Path(".cache") / "short_interest_prices"


def cache_dir_for(cache_dir: Path | str | None) -> Path:
    return Path(cache_dir) if cache_dir is not None else CACHE_DIR


def monthly_cache_dir_for(cache_dir: Path | str | None) -> Path:
    base = cache_dir_for(cache_dir)
    return base / "monthly" if base == CACHE_DIR else Path(cache_dir) / "monthly"


def regsho_symbol(ticker: str) -> str:
    """Map a yfinance ticker to the Reg SHO slash class-share convention."""
    return str(ticker).strip().upper().replace("-", "/")


def load_universe() -> list[str]:
    """Broad S&P 500/400/600 union (yfinance ``-`` convention), sorted/deduped."""
    constituents = broad_probe.fetch_constituents()
    universe: set[str] = set()
    for tickers in constituents.values():
        universe.update(tickers)
    return sorted(universe)


def _month_key(day: pd.Timestamp) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def fetch_month_short_ratio(
    month_start: pd.Timestamp,
    universe_symbols: set[str],
    fetch=None,
    throttle_s: float = 0.0,
) -> pd.DataFrame:
    """Mean daily short-volume ratio per symbol for one calendar month.

    Returns a DataFrame with columns ``[symbol, ratio_sum, n_days]`` (the mean is
    ``ratio_sum / n_days``). A month with no usable daily file yields an empty
    frame. The result is cached under ``.cache/short_interest/monthly/YYYY-MM.parquet``
    so a re-run resumes without re-fetching.
    """
    fetch = fetch or probe_regsho.fetch_regsho
    month_start = pd.Timestamp(month_start)
    cache_dir = monthly_cache_dir_for(None)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{_month_key(month_start)}.parquet"
    if cache_file.exists():
        return pd.read_parquet(cache_file)

    month_end = month_start + pd.offsets.MonthEnd(0)
    days = pd.bdate_range(month_start, month_end)
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for day in days:
        raw = fetch(day.date())
        if raw is None:
            continue
        frame = probe_regsho.parse_regsho(raw)
        if len(frame) == 0:
            continue
        frame = frame[frame["Symbol"].isin(universe_symbols)]
        if len(frame) == 0:
            continue
        for row in frame.itertuples(index=False):
            symbol = row.Symbol
            ratio = float(row.ShortRatio)
            if not np.isfinite(ratio):
                continue
            sums[symbol] = sums.get(symbol, 0.0) + ratio
            counts[symbol] = counts.get(symbol, 0) + 1
        if throttle_s:
            time.sleep(throttle_s)

    if not sums:
        empty = pd.DataFrame(columns=["symbol", "ratio_sum", "n_days"])
        empty.to_parquet(cache_file, index=False)
        return empty

    out = pd.DataFrame(
        {
            "symbol": list(sums.keys()),
            "ratio_sum": [sums[s] for s in sums],
            "n_days": [counts[s] for s in sums],
        }
    )
    out.to_parquet(cache_file, index=False)
    return out


def build_pressure_signal_panel(
    universe: list[str],
    calendar: pd.DatetimeIndex,
    fetch=None,
    cache_dir: Path | str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Build the monthly short-pressure signal panel (index=calendar, cols=tickers).

    The returned panel is ``-z`` of the monthly mean short-volume ratio so that
    the long-top/short-bottom hysteresis sorter shorts high-pressure names and
    longs low-pressure names (the pre-registered direction).
    """
    del cache_dir  # monthly cache location is fixed; kept for signature symmetry
    universe_symbols = {regsho_symbol(t) for t in universe}
    sym_to_ticker = {regsho_symbol(t): t for t in universe}

    months = pd.date_range(pd.Timestamp(START).replace(day=1), pd.Timestamp(END), freq="MS")
    monthly_rows: dict[str, dict[str, float]] = {}
    for month_start in months:
        frame = fetch_month_short_ratio(month_start, universe_symbols, fetch=fetch)
        if len(frame) == 0:
            continue
        for row in frame.itertuples(index=False):
            ticker = sym_to_ticker.get(row.symbol)
            if ticker is None:
                continue
            mean_ratio = row.ratio_sum / row.n_days if row.n_days else np.nan
            monthly_rows.setdefault(_month_key(month_start), {})[ticker] = mean_ratio

    if not monthly_rows:
        return pd.DataFrame(index=calendar), []

    monthly = pd.DataFrame.from_dict(monthly_rows, orient="index")
    monthly.index = pd.to_datetime(monthly.index + "-01")
    monthly = monthly.sort_index()

    # Month-end stamp -> reindex to the business-day calendar and forward-fill.
    month_end_index = [m + pd.offsets.MonthEnd(0) for m in monthly.index]
    monthly.index = month_end_index
    panel = monthly.reindex(calendar).ffill()

    # Keep only tickers with at least MIN_MONTHS of coverage.
    valid_cols = panel.columns[panel.notna().sum() >= MIN_MONTHS]
    panel = panel[valid_cols]
    if len(panel.columns) == 0:
        return pd.DataFrame(index=calendar), []

    pressure_z = cross_sectional_z(panel)
    signal_panel = -pressure_z
    valid_tickers = list(signal_panel.columns)
    return signal_panel, valid_tickers


def cross_sectional_z(frame: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score each row (NaN-aware, std>0, count>=2)."""
    values = frame.to_numpy(dtype=float)
    active = np.isfinite(values)
    counts = active.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        means = np.where(counts > 0, np.nansum(values, axis=1) / counts, np.nan)
        centered = np.where(active, values - means[:, None], np.nan)
        variances = np.nansum(centered**2, axis=1) / counts
    stds = np.sqrt(variances)
    usable = (counts >= 2) & np.isfinite(stds) & (stds > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(active, centered / np.where(usable, stds, np.nan)[:, None], np.nan)
    return pd.DataFrame(z, index=frame.index, columns=frame.columns)


# ---------------------------------------------------------------------------
# Signal, sizing and backtest (same primitives as H200 / H184 lineage)
# ---------------------------------------------------------------------------


def signal_weights(
    z: pd.DataFrame, entry_z: float, exit_z: float, k: int, tickers: list[str] | None = None
) -> pd.DataFrame:
    """Hysteresis cross-sectional rank: long top-k / short bottom-k by z."""
    calendar = z.index
    tickers = list(tickers if tickers is not None else z.columns)
    state = {ticker: 0 for ticker in tickers}
    weights = pd.DataFrame(0.0, index=calendar, columns=tickers, dtype=float)
    for day in calendar:
        zi = z.loc[day]
        new = dict(state)
        long_candidates: list[tuple[str, float]] = []
        short_candidates: list[tuple[str, float]] = []
        for ticker in tickers:
            if not pd.notna(zi[ticker]):
                new[ticker] = 0
                continue
            value = float(zi[ticker])
            if state[ticker] == 1 and value <= exit_z:
                new[ticker] = 0
            elif state[ticker] == -1 and value >= -exit_z:
                new[ticker] = 0
            elif state[ticker] == 0:
                if value >= entry_z:
                    long_candidates.append((ticker, value))
                elif value <= -entry_z:
                    short_candidates.append((ticker, value))
        held_longs = [ticker for ticker in tickers if new[ticker] == 1]
        held_shorts = [ticker for ticker in tickers if new[ticker] == -1]
        for ticker, _ in sorted(long_candidates, key=lambda item: item[1], reverse=True):
            if len(held_longs) >= k:
                break
            new[ticker] = 1
            held_longs.append(ticker)
        for ticker, _ in sorted(short_candidates, key=lambda item: item[1]):
            if len(held_shorts) >= k:
                break
            if ticker in held_longs:
                continue
            new[ticker] = -1
            held_shorts.append(ticker)
        state = new
        open_legs = [ticker for ticker in tickers if state[ticker] != 0]
        if open_legs:
            scale = 1.0 / len(open_legs)
            for ticker in open_legs:
                weights.loc[day, ticker] = state[ticker] * scale
    return weights


def vol_scale(portfolio_returns: pd.Series, vol_target: float) -> pd.Series:
    """Delever-only vol target: scale = min(target / trailing vol, 1)."""
    trailing = portfolio_returns.rolling(VOL_LOOKBACK).std(ddof=0) * math.sqrt(DAYS_PER_YEAR)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = vol_target / trailing
    scale = pd.Series(raw, index=portfolio_returns.index, dtype=float).fillna(1.0)
    scale = scale.where(scale <= 1.0, 1.0)
    scale = scale.where(scale > 0, 1.0)
    return scale


def backtest_metrics(
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    side_bps: float = COST_ONE_WAY_BPS,
) -> dict:
    """Shift(1) the target weights, charge turnover costs."""
    shifted = weights.shift(1).fillna(0.0)
    gross = (shifted * returns).sum(axis=1)
    turnover = shifted.diff().abs().sum(axis=1)
    if len(turnover):
        turnover.iloc[0] = float(shifted.iloc[0].abs().sum())
    trade_cost = turnover * (side_bps / 1e4)
    net = (gross - trade_cost).fillna(0.0)
    equity = (1.0 + net).cumprod()
    trades = int((shifted.diff().abs().fillna(shifted.abs()) > 1e-12).sum().sum())
    return {
        "returns": net,
        "equity": equity,
        "trades": trades,
        "gross_returns": gross.fillna(0.0),
        "cost": trade_cost.fillna(0.0),
    }


def metrics(returns: pd.Series, equity: pd.Series, trades: int) -> dict:
    return {
        "sharpe": annualized_sharpe(returns),
        "profit_factor": profit_factor(returns),
        "max_drawdown": max_drawdown(equity),
        "trades": int(trades),
        "periods": int(returns.dropna().shape[0]),
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) > 1 else 0.0,
        "worst_regime_rolling252_sharpe": worst_rolling_sharpe(returns),
    }


def annualized_sharpe(returns: pd.Series) -> float:
    values = pd.Series(returns).dropna()
    if len(values) < 20:
        return 0.0
    std = float(values.std(ddof=0))
    if not np.isfinite(std) or std <= 0:
        return 0.0
    return float(values.mean() / std * math.sqrt(DAYS_PER_YEAR))


def profit_factor(returns: pd.Series) -> float:
    values = pd.Series(returns).dropna()
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses <= 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def max_drawdown(equity: pd.Series) -> float:
    values = pd.Series(equity).dropna()
    if values.empty:
        return 0.0
    return float((values / values.cummax() - 1.0).min())


def worst_rolling_sharpe(returns: pd.Series, window: int = 252) -> float:
    values = pd.Series(returns).dropna()
    if len(values) < window:
        return annualized_sharpe(values)
    array = values.to_numpy(dtype=float)
    worst = float("inf")
    for end in range(window, len(array) + 1):
        block = array[end - window : end]
        std = float(block.std(ddof=0))
        if not np.isfinite(std) or std <= 0:
            continue
        worst = min(worst, float(block.mean() / std * math.sqrt(DAYS_PER_YEAR)))
    return worst if np.isfinite(worst) else annualized_sharpe(values)


def scaled_weights(
    signal: pd.DataFrame, params: dict, returns: pd.DataFrame, tickers: list[str]
) -> tuple[pd.DataFrame, pd.Series]:
    """Target weights and delever-only scale for one parameter combination."""
    weights = signal_weights(signal, params["entry_z"], params["exit_z"], int(params["k"]), tickers)
    raw_port = (weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    scale = vol_scale(raw_port, float(params["vol_target"]))
    return weights.mul(scale, axis=0), scale


def walk_forward_score(
    signal: pd.DataFrame,
    params: dict,
    returns: pd.DataFrame,
    tickers: list[str],
    train_index: pd.DatetimeIndex,
    n_folds: int = 4,
) -> float:
    """Mean contiguous-fold Sharpe on the train block (selection score only)."""
    if len(train_index) < 400:
        return -999.0
    weights, _ = scaled_weights(signal.loc[train_index], params, returns.loc[train_index], tickers)
    fold = len(train_index) // n_folds
    sharpes = []
    for fold_no in range(n_folds):
        start = fold_no * fold
        stop = len(train_index) if fold_no == n_folds - 1 else (fold_no + 1) * fold
        block = train_index[start:stop]
        if len(block) < 120:
            continue
        result = backtest_metrics(
            weights.reindex(block).fillna(0.0),
            returns.reindex(block).fillna(0.0),
        )
        sharpes.append(annualized_sharpe(result["returns"]))
    return float(np.mean(sharpes)) if sharpes else -999.0


def passive_long_weights(returns: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Passive equal-weight long book: equal weight across names with data."""
    active = returns.notna()
    counts = active.sum(axis=1)
    weights = active.astype(float).div(counts.where(counts > 0), axis=0).fillna(0.0)
    return weights.reindex(calendar).fillna(0.0)


def random_weights(weights: pd.DataFrame, returns: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Random-ranking control with the same number of active legs per day."""
    rng = np.random.default_rng(seed)
    out = pd.DataFrame(0.0, index=weights.index, columns=weights.columns, dtype=float)
    for day in weights.index:
        active = [column for column in weights.columns if pd.notna(returns.at[day, column])]
        target_n = int((weights.loc[day] != 0).sum())
        if target_n == 0 or not active:
            continue
        chosen = rng.choice(active, size=min(target_n, len(active)), replace=False)
        signs = rng.choice([-1.0, 1.0], size=len(chosen))
        for column, sign in zip(chosen, signs):
            out.loc[day, column] = float(sign) / len(chosen)
    return out


def iter_grid():
    for entry_z in GRID["entry_z"]:
        for exit_z in GRID["exit_z"]:
            for k in GRID["k"]:
                for vol_target in GRID["vol_target"]:
                    yield {
                        "entry_z": float(entry_z),
                        "exit_z": float(exit_z),
                        "k": int(k),
                        "vol_target": float(vol_target),
                    }


def perturbation_sharpes(
    signal: pd.DataFrame,
    selected: dict,
    returns: pd.DataFrame,
    tickers: list[str],
    oos_index: pd.DatetimeIndex,
) -> list[float]:
    """OAT +/-20% perturbation of entry_z, exit_z and k, measured on OOS."""
    variants = []
    for factor in (0.8, 1.2):
        for param in ("entry_z", "exit_z"):
            variant = dict(selected)
            variant[param] = round(float(selected[param]) * factor, 6)
            variants.append(variant)
    for factor in (0.8, 1.2):
        variant = dict(selected)
        variant["k"] = max(1, int(round(float(selected["k"]) * factor)))
        variants.append(variant)
    sharpes = []
    for variant in variants:
        weights, _ = scaled_weights(signal, variant, returns, tickers)
        result = backtest_metrics(
            weights.reindex(oos_index).fillna(0.0),
            returns.reindex(oos_index).fillna(0.0),
        )
        sharpes.append(annualized_sharpe(result["returns"]))
    return sharpes


def fetch_price_data(
    tickers: list[str],
    calendar: pd.DatetimeIndex,
    cache_dir: Path = PRICE_CACHE_DIR,
) -> pd.DataFrame:
    """Fetch daily adjusted close prices for tickers using yfinance (cached)."""
    import yfinance as yf

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "prices.parquet"

    if cache_file.exists():
        cached = pd.read_parquet(cache_file)
        if set(tickers).issubset(set(cached.columns)):
            if cached.index.min() <= calendar[0] and cached.index.max() >= calendar[-1]:
                return cached.reindex(calendar).ffill()

    print(f"Fetching price data for {len(tickers)} tickers...")
    start = calendar[0] - pd.Timedelta(days=30)
    end = calendar[-1] + pd.Timedelta(days=1)

    batch_size = 50
    all_prices: dict[str, pd.Series] = {}
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        try:
            df = yf.download(
                batch,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True,
                threads=False,
            )
            if isinstance(df.columns, pd.MultiIndex):
                if "Close" in df.columns.get_level_values(0):
                    close = df["Close"]
                elif "Adj Close" in df.columns.get_level_values(0):
                    close = df["Adj Close"]
                else:
                    close = df.iloc[:, 0::6]
                close.columns = [c[1] if isinstance(c, tuple) else c for c in close.columns]
            else:
                close = df[["Close"]] if "Close" in df.columns else df[["Adj Close"]]
                close.columns = batch
            all_prices.update({col: close[col] for col in close.columns})
        except Exception as e:  # noqa: BLE001 - report, keep going
            print(f"  Warning: failed to fetch batch {i}-{i + batch_size}: {e}")
        time.sleep(0.5)

    if not all_prices:
        return pd.DataFrame(index=calendar)

    price_panel = pd.DataFrame(all_prices)
    price_panel.index = pd.to_datetime(price_panel.index)
    price_panel = price_panel.reindex(calendar).ffill()
    price_panel.to_parquet(cache_file)
    print(f"Cached price panel to {cache_file}")
    return price_panel


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def artifact_dir(out: str | None) -> Path:
    if out:
        path = Path(out).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = (Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{stamp}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def main(
    out: str | None = None,
    download_only: bool = False,
) -> dict:
    started = time.time()
    calendar = pd.bdate_range(START, END)

    universe = load_universe()
    print(f"Broad universe: {len(universe)} tickers")

    signal_panel, valid_tickers = build_pressure_signal_panel(universe, calendar)
    print(f"Signal panel shape: {signal_panel.shape}")
    print(f"Valid tickers (>= {MIN_MONTHS} months Reg SHO): {len(valid_tickers)}")

    if download_only:
        print(json.dumps({"valid_tickers": len(valid_tickers)}, indent=2))
        return {"valid_tickers": len(valid_tickers)}

    if len(valid_tickers) == 0:
        raise RuntimeError("no signal data: no tickers with sufficient Reg SHO history")

    price_panel = fetch_price_data(valid_tickers, calendar)
    if len(price_panel.columns) == 0:
        raise RuntimeError("no price data fetched")

    price_panel = price_panel[valid_tickers].ffill()
    returns = price_panel.pct_change().fillna(0.0)

    tickers = valid_tickers
    artifact = artifact_dir(out)

    train_end = pd.Timestamp(TRAIN_END)
    val_end = pd.Timestamp(VAL_END)
    train_index = calendar[calendar <= train_end]
    val_index = calendar[(calendar > train_end) & (calendar <= val_end)]
    test_index = calendar[calendar > val_end]
    oos_index = calendar[calendar > train_end]

    grid_rows = []
    for params in iter_grid():
        score = walk_forward_score(signal_panel, params, returns, tickers, train_index)
        grid_rows.append({**params, "wf_train_sharpe": score})
    grid = pd.DataFrame(grid_rows).sort_values("wf_train_sharpe", ascending=False)
    grid.to_csv(artifact / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows: train selection produced no finite score")
    best = valid.iloc[0].to_dict()

    selected = {
        "entry_z": float(best["entry_z"]),
        "exit_z": float(best["exit_z"]),
        "k": int(best["k"]),
        "vol_target": float(best["vol_target"]),
    }

    weights, _ = scaled_weights(signal_panel, selected, returns, tickers)
    full = backtest_metrics(weights, returns)
    train_result = backtest_metrics(
        weights.reindex(train_index).fillna(0.0),
        returns.reindex(train_index).fillna(0.0),
    )
    train_sharpe = annualized_sharpe(train_result["returns"])
    oos = backtest_metrics(
        weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
    )
    oos_metrics = metrics(oos["returns"], oos["equity"], oos["trades"])

    wf_stability = (
        float(oos_metrics["sharpe"] / train_sharpe)
        if np.isfinite(train_sharpe) and train_sharpe != 0
        else (float("inf") if oos_metrics["sharpe"] > 0 else 0.0)
    )

    bench_weights = passive_long_weights(returns, calendar)
    bench_raw = (bench_weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    bench_scale = vol_scale(bench_raw, selected["vol_target"])
    bench_sized = bench_weights.mul(bench_scale, axis=0)
    bench_full = backtest_metrics(bench_sized, returns)
    bench_oos = backtest_metrics(
        bench_sized.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
    )
    bench_metrics = metrics(bench_oos["returns"], bench_oos["equity"], bench_oos["trades"])
    del bench_full

    comparison = compare_to_benchmark(oos["returns"], bench_oos["returns"])
    p_value = float(comparison["alpha_p_value"])
    information_ratio = float(comparison["information_ratio"])

    random_target = random_weights(
        weights.reindex(oos_index).fillna(0.0), returns.reindex(oos_index)
    )
    random_result = backtest_metrics(
        random_target,
        returns.reindex(oos_index).fillna(0.0),
    )
    random_metrics = metrics(
        random_result["returns"], random_result["equity"], random_result["trades"]
    )

    inverse_signal = -signal_panel
    inverse_weights, _ = scaled_weights(inverse_signal, selected, returns, tickers)
    inverse_result = backtest_metrics(
        inverse_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
    )
    inverse_metrics = metrics(
        inverse_result["returns"], inverse_result["equity"], inverse_result["trades"]
    )

    perturbed = [
        value
        for value in perturbation_sharpes(signal_panel, selected, returns, tickers, oos_index)
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

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - started, 3),
        "data": {
            "source": "FINRA Reg SHO daily short volume (free/PIT by trade date)",
            "universe": "broad S&P 500/400/600",
            "universe_size": len(universe),
            "start": START,
            "end": END,
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "train_rows": int(len(train_index)),
            "val_rows": int(len(val_index)),
            "test_rows": int(len(test_index)),
            "oos_rows": int(len(oos_index)),
            "calendar": "business days; monthly refresh, shift(1) in engine",
            "unique_tickers": len(tickers),
            "min_months_regsho": MIN_MONTHS,
        },
        "grid_size": int(len(grid)),
        "selected": selected,
        "wf_train_sharpe": float(valid.iloc[0]["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sharpe),
        "full_sample": metrics(full["returns"], full["equity"], full["trades"]),
        "oos_val_test": oos_metrics,
        "val": metrics(
            oos["returns"].reindex(val_index).fillna(0.0),
            oos["equity"].reindex(val_index),
            int((oos["returns"].reindex(val_index).fillna(0.0).ne(0.0)).sum()),
        ),
        "test": metrics(
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
        "information_ratio_vs_passive_equal_weight": information_ratio,
        "perturbation": {
            "min_ratio": float(min_ratio) if np.isfinite(min_ratio) else str(min_ratio),
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
            "cost_one_way_bps": COST_ONE_WAY_BPS,
            "benchmark_pvalue_statistic": "two-sided (published gate statistic)",
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
        help="populate the Reg SHO monthly cache and exit (resumable)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    arguments = _parse_args()
    main(arguments.out, download_only=arguments.download_only)
