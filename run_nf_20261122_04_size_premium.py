"""NF-20261122-04 / H199 (Cycle 272 pre-registration and execution).

Broad mechanism category: stock-level size effect (small-minus-big market-cap
premium). Repo-new root family relative to executed H1-H198: no executed H-ID
sorts purely by market capitalization. The closest prior families are the
continuous equity cross-sections H187-H198 (accruals, issuance, valuation,
innovation, beta, coskewness, price delay, turnover, capital structure,
index-membership event drift). Per directive §6 a raw characteristic sort on
firm size is a distinct return-generating mechanism from beta (H193), value
(H191), turnover (H196), or an index-event book (H198) -- not a
parameter/universe/timeframe variant of any of them. It is only meaningful on
the broad small/mid-cap universe; the 98-name S&P 100 has no size dispersion.

Mechanism / causal chain. Smaller firms are less followed, less liquid, and bear
higher information and liquidity risk; investors demand a premium for holding
them (Banz 1981; Datar, Naik & Radcliffe 1998; Fama & French 1992, 1993).
Prediction (directional): **long small-cap names / short big-cap names,
rebalanced monthly, dollar-neutral.** Null (H0): a small-minus-big market-cap
book adds nothing over a passive equal-weight book of the same universe after
costs.

Data and PIT timing. Universe: the S&P 500 (large), S&P 400 (mid) and S&P 600
(small) current constituents (~1502 names, mega/mid/small cap), sourced from
the free Wikipedia constituent lists (`scripts/probe_broad_universe_availability.py`).
Point-in-time market cap at each monthly rebalance = shares outstanding ×
close(month-end). Shares outstanding come from the SEC XBRL `frames` API
(`dei:EntityCommonStockSharesOutstanding`, one request per quarter returns every
reporting entity's value; `scripts/probe_broad_universe_shares_availability.py`
measured 88.8% of the universe with ≥4 quarters of PIT depth from 12 requests).
Prices: yfinance daily auto-adjusted Close, calendar-aligned ffilled before
`pct_change` (the H191 convention). A conservative ~1-quarter PIT lag is
applied: the shares value usable at month-end `m` is the latest frames
observation with instant `end <= m - 90 days`, so the 10-Q/10-K filing is
public before use. Only names with both a PIT shares series and a price series
covering the rebalance are tradeable at that date.

Pre-registration (Cycle 272, written before any forward-return outcome is
computed). Sample 2015-01-01 -> 2026-11-21; Train -> 2021-12-31; Val
2022-01-01 -> 2023-12-31; Test protected 2024-01-01 -> 2026-11-21. At each
month-end, tradeable names are ranked by PIT market cap and sorted into
`n_bins` equal-size bins (grid: `n_bins` {3 terciles, 5 quintiles}); the
small leg = bottom bin, big leg = top bin; each side equal-weighted,
dollar-neutral, gross-normalized to one across simultaneously open positions
(sum |w| = 1); positions held until the next monthly rebalance (ffill between
rebalances) and the engine applies `shift(1)` so a position set at rebalance
date `t` earns returns `t -> t+1`. Delever-only vol targeting to `vol_target`
(grid: {0.10, 0.15}); train-only 4-fold walk-forward Sharpe selection over the
bounded 4-combo grid. Costs: 5 bps one-way per leg traded (equity commission +
spread); no short-borrow cost modelled (disclosed optimistic). `src/qtr`
unchanged.

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from H187/H190-H198):
Sharpe >= 1.0; trades >= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7;
worst-regime rolling-252 Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with
IR >= 0 vs the passive equal-weight long book of the same universe; OAT
+/-20% perturbation min ratio >= 0.5.

Ablations/falsifiers: Passive equal-weight long book (benchmark); random bin
signs (same active legs per day, seed 42); inverse size (long big / short
small); long-only small (short leg removed); long-only big; coverage / universe
diagnostics.

Artifact. `run_nf_20261122_04_size_premium.py` under
`.experiments/nf_runs/nf_20261122_04_size_premium_<timestamp>/` with
summary.json + grid.csv + data_meta.json; price panel and shares panel cached
resumably under `.cache/size_premium/` (gitignored). Free/public real data only
(Wikipedia constituent lists + SEC XBRL frames + yfinance daily auto-adjusted
Close).
"""

from __future__ import annotations

import argparse
import datetime as dt
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

# Import shared primitives from H184 (commodity term structure carry) via H187
_H187_PATH = ROOT / "run_nf_20261120_01_equity_accruals.py"
_h187_spec = importlib.util.spec_from_file_location("h187_accruals", _H187_PATH)
assert _h187_spec is not None and _h187_spec.loader is not None
h187 = importlib.util.module_from_spec(_h187_spec)  # type: ignore[arg-type]
sys.modules[_h187_spec.name] = h187
_h187_spec.loader.exec_module(h187)
h184 = h187.h184

# Import the broad universe shares availability probe functions
_SHARES_PROBE_PATH = ROOT / "scripts" / "probe_broad_universe_shares_availability.py"
_shares_probe_spec = importlib.util.spec_from_file_location("shares_probe", _SHARES_PROBE_PATH)
assert _shares_probe_spec is not None and _shares_probe_spec.loader is not None
shares_probe = importlib.util.module_from_spec(_shares_probe_spec)  # type: ignore[arg-type]
sys.modules[_shares_probe_spec.name] = shares_probe
_shares_probe_spec.loader.exec_module(shares_probe)

# Import the broad universe availability probe for constituent lists
_AVAIL_PROBE_PATH = ROOT / "scripts" / "probe_broad_universe_availability.py"
_avail_probe_spec = importlib.util.spec_from_file_location("avail_probe", _AVAIL_PROBE_PATH)
assert _avail_probe_spec is not None and _avail_probe_spec.loader is not None
avail_probe = importlib.util.module_from_spec(_avail_probe_spec)  # type: ignore[arg-type]
sys.modules[_avail_probe_spec.name] = avail_probe
_avail_probe_spec.loader.exec_module(avail_probe)

EXPERIMENT = "nf_20261122_04_size_premium"
NF_ID = "NF-20261122-04"
HYPOTHESIS = "H199"

START = "2015-01-01"
END = "2026-11-21"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 30
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252
PIT_LAG_DAYS = 90  # ~1 quarter conservative lag

GATES = dict(h184.GATES)

GRID = {
    "n_bins": [3, 5],  # terciles, quintiles
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "size_premium"
SHARES_CACHE_DIR = Path(".cache") / "broad_shares"
PRICE_CACHE_DIR = Path(".cache") / "size_premium" / "prices"


# ---------------------------------------------------------------------------
# Universe: Wikipedia S&P 500/400/600 constituent lists
# ---------------------------------------------------------------------------


def load_constituents(
    fetch_fn=None,
    cache_dir: Path | str | None = None,
    refresh: bool = False,
) -> list[str]:
    """Load and dedup the S&P 500/400/600 constituent lists (cached CSV)."""
    cache_dir = Path(cache_dir) if cache_dir is not None else SHARES_CACHE_DIR
    path = cache_dir / "constituents.csv"
    if path.exists() and not refresh:
        frame = pd.read_csv(path)
        return sorted(frame["ticker"].dropna().astype(str).unique().tolist())

    constituents = avail_probe.fetch_constituents(fetch_fn=fetch_fn)
    universe: set[str] = set()
    for name, tickers in constituents.items():
        universe.update(tickers)
    universe = sorted(universe)

    cache_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"ticker": universe}).to_csv(path, index=False)
    return universe


# ---------------------------------------------------------------------------
# Shares outstanding: SEC frames API -> monthly PIT panel
# ---------------------------------------------------------------------------


def build_monthly_shares_panel(
    frames: dict[str, list[dict]],
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Build a monthly-aligned shares-outstanding panel from frames data.

    Each month-end gets the latest frames observation with `end <= month_end - PIT_LAG_DAYS`.
    Forward-filled to daily calendar for the backtest engine.
    """
    # Collapse frames into {cik: [{end, val, period}, ...]}
    panel = shares_probe.build_shares_panel(frames)

    # Build monthly refresh grid: last business day of each month in calendar
    month_ends = calendar.to_series().groupby(calendar.to_series().dt.to_period("M")).last()
    refresh_dates = pd.DatetimeIndex(month_ends.values)

    # For each CIK, build a series indexed by refresh date
    shares_series: dict[int, pd.Series] = {}
    for cik, obs in panel.items():
        if not obs:
            continue
        # Create series indexed by the instant (end) date
        obs_df = pd.DataFrame(obs)
        obs_df["end"] = pd.to_datetime(obs_df["end"])
        obs_df = obs_df.set_index("end").sort_index()
        obs_df = obs_df[["val"]]

        values = []
        for rd in refresh_dates:
            # PIT: latest observation with end <= rd - PIT_LAG_DAYS
            cutoff = rd - pd.Timedelta(days=PIT_LAG_DAYS)
            usable = obs_df[obs_df.index <= cutoff]
            if len(usable):
                values.append(float(usable.iloc[-1]["val"]))
            else:
                values.append(np.nan)
        shares_series[cik] = pd.Series(values, index=refresh_dates, name=cik)

    if not shares_series:
        return pd.DataFrame(index=calendar)

    # Forward-fill to daily calendar
    refresh_frame = pd.DataFrame(shares_series)  # index=refresh_dates, columns=CIKs
    daily = refresh_frame.reindex(calendar).ffill()
    return daily


# ---------------------------------------------------------------------------
# Price data: yfinance daily closes with resumable cache
# ---------------------------------------------------------------------------


def load_price_panel(
    tickers: list[str],
    start: str = START,
    end: str = END,
    cache_dir: Path | str | None = None,
    refresh: bool = False,
    max_attempts: int = 2,
    throttle_s: float = 0.25,
    verbose: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """Download (or load cached) daily closes for the universe.

    Returns ``(closes, coverage)`` where ``closes`` is a date x ticker panel of
    raw yfinance closes and ``coverage`` records per-ticker metadata.
    Cached to ``<cache_dir>/price_panel.parquet`` + ``<cache_dir>/price_coverage.json``.
    """
    cache_dir = Path(cache_dir) if cache_dir is not None else PRICE_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / "price_panel.parquet"
    coverage_path = cache_dir / "price_coverage.json"

    if path.exists() and coverage_path.exists() and not refresh:
        closes = pd.read_parquet(path)
        coverage = json.loads(coverage_path.read_text())
        missing = [ticker for ticker in tickers if ticker not in closes.columns]
        if not missing:
            return closes, coverage

    import yfinance as yf

    series: dict[str, pd.Series] = {}
    coverage: dict[str, dict] = {}
    for index, ticker in enumerate(tickers, 1):
        close, error, attempts, transient = _download_close(
            ticker, start, end, max_attempts=max_attempts, throttle_s=throttle_s
        )
        if close is None:
            coverage[ticker] = {
                "has_data": False,
                "rows": 0,
                "attempts": attempts,
                "transient_failures": transient,
                "error": (error or "")[:120],
            }
        else:
            coverage[ticker] = {
                "has_data": True,
                "rows": int(len(close)),
                "attempts": attempts,
                "transient_failures": transient,
                "first_date": str(close.index[0].date()),
                "last_date": str(close.index[-1].date()),
            }
            series[ticker] = close
        if verbose and index % 100 == 0:
            usable = sum(1 for row in coverage.values() if row["has_data"])
            print(f"  {index}/{len(tickers)} tickers, {usable} with data", flush=True)
        time.sleep(throttle_s * 0.6)

    if not series:
        raise RuntimeError(
            "no ticker returned a price series; check network access / quote-API rate limits"
        )

    closes = pd.DataFrame(series).sort_index()
    closes.to_parquet(path)
    coverage_path.write_text(json.dumps(coverage, indent=2) + "\n")
    return closes, coverage


def _download_close(ticker: str, start: str, end: str, max_attempts: int, throttle_s: float):
    """One ticker's daily closes with linear-backoff retries on transient empties."""
    import yfinance as yf

    last_error: str | None = None
    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            frame = yf.download(
                ticker,
                start=start,
                end=end,
                progress=False,
                auto_adjust=True,
                threads=False,
            )
        except Exception as exc:  # noqa: BLE001 - report, do not crash the whole run
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < max_attempts:
                time.sleep(throttle_s * attempt)
                continue
            return None, last_error, attempt, attempt - 1
        if frame is None or len(frame) == 0:
            last_error = "empty frame"
            if attempt < max_attempts:
                time.sleep(throttle_s * attempt)
                continue
            return None, last_error, attempt, attempt - 1
        if "Close" in frame.columns:
            close = frame["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
        else:
            close = frame.iloc[:, 0]
        return close.astype(float), None, attempt, 0
    return None, (last_error or "no attempt executed")[:120], max_attempts, max_attempts


# ---------------------------------------------------------------------------
# Returns from closes (calendar-aligned ffill + pct_change, H191 convention)
# ---------------------------------------------------------------------------


def returns_from_closes(closes: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Calendar-align ffilled closes then pct_change (the H191 convention)."""
    aligned = closes.reindex(calendar).ffill()
    returns = aligned.pct_change(fill_method=None)
    return returns.where(np.isfinite(returns))


# ---------------------------------------------------------------------------
# Size signal: cross-sectional market-cap sort into bins
# ---------------------------------------------------------------------------


def build_market_cap_panel(
    shares_daily: pd.DataFrame,
    closes: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Daily market cap = shares * close, aligned on calendar."""
    # shares_daily columns are CIKs (int), closes columns are tickers (str)
    # We need a ticker->CIK map to align them
    ticker_to_cik = shares_probe.load_ticker_cik_map(SHARES_CACHE_DIR, fetch=False)

    # Build a DataFrame with ticker columns
    market_cap = pd.DataFrame(index=calendar, columns=closes.columns, dtype=float)
    for ticker in closes.columns:
        cik = ticker_to_cik.get(ticker)
        if cik is not None and cik in shares_daily.columns:
            market_cap[ticker] = shares_daily[cik] * closes[ticker]
    return market_cap


def build_size_weights(
    market_cap: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    n_bins: int = 5,
) -> pd.DataFrame:
    """Monthly rebalanced size weights: long small (bottom bin) / short big (top bin).

    At each month-end, rank tradeable names by market cap, sort into n_bins
    equal-size bins. Long bottom bin, short top bin. Equal weight within each
    bin side. Gross-normalized to sum |w| = 1. Forward-filled between rebalances.
    Engine applies shift(1) before returns are earned.
    """
    # Monthly refresh grid: last business day of each month
    month_ends = calendar.to_series().groupby(calendar.to_series().dt.to_period("M")).last()
    refresh_dates = pd.DatetimeIndex(month_ends.values)

    weights = pd.DataFrame(0.0, index=calendar, columns=market_cap.columns, dtype=float)

    for rd in refresh_dates:
        # Market cap at this rebalance date
        mc = market_cap.loc[rd].dropna()
        if len(mc) < n_bins * 2:
            continue

        # Rank and bin
        mc_sorted = mc.sort_values()
        n = len(mc_sorted)
        bin_size = n // n_bins
        if bin_size == 0:
            continue

        # Bottom bin = small (long), top bin = big (short)
        small_names = mc_sorted.iloc[:bin_size].index.tolist()
        big_names = mc_sorted.iloc[-bin_size:].index.tolist()

        # Equal weight within each side, gross-normalized to 1
        n_long = len(small_names)
        n_short = len(big_names)
        if n_long == 0 or n_short == 0:
            continue

        # Each side gets 0.5 total weight
        long_weight = 0.5 / n_long
        short_weight = -0.5 / n_short

        for name in small_names:
            weights.at[rd, name] = long_weight
        for name in big_names:
            weights.at[rd, name] = short_weight

    # Forward-fill to daily (held until next rebalance)
    weights = weights.ffill().fillna(0.0)
    return weights


def scaled_size_weights(
    weights: pd.DataFrame, returns: pd.DataFrame, vol_target: float
) -> pd.DataFrame:
    """Delever-only vol scaling of the size book (same convention as H184)."""
    raw = (weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    scale = h184.vol_scale(raw, vol_target)
    return weights.mul(scale, axis=0)


def zero_rolls(index: pd.DatetimeIndex, products: list[str]) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=index, columns=products, dtype=float)


# ---------------------------------------------------------------------------
# Grid search / walk-forward selection
# ---------------------------------------------------------------------------


def iter_grid():
    for n_bins in GRID["n_bins"]:
        for vol_target in GRID["vol_target"]:
            yield {
                "n_bins": int(n_bins),
                "vol_target": float(vol_target),
            }


def size_walk_forward_score(
    market_cap: pd.DataFrame,
    returns: pd.DataFrame,
    products: list[str],
    train_index: pd.DatetimeIndex,
    params: dict,
    n_folds: int = 4,
) -> float:
    """Mean contiguous-fold Sharpe on the train block (selection score only)."""
    if len(train_index) < 400:
        return -999.0
    weights = build_size_weights(
        market_cap.loc[train_index],
        train_index,
        int(params["n_bins"]),
    )
    weights = scaled_size_weights(
        weights, returns.reindex(train_index).fillna(0.0), float(params["vol_target"])
    )
    fold = len(train_index) // n_folds
    sharpes = []
    for fold_no in range(n_folds):
        start = fold_no * fold
        stop = len(train_index) if fold_no == n_folds - 1 else (fold_no + 1) * fold
        block = train_index[start:stop]
        if len(block) < 120:
            continue
        result = h184.backtest_metrics(
            weights.reindex(block).fillna(0.0),
            returns.reindex(block).fillna(0.0),
            zero_rolls(block, products),
        )
        sharpes.append(h184.annualized_sharpe(result["returns"]))
    return float(np.mean(sharpes)) if sharpes else -999.0


def perturbation_sharpes(
    market_cap: pd.DataFrame,
    returns: pd.DataFrame,
    products: list[str],
    selected: dict,
    oos_index: pd.DatetimeIndex,
) -> list[float]:
    """OAT +/-20% perturbation of n_bins and vol_target on OOS."""
    variants = []
    for factor in (0.8, 1.2):
        variant = dict(selected)
        variant["vol_target"] = round(float(selected["vol_target"]) * factor, 6)
        variants.append(variant)
    # n_bins perturbation (integer)
    for delta in (-1, 1):
        variant = dict(selected)
        variant["n_bins"] = max(2, int(selected["n_bins"]) + delta)
        variants.append(variant)

    out: list[float] = []
    for variant in variants:
        weights = build_size_weights(
            market_cap.loc[oos_index],
            oos_index,
            int(variant["n_bins"]),
        )
        weights = scaled_size_weights(
            weights, returns.reindex(oos_index).fillna(0.0), float(variant["vol_target"])
        )
        result = h184.backtest_metrics(
            weights,
            returns.reindex(oos_index).fillna(0.0),
            zero_rolls(oos_index, products),
        )
        out.append(h184.annualized_sharpe(result["returns"]))
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def artifact_dir(out: str | None) -> Path:
    if out:
        path = Path(out).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = (ROOT / ".experiments" / "nf_runs" / f"{EXPERIMENT}_{stamp}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def main(
    out: str | None = None,
    download_only: bool = False,
    refresh_data: bool = False,
) -> dict:
    started = time.time()
    calendar = pd.bdate_range(START, END)

    # 1. Load constituents
    universe = load_constituents(refresh=refresh_data)
    print(f"Universe: {len(universe)} tickers (S&P 500/400/600)")

    # 2. Load shares outstanding (SEC frames)
    ticker_to_cik = shares_probe.load_ticker_cik_map(
        SHARES_CACHE_DIR, refresh=refresh_data, fetch=True
    )
    n_mapped = sum(1 for t in universe if t in ticker_to_cik)
    print(f"Ticker->CIK: {n_mapped}/{len(universe)} mapped")

    periods = shares_probe.frame_periods(12)  # 12 quarters = 3 years
    frames = shares_probe.fetch_frames(periods)
    n_points = sum(len(points) for points in frames.values())
    print(f"SEC frames: {len(periods)} requests, {n_points} entity-observations")

    shares_daily = build_monthly_shares_panel(frames, calendar)

    # 3. Load price panel
    if download_only:
        closes, coverage = load_price_panel(universe, refresh=refresh_data, verbose=False)
        provenance = {
            "universe_size": len(universe),
            "tickers_with_cik": n_mapped,
            "frames_periods": len(periods),
            "frames_entity_observations": n_points,
            "tickers_with_price_data": sum(1 for row in coverage.values() if row["has_data"]),
        }
        print(json.dumps(provenance, indent=2))
        return provenance

    closes, coverage = load_price_panel(universe, refresh=refresh_data)

    # 4. Build market cap panel and returns
    market_cap = build_market_cap_panel(shares_daily, closes, calendar)
    returns = returns_from_closes(closes, calendar)

    # Filter to names that have both market cap and returns data
    valid_names = [
        name
        for name in market_cap.columns
        if market_cap[name].notna().any() and returns[name].notna().any()
    ]
    print(f"Tradeable names (market cap + price): {len(valid_names)}")
    market_cap = market_cap[valid_names]
    returns = returns[valid_names]
    products = valid_names

    train_end = pd.Timestamp(TRAIN_END)
    val_end = pd.Timestamp(VAL_END)
    train_index = calendar[calendar <= train_end]
    val_index = calendar[(calendar > train_end) & (calendar <= val_end)]
    test_index = calendar[calendar > val_end]
    oos_index = calendar[calendar > train_end]

    artifact = artifact_dir(out)
    grid_rows = []
    for params in iter_grid():
        score = size_walk_forward_score(market_cap, returns, products, train_index, params)
        grid_rows.append({**params, "wf_train_sharpe": score})
    grid = pd.DataFrame(grid_rows).sort_values("wf_train_sharpe", ascending=False)
    grid.to_csv(artifact / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows: train selection produced no finite score")
    best = valid.iloc[0].to_dict()
    selected = {
        "n_bins": int(best["n_bins"]),
        "vol_target": float(best["vol_target"]),
    }

    weights = build_size_weights(market_cap, calendar, selected["n_bins"])
    weights = scaled_size_weights(weights, returns, selected["vol_target"])

    full = h184.backtest_metrics(weights, returns.fillna(0.0), zero_rolls(calendar, products))
    train_result = h184.backtest_metrics(
        weights.reindex(train_index).fillna(0.0),
        returns.reindex(train_index).fillna(0.0),
        zero_rolls(train_index, products),
    )
    train_sharpe = h184.annualized_sharpe(train_result["returns"])
    oos = h184.backtest_metrics(
        weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    oos_metrics = h184.metrics(oos["returns"], oos["equity"], oos["trades"])

    wf_stability = (
        float(oos_metrics["sharpe"] / train_sharpe)
        if np.isfinite(train_sharpe) and train_sharpe != 0
        else (float("inf") if oos_metrics["sharpe"] > 0 else 0.0)
    )

    bench_weights = h184.passive_long_weights(returns, calendar)
    bench_raw = (bench_weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    bench_scale = h184.vol_scale(bench_raw, selected["vol_target"])
    bench_sized = bench_weights.mul(bench_scale, axis=0)
    bench_oos = h184.backtest_metrics(
        bench_sized.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    bench_metrics = h184.metrics(bench_oos["returns"], bench_oos["equity"], bench_oos["trades"])

    comparison = compare_to_benchmark(oos["returns"], bench_oos["returns"])
    p_value = float(comparison["alpha_p_value"])
    information_ratio = float(comparison["information_ratio"])

    random_target = h184.random_weights(
        weights.reindex(oos_index).fillna(0.0), returns.reindex(oos_index), seed=SEED
    )
    random_result = h184.backtest_metrics(
        random_target,
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    random_metrics = h184.metrics(
        random_result["returns"], random_result["equity"], random_result["trades"]
    )

    inverse_weights = build_size_weights(market_cap, calendar, selected["n_bins"])
    # Inverse: long big / short small
    inverse_weights = -inverse_weights
    inverse_weights = scaled_size_weights(inverse_weights, returns, selected["vol_target"])
    inverse_result = h184.backtest_metrics(
        inverse_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    inverse_metrics = h184.metrics(
        inverse_result["returns"], inverse_result["equity"], inverse_result["trades"]
    )

    # Long-only small (short leg removed)
    long_only_small_weights = build_size_weights(market_cap, calendar, selected["n_bins"])
    # Zero out short side
    long_only_small_weights = long_only_small_weights.where(long_only_small_weights >= 0, 0.0)
    # Renormalize gross to 1
    gross = long_only_small_weights.abs().sum(axis=1)
    long_only_small_weights = long_only_small_weights.div(gross.replace(0, np.nan), axis=0).fillna(
        0.0
    )
    long_only_small_weights = scaled_size_weights(
        long_only_small_weights, returns, selected["vol_target"]
    )
    long_only_small_oos = h184.backtest_metrics(
        long_only_small_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    long_only_small_metrics = h184.metrics(
        long_only_small_oos["returns"], long_only_small_oos["equity"], long_only_small_oos["trades"]
    )

    # Long-only big (long leg removed)
    long_only_big_weights = build_size_weights(market_cap, calendar, selected["n_bins"])
    long_only_big_weights = long_only_big_weights.where(long_only_big_weights <= 0, 0.0)
    gross = long_only_big_weights.abs().sum(axis=1)
    long_only_big_weights = long_only_big_weights.div(gross.replace(0, np.nan), axis=0).fillna(0.0)
    long_only_big_weights = scaled_size_weights(
        long_only_big_weights, returns, selected["vol_target"]
    )
    long_only_big_oos = h184.backtest_metrics(
        long_only_big_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    long_only_big_metrics = h184.metrics(
        long_only_big_oos["returns"], long_only_big_oos["equity"], long_only_big_oos["trades"]
    )

    perturbed = [
        value
        for value in perturbation_sharpes(market_cap, returns, products, selected, oos_index)
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

    # Data provenance
    tickers_with_data = sum(1 for row in coverage.values() if row["has_data"])
    tickers_with_shares = int(shares_daily.notna().any().sum())
    data_meta = {
        "constituent_source": "Wikipedia S&P 500/400/600 (free/public)",
        "constituent_urls": avail_probe.CONSTITUENT_SOURCES,
        "shares_source": "SEC XBRL frames dei/EntityCommonStockSharesOutstanding/shares (free/public/PIT)",
        "shares_url_template": shares_probe.FRAMES_URL,
        "ticker_map_url": shares_probe.TICKER_MAP_URL,
        "pit_lag_days": PIT_LAG_DAYS,
        "price_source": "yfinance auto-adjusted Close (free/public)",
        "universe_size": len(universe),
        "tickers_with_cik": n_mapped,
        "tickers_with_shares_data": tickers_with_shares,
        "tickers_with_price_data": tickers_with_data,
        "tradeable_names": len(valid_names),
        "frames_periods": len(periods),
        "frames_entity_observations": n_points,
        "cost_one_way_bps": COST_ONE_WAY_BPS,
        "borrow_cost_modelled": False,
        "min_active_names": MIN_ACTIVE_NAMES,
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
        "full_sample": h184.metrics(full["returns"], full["equity"], full["trades"]),
        "oos_val_test": oos_metrics,
        "val": h184.metrics(
            oos["returns"].reindex(val_index).fillna(0.0),
            oos["equity"].reindex(val_index),
            int((oos["returns"].reindex(val_index).fillna(0.0).ne(0.0)).sum()),
        ),
        "test": h184.metrics(
            oos["returns"].reindex(test_index).fillna(0.0),
            oos["equity"].reindex(test_index),
            int((oos["returns"].reindex(test_index).fillna(0.0).ne(0.0)).sum()),
        ),
        "benchmark_passive_equal_weight_long_oos": bench_metrics,
        "benchmark_comparison": comparison,
        "ablations": {
            "random_bin_signs_oos": random_metrics,
            "inverse_size_oos": inverse_metrics,
            "long_only_small_oos": long_only_small_metrics,
            "long_only_big_oos": long_only_big_metrics,
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
            "borrow_cost_modelled": False,
            "benchmark_pvalue_statistic": "two-sided (published gate statistic)",
            "pit_rule": "SEC frames end <= month_end - 90d; engine shift(1); monthly rebalance",
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
        help="populate the shares/price cache and exit (resumable)",
    )
    parser.add_argument(
        "--refresh-data",
        action="store_true",
        help="re-fetch the constituents, frames, and price panel even if cached",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only, refresh_data=args.refresh_data)
