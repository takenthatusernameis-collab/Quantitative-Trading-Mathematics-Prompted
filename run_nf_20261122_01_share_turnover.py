"""NF-20261122-01 / H196 (Cycle 250 pre-registration and execution).

Broad mechanism category: liquidity / trading-activity (stock-level share
turnover). Repo-new root family relative to executed H1-H195: no executed H-ID
sorts single stocks by their *share turnover* (trading volume divided by shares
outstanding) into a long-low-turnover / short-high-turnover cross-section. The
closest prior families are H121 (SPY-level Amihud illiquidity *regime timing* --
a single-asset |return|/dollar-volume risk-off overlay, not a cross-section),
H19/H20 (volume / order-flow *direction* timing on SPY/QQQ/IWM, not a
cross-section), H2/H16/H117/H119 (cross-sectional momentum / reversal on *own
past return*) and the value / quality / volatility / higher-moment families
(H191 value, H187/H188/H189 fundamentals, H193 beta, H194 coskewness, H195
delay). Turnover is a *liquidity / trading-activity* characteristic -- how
actively a stock trades relative to its size -- which is none of a past return,
a fundamental ratio, a volatility / higher moment, a beta, or a response-speed
friction. A turnover-sorted long/short stock book is a distinct portfolio
construction. That makes it a distinct return-generating mechanism (per
directive sec. 6), not a parameter/universe/market variant of any prior family.

Mechanism / causal chain.  Two well-documented channels predict the same sign.
(i) Liquidity premium (Datar, Naik & Radcliffe 1998; Amihud & Mendelson 1986):
high turnover proxies for high liquidity, and liquid stocks carry a *lower*
expected return than illiquid stocks because investors accept a lower return for
the ability to trade cheaply; illiquid (low-turnover) stocks must offer a
liquidity risk premium. (ii) Overvaluation / speculation (Baker & Wurgler 2013;
Baker, Stein & Wurgler 2012): high turnover reflects speculative demand and
overpricing, which reverses, so high-turnover stocks subsequently earn lower
returns. Both channels predict: **long the bottom-k names by turnover (least
active / most illiquid / most undervalued), short the top-k (most active / most
liquid / most overvalued).** Null (H0): the turnover cross-section carries no
predictive power for next-period equity returns after costs -- a low-turnover
tilt adds nothing over a passive equal-weight book of the same universe.

Mechanism separation from H121 / H19 / H20 / momentum.  H121 is a *single-asset*
(SPY) Amihud price-impact *timing* overlay (|return| / dollar-volume z-score
reduces exposure when liquidity is stressed); H196 is a *cross-sectional*
stock-level *turnover* (volume / shares outstanding) long-low / short-high book.
H19/H20 predict the *direction* of an index from lagged volume / order flow; they
are market-timing, not a stock-selection cross-section. Momentum/reversal families
(H2/H16/H117/H119) rank on the stock's *own past return*; turnover ranks on
*trading activity relative to size*. A stock can be high-momentum but low-turnover,
or low-momentum but high-turnover. Turnover is therefore not reproducible as a
momentum / volume-timing / amihud-timing variant; the run reports cross-sectional
Spearman diagnostics vs beta (H193), trailing 252-day return (momentum) and
trailing 252-day volatility.

PIT / causality.  The share count at month-refresh date R is the latest 10-K
share count *filed* on/before R (the SEC acceptance date; no fiscal-period
``end`` is ever used as an availability stamp). Turnover at R = trailing
``window``-trading-day share volume (from yfinance, known at R) / that share
count. The shared engine applies ``shift(1)``, so a position formed at close R
earns R -> R+1 -- strictly causal. The panel refreshes on the first business day
of each month and is forward-filled to the daily calendar (turnover at most
monthly).

Pre-registration (Cycle 250, written before any forward-return outcome was
computed).  Sample 2011-01-03 -> 2026-11-21; Train -> 2021-12-31; Val
2022-01-01 -> 2023-12-31; Test protected 2024-01-01 -> 2026-11-21.  Universe:
the 100-name S&P 100 snapshot in
``scripts/probe_sec_xbrl_fundamentals.py:UNIVERSE`` minus XOM and BKNG (same
measured exclusions as H187/H188/H191/H192/H193/H194/H195) = 98 names; only names
with >= 2 annual share-count observations are tradeable (measured below, well
above the 40-name minimum).  Features ``turnover_21`` (1-month) and
``turnover_252`` (1-year) are both estimated; the traded signal is the selected
one and the pair is a collinearity diagnostic.  Cross-sectional z on the monthly
refresh grid, winsorized at +/-3, hysteresis entry_z/exit_z, long bottom-k
(lowest turnover) / short top-k (highest turnover), gross-normalized,
forward-filled to the daily calendar.  Grid (bounded, 16): feature
{turnover_21, turnover_252} x entry_z {0.5, 1.0} x exit_z {0.0} x k {5, 10} x
vol_target {0.10, 0.15}; train-only 4-fold walk-forward Sharpe selection.  Costs:
5 bps one-way per leg traded; no borrow cost for shorts is modelled -- disclosed
as an optimistic assumption for a long/short equity book (identical to
H187/H191/H192/H193/H194/H195).

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from
H187/H190/H191/H192/H193/H194/H195): Sharpe >= 1.0; trades >= 50; PF >= 1.3;
maxDD <= 15%; WF stability >= 0.7; worst-regime rolling-252 Sharpe >= 0.3;
benchmark p <= 0.05 (two-sided) with IR >= 0 vs the passive equal-weight long
book of the same universe; OAT +/-20% perturbation min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same active
leg count, seed 42); inverse signal (anti-turnover, i.e. long high-turnover /
short low-turnover); train-block Spearman of ``turnover_21`` vs ``turnover_252``
as an input-collinearity diagnostic; cross-sectional Spearman of turnover vs beta
(H193), trailing 252-day return (momentum) and trailing 252-day volatility as
mechanism-separation diagnostics.

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors, share-count loader and cross-sectional/hysteresis
primitives from run_nf_20261121_01_equity_value.py (H191), which in turn imports
run_nf_20261120_01_equity_accruals.py (H187) and
run_nf_20261114_01_commodity_termstructure_carry.py (H184). Only the share-turnover
panel construction is new code.  Free/public real data only (SEC XBRL companyfacts
share counts + yfinance daily auto-adjusted Close and Volume); ``src/qtr``
unchanged.  Artifact under
.experiments/nf_runs/nf_20261122_01_share_turnover_<timestamp>/summary.json +
grid.csv + data_meta.json.
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

# Reuse the H191 equity-value runner (which exposes h187 / h184 / the XBRL probe
# and the share-count loader). Only the turnover panel is new code.
_H191_PATH = ROOT / "run_nf_20261121_01_equity_value.py"
_h191_spec = importlib.util.spec_from_file_location("h191_value", _H191_PATH)
assert _h191_spec is not None and _h191_spec.loader is not None
h191 = importlib.util.module_from_spec(_h191_spec)  # type: ignore[arg-type]
sys.modules[_h191_spec.name] = h191
_h191_spec.loader.exec_module(h191)

h187 = h191.h187
h184 = h191.h184
xbrl = h191.xbrl

EXPERIMENT = "nf_20261122_01_share_turnover"
NF_ID = "NF-20261122-01"
HYPOTHESIS = "H196"

START = "2011-01-03"
END = "2026-11-21"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

# Universe: the probe's 100-name S&P 100 snapshot minus XOM and BKNG (same as
# H187/H188/H191/H192/H193/H194/H195).
UNIVERSE_SYMBOLS = [s for s in xbrl.UNIVERSE if s not in ("XOM", "BKNG")]
assert len(UNIVERSE_SYMBOLS) == 98

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 40
MIN_SHARE_OBSERVATIONS = 2
MIN_PRICE_OBSERVATIONS = 252
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252

GATES = dict(h184.GATES)

TURNOVER_WINDOWS = [21, 252]
FEATURES = [f"turnover_{window}" for window in TURNOVER_WINDOWS]
GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [5, 10],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "xbrl"
SHARE_TAGS = h191.SHARE_TAGS


# ---------------------------------------------------------------------------
# Data acquisition: load cached share counts and equity prices, build monthly
# turnover panels.
# ---------------------------------------------------------------------------


def shares_observations(facts: dict) -> pd.DataFrame:
    """Point-in-time annual share counts for one company.

    Uses the same (namespace, tag) priority and per-``end`` filed-dedup as the
    H191 equity-value runner (``CommonStockSharesOutstanding`` ->
    ``WeightedAverageNumberOfSharesOutstandingBasic`` ->
    ``dei:EntityCommonStockSharesOutstanding``).  ``filed`` is the SEC
    acceptance date; a share count is only usable from that date onward.
    """
    for namespace, tag in SHARE_TAGS:
        candidate = h191._share_rows(facts, namespace, tag)
        candidate = (
            candidate.dropna(subset=["end", "filed", "val"]) if len(candidate) else candidate
        )
        if len(candidate):
            return (
                candidate.sort_values("filed")
                .drop_duplicates("end", keep="first")[["end", "filed", "val"]]
                .rename(columns={"val": "shares"})
                .reset_index(drop=True)
            )
    return pd.DataFrame(columns=["end", "filed", "shares"])


def load_all_shares(
    symbols: list[str],
    cache_dir: Path = CACHE_DIR,
) -> dict[str, pd.DataFrame]:
    """Load per-symbol share-count observations from cached companyfacts.

    Fetches on demand (the cache is git-ignored and empty on a fresh clone) and
    skips symbols whose companyfacts cannot be retrieved or lack a share tag.
    """
    mapping = xbrl.load_ticker_cik_map(Path(cache_dir) / "company_tickers.json", fetch=True)
    observations: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        cik = mapping.get(symbol.upper())
        if cik is None:
            continue
        try:
            facts = xbrl.cached_companyfacts(cik, cache_dir, fetch=True)
        except Exception:  # network/HTTP; skip this symbol, keep the rest
            continue
        obs = shares_observations(facts)
        if len(obs) >= MIN_SHARE_OBSERVATIONS:
            observations[symbol] = obs
    return observations


def load_or_fetch_prices(products: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load cached equity closes and volumes, fetching from yfinance if absent."""
    cache_dir = Path(".cache") / "xbrl"
    cache_dir.mkdir(parents=True, exist_ok=True)
    price_path = cache_dir / "equity_closes.csv"
    volume_path = cache_dir / "equity_volume.csv"
    if price_path.exists() and volume_path.exists():
        closes = pd.read_csv(price_path, index_col=0, parse_dates=True)
        volumes = pd.read_csv(volume_path, index_col=0, parse_dates=True)
        if set(products).issubset(set(closes.columns)) and set(products).issubset(
            set(volumes.columns)
        ):
            return (
                closes.reindex(columns=list(products)),
                volumes.reindex(columns=list(products)),
            )
    import yfinance as yf

    raw = yf.download(list(products), start=START, end=END, auto_adjust=True, progress=False)
    closes = raw["Close"].reindex(columns=list(products))
    volumes = raw["Volume"].reindex(columns=list(products))
    closes.to_csv(price_path)
    volumes.to_csv(volume_path)
    return closes, volumes


def returns_from_closes(closes: pd.DataFrame) -> pd.DataFrame:
    """Daily simple returns, non-finite -> NaN (first row is all-NaN by design)."""
    returns = closes.pct_change(fill_method=None)
    return returns.replace([np.inf, -np.inf], np.nan)


def _refresh_dates(calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First business day of each month in ``calendar`` (monthly refresh grid)."""
    series = calendar.to_series()
    return pd.DatetimeIndex(series.groupby(series.dt.to_period("M")).first().values)


def build_turnover_panels(
    shares: dict[str, pd.DataFrame],
    volumes: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> dict[str, pd.DataFrame]:
    """Construct monthly-refreshed share-turnover panels for each window.

    Turnover = trailing ``window``-trading-day share volume / latest filed share
    count.  Turnover is slow-moving, so it is sampled on each month's first
    business day and forward-filled to the daily calendar; turnover therefore
    happens at most monthly.  The share count at refresh date R is the latest
    10-K share count *filed* on/before R (never the fiscal-period end).
    """
    refresh = _refresh_dates(calendar)
    volume_panel = volumes.fillna(0.0)
    panels: dict[str, pd.DataFrame] = {}
    for window in TURNOVER_WINDOWS:
        trailing_volume = volume_panel.rolling(window, min_periods=window).sum()
        volume_at_refresh = trailing_volume.reindex(refresh)
        series: dict[str, pd.Series] = {}
        for symbol, obs in shares.items():
            obs = obs.dropna(subset=["filed", "shares"]).sort_values("filed")
            values: list[float] = []
            for rd in refresh:
                usable = obs[obs["filed"] <= rd]
                if not len(usable):
                    values.append(np.nan)
                    continue
                share_count = float(usable.iloc[-1]["shares"])
                volume = (
                    float(volume_at_refresh.at[rd, symbol])
                    if symbol in volume_at_refresh.columns
                    else np.nan
                )
                if (
                    np.isfinite(share_count)
                    and share_count > 0.0
                    and np.isfinite(volume)
                    and volume >= 0.0
                ):
                    values.append(volume / share_count)
                else:
                    values.append(np.nan)
            series[symbol] = pd.Series(values, index=refresh)
        daily = pd.DataFrame(series).reindex(calendar).ffill()
        panels[f"turnover_{window}"] = daily.reindex(columns=list(shares.keys()))
    return panels


# ---------------------------------------------------------------------------
# Signal, sizing and backtest (reuse h187 / h184 primitives; long-low direction)
# ---------------------------------------------------------------------------


def target_weights(
    feature_daily: pd.DataFrame,
    params: dict,
    returns: pd.DataFrame,
    products: list[str],
) -> pd.DataFrame:
    """Cross-sectional z + long-low hysteresis on daily turnover, vol-target scaled.

    Turnover direction is long the *lowest* turnover (illiquid / undervalued) and
    short the *highest* (liquid / overvalued), which is exactly h187's long-low
    hysteresis convention (``signal_weights``: long where z <= -entry_z, short
    where z >= entry_z).  The z-score is winsorized at +/-3 (h187 contract).
    """
    return h187.target_weights(feature_daily, params, returns, products)


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


def train_collinearity(features: dict[str, pd.DataFrame], train_index: pd.DatetimeIndex) -> float:
    """Input-only diagnostic: cross-sectional Spearman of turnover_21 vs turnover_252."""
    left, right = features["turnover_21"], features["turnover_252"]
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
    return float(np.mean(values)) if values else 0.0


def _mean_cross_sectional_spearman(
    left: pd.DataFrame, right: pd.DataFrame, index: pd.DatetimeIndex
) -> float | None:
    """Average cross-sectional Spearman of two daily panels over ``index``."""
    values = []
    for day in index:
        a, b = left.loc[day], right.loc[day]
        usable = a.notna() & b.notna()
        if int(usable.sum()) < 3:
            continue
        a_vals, b_vals = a[usable], b[usable]
        if a_vals.nunique() < 2 or b_vals.nunique() < 2:
            continue
        value = float(a_vals.corr(b_vals, method="spearman"))
        if np.isfinite(value):
            values.append(value)
    return float(np.mean(values)) if values else None


def trailing_total_return(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """Trailing cumulative simple return over ``window`` days (causal momentum)."""
    growth = (1.0 + returns).rolling(window, min_periods=window).apply(np.prod, raw=True)
    return growth - 1.0


def trailing_volatility(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """Trailing realized volatility (population std) over ``window`` days."""
    return returns.rolling(window, min_periods=window).std(ddof=0)


def train_mechanism_separation(
    turnover_features: dict[str, pd.DataFrame],
    beta_features: dict[str, pd.DataFrame] | None,
    returns: pd.DataFrame,
    train_index: pd.DatetimeIndex,
) -> dict[str, float]:
    """Cross-sectional Spearman of turnover_252 vs beta (H193), momentum and vol."""
    diagnostics: dict[str, float] = {}
    turnover = turnover_features["turnover_252"]
    # Momentum / volatility are computed from ``returns`` (yfinance trading days);
    # align them to the turnover panel's daily calendar so the exact-label
    # Spearman lookup does not fail on market holidays the synthetic
    # ``pd.bdate_range`` calendar includes but ``returns`` does not.
    calendar_index = turnover.index

    if beta_features is not None:
        beta = beta_features.get("beta_252")
        if beta is not None:
            value = _mean_cross_sectional_spearman(turnover, beta, train_index)
            if value is not None:
                diagnostics["turnover_252_vs_beta_252"] = value

    momentum = trailing_total_return(returns, 252).reindex(calendar_index)
    value = _mean_cross_sectional_spearman(turnover, momentum, train_index)
    if value is not None:
        diagnostics["turnover_252_vs_momentum_252"] = value

    volatility = trailing_volatility(returns, 252).reindex(calendar_index)
    value = _mean_cross_sectional_spearman(turnover, volatility, train_index)
    if value is not None:
        diagnostics["turnover_252_vs_realized_vol_252"] = value

    return diagnostics


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


def main(out: str | None = None, download_only: bool = False) -> dict:
    started = time.time()
    calendar = pd.bdate_range(START, END)
    products = list(UNIVERSE_SYMBOLS)

    shares = load_all_shares(products)
    if download_only:
        coverage = {
            "symbols_with_share_observations": int(len(shares)),
            "total_symbols_requested": len(UNIVERSE_SYMBOLS),
            "min_share_observations": int(min((len(obs) for obs in shares.values()), default=0)),
        }
        print(json.dumps(coverage, indent=2))
        return coverage

    if len(shares) < MIN_ACTIVE_NAMES:
        raise RuntimeError(f"share universe {len(shares)} < MIN_ACTIVE_NAMES {MIN_ACTIVE_NAMES}")

    closes, volumes = load_or_fetch_prices(products)
    returns = returns_from_closes(closes)

    # Restrict to names with >= MIN_PRICE_OBSERVATIONS valid daily returns and
    # >= MIN_SHARE_OBSERVATIONS share observations.
    valid_counts = returns.notna().sum()
    products = [
        symbol for symbol in shares if int(valid_counts.get(symbol, 0)) >= MIN_PRICE_OBSERVATIONS
    ]
    if len(products) < MIN_ACTIVE_NAMES:
        raise RuntimeError(
            f"tradable turnover universe {len(products)} < MIN_ACTIVE_NAMES {MIN_ACTIVE_NAMES}"
        )
    shares = {symbol: shares[symbol] for symbol in products}
    volumes = volumes.reindex(columns=products)
    closes = closes.reindex(columns=products)
    returns = returns.reindex(columns=products)

    features_daily = build_turnover_panels(shares, volumes, calendar)
    for feat in FEATURES:
        if features_daily[feat].empty:
            raise RuntimeError(f"no {feat} signal built")

    train_end = pd.Timestamp(TRAIN_END)
    val_end = pd.Timestamp(VAL_END)
    train_index = calendar[calendar <= train_end]
    val_index = calendar[(calendar > train_end) & (calendar <= val_end)]
    test_index = calendar[calendar > val_end]
    oos_index = calendar[calendar > train_end]

    artifact = artifact_dir(out)
    grid_rows = []
    for params in iter_grid():
        score = h187.walk_forward_score(
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

    weights = target_weights(feature_daily, selected, returns, products)
    full = h184.backtest_metrics(weights, returns, h187.zero_rolls(calendar, products))
    train_result = h184.backtest_metrics(
        weights.reindex(train_index).fillna(0.0),
        returns.reindex(train_index).fillna(0.0),
        h187.zero_rolls(train_index, products),
    )
    train_sharpe = h184.annualized_sharpe(train_result["returns"])
    oos = h184.backtest_metrics(
        weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        h187.zero_rolls(oos_index, products),
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
        h187.zero_rolls(oos_index, products),
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
        h187.zero_rolls(oos_index, products),
    )
    random_metrics = h184.metrics(
        random_result["returns"], random_result["equity"], random_result["trades"]
    )

    inverse_weights = target_weights(-feature_daily, selected, returns, products)
    inverse_result = h184.backtest_metrics(
        inverse_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        h187.zero_rolls(oos_index, products),
    )
    inverse_metrics = h184.metrics(
        inverse_result["returns"], inverse_result["equity"], inverse_result["trades"]
    )

    perturbed = [
        value
        for value in h187.perturbation_sharpes(
            feature_daily, selected, returns, products, oos_index
        )
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

    # For beta separation, reuse H193's beta panels (input-only diagnostic).
    from run_nf_20261121_03_bab_beta import build_beta_panels as build_beta_panels_h193

    beta_features = build_beta_panels_h193(returns, calendar, products)
    separation = train_mechanism_separation(features_daily, beta_features, returns, train_index)

    data_meta = {
        "equity_source": "yfinance auto-adjusted Close and Volume (free/public)",
        "shares_source": "SEC XBRL companyfacts share counts, PIT by filed date (free/public)",
        "turnover_definition": (
            "trailing window trading-day share volume / latest filed shares outstanding"
        ),
        "turnover_windows": TURNOVER_WINDOWS,
        "universe_symbols": products,
        "universe_size": len(products),
        "excluded_symbols": ["XOM", "BKNG"],
        "symbols_with_share_observations": int(len(shares)),
        "min_price_observations": MIN_PRICE_OBSERVATIONS,
        "min_share_observations": MIN_SHARE_OBSERVATIONS,
        "features": FEATURES,
        "min_active_names": MIN_ACTIVE_NAMES,
        "cost_one_way_bps": COST_ONE_WAY_BPS,
        "borrow_cost_modelled": False,
        "monthly_refresh": True,
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
        "train_input_collinearity_turnover21_vs_turnover252": collinearity,
        "train_mechanism_separation": separation,
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
            "pit_rule": "trailing share volume through t only / latest filed shares, engine shift(1), monthly refresh",
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
        help="report share-history coverage and exit (no backtest)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only)
