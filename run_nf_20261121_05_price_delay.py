"""NF-20261121-05 / H195 (Cycle 249 pre-registration and execution).

Broad mechanism category: market frictions / slow information diffusion
(stock-level price delay). Repo-new root family relative to executed H1-H194:
no executed H-ID sorts single stocks by their *delay* (the sluggishness with
which a stock's price responds to market-wide information) into a
long-high-delay / short-low-delay cross-section. The closest prior families are
H93 (idiosyncratic-volatility cross-section -- residual *second* moment vs the
market), H128 (realized skewness -- a single-asset *third* moment), H194
(coskewness -- a *systematic third* moment) and the momentum/reversal families
(H2/H16/H117/H119 -- past *own* return). Hou & Moskowitz (2005, "Market
Frictions, Delay, and the Response of Stock Prices", Review of Financial
Studies) define delay as the degree to which a stock's return responds to
lagged market returns rather than only the contemporaneous market return; it is
a *response-speed* friction measure, not a volatility, higher-moment, or
past-return measure. A delay-sorted long/short stock book is a distinct
portfolio construction. That makes it a distinct return-generating mechanism
(per directive sec. 6), not a parameter/universe/market variant of any prior
family.

Mechanism / causal chain.  Frictions -- limited investor attention, slow
information diffusion, and transaction/participation costs -- cause a stock's
price to incorporate market-wide information with a lag. Stocks with *high*
delay (slow response) underreact to market-wide news and subsequently earn
higher returns as the information is incorporated; stocks with *low* delay
(fast response) have already priced the information and earn no such drift
(Hou & Moskowitz 2005). Prediction (directional): **long the top-k names by
delay (slowest response), short the bottom-k (fastest response).** Null (H0):
the delay cross-section carries no predictive power for next-period equity
returns after costs -- a high-delay-minus-low-delay tilt adds nothing over a
passive equal-weight book of the same universe. The mechanism can persist
because limited attention and slow diffusion are structural behavioural
frictions that do not arbitrage away in a large-cap universe.

Mechanism separation from H93 / H128 / H194 / momentum.  H93 (idiosyncratic
volatility) ranks on the *residual standard deviation* of symbol-minus-SPY
returns -- a second moment. H128 (realized skewness) and H194 (coskewness) rank
on *third* moments (own and systematic). The momentum/reversal families rank
on the stock's *own past return*. Delay ranks on the *lag structure* of the
stock's response to *market* returns (contemporaneous vs lagged market
co-movement). A stock can be high-momentum but low-delay (it responds fast to
market news), or low-momentum but high-delay. Delay is therefore not
reproducible as a volatility, higher-moment, or momentum/reversal variant; the
run reports cross-sectional Spearman diagnostics vs beta (H193), trailing
252-day return (momentum) and trailing 252-day volatility.

PIT / causality.  Delay at day t is estimated from a trailing window of daily
returns and market returns through t only (the design uses lagged market
returns, never future ones); the shared engine applies ``shift(1)``, so the
target set at close t earns the return t -> t+1 -- strictly causal, no
same-day look-ahead. The market proxy is the equal-weight mean of the tradable
universe's contemporaneous returns (a broad-market proxy; each name carries
1/98 weight, so the own-inclusion bias is ~1%, disclosed). Delay is
slow-moving, so the signal refreshes monthly (first business day of each month)
and forward-fills to the daily calendar, so turnover happens at most monthly.

Pre-registration (Cycle 249, written before any forward-return outcome was
computed).  Sample 2011-01-03 -> 2026-11-21; Train -> 2021-12-31; Val
2022-01-01 -> 2023-12-31; Test protected 2024-01-01 -> 2026-11-21.  Universe:
the 100-name S&P 100 snapshot in
``scripts/probe_sec_xbrl_fundamentals.py:UNIVERSE`` minus XOM and BKNG (same
measured exclusions as H187/H188/H191/H192/H193/H194) = 98 names; all 98 have
>= 252 valid daily returns (measured min 441), so no name is dropped for short
history. Features ``delay_252`` (12-month trailing delay) and ``delay_126``
(6-month) are both estimated; the traded signal is the selected one and the
pair is a collinearity diagnostic. Cross-sectional z on the monthly refresh
grid, winsorized at +/-3, hysteresis entry_z/exit_z, long top-k (highest
delay) / short bottom-k (lowest delay), gross-normalized, forward-filled to the
daily calendar.  Grid (bounded, 16): feature {delay_126, delay_252} x entry_z
{0.5, 1.0} x exit_z {0.0} x k {5, 10} x vol_target {0.10, 0.15}; train-only
4-fold walk-forward Sharpe selection. Costs: 5 bps one-way per leg traded; no
borrow cost for shorts is modelled -- disclosed as an optimistic assumption for
a long/short equity book (identical to H187/H191/H192/H193/H194).

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from
H187/H190/H191/H192/H193/H194): Sharpe >= 1.0; trades >= 50; PF >= 1.3; maxDD
<= 15%; WF stability >= 0.7; worst-regime rolling-252 Sharpe >= 0.3; benchmark
p <= 0.05 (two-sided) with IR >= 0 vs the passive equal-weight long book of the
same universe; OAT +/-20% perturbation min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same active
leg count, seed 42); inverse signal (anti-delay, i.e. long low-delay /
short high-delay); train-block Spearman of ``delay_126`` vs ``delay_252`` as an
input-collinearity diagnostic; cross-sectional Spearman of delay vs beta (H193),
trailing 252-day return (momentum) and trailing 252-day volatility as
mechanism-separation diagnostics.

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors and cross-sectional/hysteresis primitives from
run_nf_20261120_01_equity_accruals.py (H187), which in turn imports
run_nf_20261119_02_commodity_hedging_pressure.py (H186) and
run_nf_20261114_01_commodity_termstructure_carry.py (H184). Only the trailing
price-delay panel construction and the (long-high-delay) signal weights are new
code. Free/public real data only (yfinance daily auto-adjusted Close);
``src/qtr`` unchanged. Artifact under
.experiments/nf_runs/nf_20261121_05_price_delay_<timestamp>/summary.json +
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

# Reuse the H187 equity runner (which exposes h184 / h186 and the shared helpers).
_H187_PATH = ROOT / "run_nf_20261120_01_equity_accruals.py"
_h187_spec = importlib.util.spec_from_file_location("h187_accruals", _H187_PATH)
assert _h187_spec is not None and _h187_spec.loader is not None
h187 = importlib.util.module_from_spec(_h187_spec)  # type: ignore[arg-type]
sys.modules[_h187_spec.name] = h187
_h187_spec.loader.exec_module(h187)

# h187 already imported h184 internally; expose it for direct use.
h184 = h187.h184

EXPERIMENT = "nf_20261121_05_price_delay"
NF_ID = "NF-20261121-05"
HYPOTHESIS = "H195"

START = "2011-01-03"
END = "2026-11-21"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

# Universe: the probe's 100-name S&P 100 snapshot minus XOM and BKNG (same as H187/H193/H194).
UNIVERSE_SYMBOLS = [
    symbol
    for symbol in (
        "AAPL ABBV ABT ACN ADBE AMAT AMD AMGN AMT AMZN ANET AVGO AXP BA BAC BKNG "
        "BLK BMY BNY C CAT CMCSA COF COP COST CRM CSCO CVS CVX DE DELL DHR DIS "
        "DUK EMR FDX GD GE GEV GILD GM GOOG GOOGL GS HD IBM INTC INTU ISRG JNJ "
        "JPM KO LIN LLY LMT LOW LRCX MA MCD MDLZ MDT META MMM MO MRK MS MSFT MU "
        "NEE NFLX NOW NVDA ORCL PANW PEP PFE PG PLTR PM QCOM RTX SBUX SCHW SNDK "
        "SO T TMO TMUS TSLA TXN UBER UNH UNP UPS USB V VZ WFC WMT XOM"
    ).split()
    if symbol not in ("XOM", "BKNG")
]
assert len(UNIVERSE_SYMBOLS) == 98

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 40
MIN_PRICE_OBSERVATIONS = 252  # minimum valid daily returns for a name to be tradeable
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252

GATES = dict(h184.GATES)

DELAY_WINDOWS = [126, 252]
DELAY_LAGS = 5  # Hou & Moskowitz (2005) use four/five lagged market returns
FEATURES = [f"delay_{window}" for window in DELAY_WINDOWS]
GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [5, 10],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "xbrl"


# ---------------------------------------------------------------------------
# Data acquisition: load cached equity closes and build monthly delay panels
# ---------------------------------------------------------------------------


def load_or_fetch_closes(products: list[str]) -> pd.DataFrame:
    """Load cached equity closes, fetching from yfinance if absent."""
    cache_dir = Path(".cache") / "xbrl"
    cache_dir.mkdir(parents=True, exist_ok=True)
    price_path = cache_dir / "equity_closes.csv"
    if price_path.exists():
        closes = pd.read_csv(price_path, index_col=0, parse_dates=True)
        if set(products).issubset(set(closes.columns)):
            return closes.reindex(columns=list(products))
    import yfinance as yf

    raw = yf.download(list(products), start=START, end=END, auto_adjust=True, progress=False)[
        "Close"
    ]
    raw = raw.reindex(columns=list(products))
    raw.to_csv(price_path)
    return raw


def returns_from_closes(closes: pd.DataFrame) -> pd.DataFrame:
    """Daily simple returns, non-finite -> NaN (first row is all-NaN by design)."""
    returns = closes.pct_change(fill_method=None)
    return returns.replace([np.inf, -np.inf], np.nan)


def _refresh_dates(calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First business day of each month in ``calendar`` (monthly refresh grid)."""
    series = calendar.to_series()
    return pd.DatetimeIndex(series.groupby(series.dt.to_period("M")).first().values)


def trailing_delay(
    returns: pd.DataFrame,
    window: int,
    n_lags: int = DELAY_LAGS,
    min_valid: int | None = None,
) -> pd.DataFrame:
    """Causal trailing Hou-Moskowitz (2005) price delay per name.

    For each stock, over the trailing ``window`` daily observations, we run

        r_i,t = a + b0 * r_mkt,t + b1 * r_mkt,t-1 + ... + b_n * r_mkt,t-n + e

    (unrestricted) and the restricted regression on the contemporaneous market
    return only, then define delay as

        delay_i = 1 - R2_restricted / R2_unrestricted

    clipped to [0, 1]. A high delay means the stock's price responds only
    sluggishly to market-wide information (slow diffusion / limited attention).

    Each stock is estimated on its **own** valid rows within the trailing
    window. A stock with a short history (e.g. a recent IPO) is estimated only
    once it has at least ``min_valid`` non-NaN observations in the window
    (default ``max(n_lags + 5, window // 2)``). Earlier this required *every*
    name to have a complete window on a given day, so a single missing name
    (many S&P 100 constituents IPO'd after 2011) discarded the entire day and
    left ~95% of the panel NaN -- a vacuous flat strategy that produced zero
    positions and zero in-sample Sharpe. Estimating per name over its available
    rows lifts coverage to ~90% of cells on the real panel while preserving the
    Hou-Moskowitz delay definition.

    The market proxy is the equal-weight mean of the tradable universe's
    contemporaneous returns (broad-market proxy; 1/N own-inclusion weight,
    disclosed). Delay at day t uses returns and lagged market returns through t
    only; the engine then applies ``shift(1)``, so the signal is strictly
    causal.

    The shared market design matrix ``[1, m_t, m_{t-1}, ..., m_{t-n_lags}]``
    must be NaN-free across the window (it is, after the first ``n_lags`` rows),
    which preserves the warm-up: complete names are NaN until row
    ``window - 1 + n_lags``. Names with a complete, finite window are solved in
    one vectorized normal-equations step; names with gaps (but ``>= min_valid``
    valid rows) fall back to a per-stock least-squares solve.
    """
    market = returns.mean(axis=1)
    n = len(returns)
    columns = list(returns.columns)
    n_names = len(columns)
    if min_valid is None:
        min_valid = max(n_lags + 5, window // 2)

    # Shared lagged-market design: [1, m_t, m_{t-1}, ..., m_{t-n_lags}].
    lag_columns = [market.shift(k).to_numpy() for k in range(n_lags + 1)]
    design_full = np.column_stack([np.ones(n)] + lag_columns)  # (n, n_lags + 2)
    data = returns.to_numpy(dtype=float)

    delay = np.full((n, n_names), np.nan)
    for t in range(window - 1, n):
        design_window = design_full[t - window + 1 : t + 1]
        if np.isnan(design_window).any():
            continue
        returns_window = data[t - window + 1 : t + 1]
        valid = ~np.isnan(returns_window)
        counts = valid.sum(axis=0)

        # Fast path: names with a complete, finite window (one shared solve).
        complete = valid.all(axis=0) & (counts >= min_valid)
        solved_complete = np.zeros(n_names, dtype=bool)
        if complete.any():
            r_complete = returns_window[:, complete]
            xtx = design_window.T @ design_window
            design_restricted = design_window[:, :2]
            try:
                beta_full = np.linalg.solve(xtx, design_window.T @ r_complete)
                beta_restricted = np.linalg.solve(
                    design_restricted.T @ design_restricted,
                    design_restricted.T @ r_complete,
                )
            except np.linalg.LinAlgError:
                beta_full = None
            if beta_full is not None:
                resid_full = r_complete - design_window @ beta_full
                ss_full = (resid_full**2).sum(axis=0)
                resid_restricted = r_complete - design_restricted @ beta_restricted
                ss_restricted = (resid_restricted**2).sum(axis=0)
                total = ((r_complete - r_complete.mean(axis=0)) ** 2).sum(axis=0)
                with np.errstate(divide="ignore", invalid="ignore"):
                    r2_full = 1.0 - ss_full / total
                    r2_restricted = 1.0 - ss_restricted / total
                    delay_value = 1.0 - r2_restricted / r2_full
                delay_value = np.where(
                    (total > 0.0) & (r2_full > 0.0) & np.isfinite(delay_value),
                    delay_value,
                    np.nan,
                )
                delay_value = np.clip(delay_value, 0.0, 1.0)
                delay[t, complete] = delay_value
                solved_complete = complete.copy()

        # Fallback path: names with gaps but enough valid rows, plus any complete
        # name the shared solve could not handle.
        needs_solve = (~solved_complete) & (counts >= min_valid)
        for j in np.nonzero(needs_solve)[0]:
            column = returns_window[:, j]
            mask = ~np.isnan(column)
            xv = design_window[mask]
            yv = column[mask]
            try:
                beta_full, *_ = np.linalg.lstsq(xv, yv, rcond=None)
                resid_full = yv - xv @ beta_full
                ss_full = float(resid_full @ resid_full)
                beta_restricted, *_ = np.linalg.lstsq(xv[:, :2], yv, rcond=None)
                resid_restricted = yv - xv[:, :2] @ beta_restricted
                ss_restricted = float(resid_restricted @ resid_restricted)
            except np.linalg.LinAlgError:
                continue
            total = float(((yv - yv.mean()) ** 2).sum())
            if total <= 0.0:
                continue
            r2_full = 1.0 - ss_full / total
            r2_restricted = 1.0 - ss_restricted / total
            if r2_full > 0.0:
                delay_value = 1.0 - r2_restricted / r2_full
                if np.isfinite(delay_value):
                    delay[t, j] = float(np.clip(delay_value, 0.0, 1.0))

    return pd.DataFrame(delay, index=returns.index, columns=columns)


def build_delay_panels(
    returns: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    products: list[str],
) -> dict[str, pd.DataFrame]:
    """Construct monthly-refreshed delay panels for each window.

    Delay is slow-moving, so it is sampled on each month's first business day
    and forward-filled to the daily calendar; turnover therefore happens at
    most monthly. The panel is indexed by the daily calendar with one column
    per symbol.
    """
    refresh = _refresh_dates(calendar)
    panels: dict[str, pd.DataFrame] = {}
    for window in DELAY_WINDOWS:
        delay = trailing_delay(returns, window).reindex(columns=products)
        # ``reindex(refresh)`` selects the refresh rows; reindexing to the full
        # calendar and forward-filling gives the daily-aligned monthly panel.
        sampled = delay.reindex(refresh)
        daily = sampled.reindex(calendar).ffill()
        panels[f"delay_{window}"] = daily.reindex(columns=products)
    return panels


# ---------------------------------------------------------------------------
# Signal, sizing and backtest (reuse h184 / h187 primitives)
# ---------------------------------------------------------------------------


def cross_sectional_z(signal: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score with winsorization at +/-3 (h187 contract)."""
    return h187.cross_sectional_z(signal)


def delay_signal_weights(
    z: pd.DataFrame,
    entry_z: float,
    exit_z: float,
    k: int,
    products: list[str] | None = None,
) -> pd.DataFrame:
    """Hysteresis cross-sectional rank: long top-k (high delay) / short bottom-k.

    Hou & Moskowitz (2005) delay direction: stocks with high delay (slow
    response to market-wide news) subsequently earn higher returns. So we
    **long the highest delay (most positive z)** and **short the lowest delay
    (most negative z)**. Since the z-score convention has high = positive, the
    *highest* z is the long leg (the mirror image of H187/H193/H194 long-low).
    """
    calendar = z.index
    products = list(products if products is not None else z.columns)
    state = {product: 0 for product in products}
    weights = pd.DataFrame(0.0, index=calendar, columns=products, dtype=float)
    for day in calendar:
        zi = z.loc[day]
        new = dict(state)
        long_candidates: list[tuple[str, float]] = []
        short_candidates: list[tuple[str, float]] = []
        for product in products:
            if not pd.notna(zi[product]):
                new[product] = 0
                continue
            value = float(zi[product])
            # Exit conditions (long-high: exit when z falls to/below exit_z;
            # short-low: exit when z rises to/above -exit_z).
            if state[product] == 1 and value <= exit_z:
                new[product] = 0
            elif state[product] == -1 and value >= -exit_z:
                new[product] = 0
            elif state[product] == 0:
                if value >= entry_z:
                    long_candidates.append((product, value))
                elif value <= -entry_z:
                    short_candidates.append((product, value))
        held_longs = [product for product in products if new[product] == 1]
        held_shorts = [product for product in products if new[product] == -1]
        # Add new longs (highest delay first)
        for product, _ in sorted(long_candidates, key=lambda item: item[1], reverse=True):
            if len(held_longs) >= k:
                break
            new[product] = 1
            held_longs.append(product)
        # Add new shorts (lowest delay first)
        for product, _ in sorted(short_candidates, key=lambda item: item[1]):
            if len(held_shorts) >= k:
                break
            if product in held_longs:
                continue
            new[product] = -1
            held_shorts.append(product)
        state = new
        open_legs = [product for product in products if state[product] != 0]
        if open_legs:
            scale = 1.0 / len(open_legs)
            for product in open_legs:
                weights.loc[day, product] = state[product] * scale
    return weights


def target_weights(
    feature_daily: pd.DataFrame,
    params: dict,
    returns: pd.DataFrame,
    products: list[str],
) -> pd.DataFrame:
    """Cross-sectional z + hysteresis on daily delay features, vol-target scaled."""
    z = cross_sectional_z(feature_daily)
    active_counts = z.notna().sum(axis=1)
    weights = delay_signal_weights(
        z, params["entry_z"], params["exit_z"], int(params["k"]), products
    )
    weights = weights.where(active_counts >= MIN_ACTIVE_NAMES, 0.0)
    raw_port = (weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    scale = h184.vol_scale(raw_port, float(params["vol_target"]))
    return weights.mul(scale, axis=0)


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
    weights = target_weights(
        feature_daily.reindex(train_index), params, returns.reindex(train_index), products
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
            h187.zero_rolls(block, products),
        )
        sharpes.append(h184.annualized_sharpe(result["returns"]))
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
        weights = target_weights(
            feature_daily.reindex(oos_index), variant, returns.reindex(oos_index), products
        )
        result = h184.backtest_metrics(
            weights.fillna(0.0),
            returns.reindex(oos_index).fillna(0.0),
            h187.zero_rolls(oos_index, products),
        )
        sharpes.append(h184.annualized_sharpe(result["returns"]))
    return sharpes


def train_collinearity(features: dict[str, pd.DataFrame], train_index: pd.DatetimeIndex) -> float:
    """Input-only diagnostic: cross-sectional Spearman of delay_126 vs delay_252."""
    left, right = features["delay_126"], features["delay_252"]
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
    delay_features: dict[str, pd.DataFrame],
    beta_features: dict[str, pd.DataFrame] | None,
    returns: pd.DataFrame,
    train_index: pd.DatetimeIndex,
) -> dict[str, float]:
    """Cross-sectional Spearman of delay vs beta (H193), momentum and vol."""
    diagnostics: dict[str, float] = {}
    delay = delay_features["delay_252"]
    # Momentum / volatility are computed from ``returns`` (indexed by the actual
    # yfinance trading days); align them to the delay panel's daily calendar
    # index so the exact-label Spearman lookup does not fail on market holidays
    # that the synthetic ``pd.bdate_range`` calendar includes but ``returns``
    # does not.
    calendar_index = delay.index

    if beta_features is not None:
        beta = beta_features.get("beta_252")
        if beta is not None:
            value = _mean_cross_sectional_spearman(delay, beta, train_index)
            if value is not None:
                diagnostics["delay_252_vs_beta_252"] = value

    momentum = trailing_total_return(returns, 252).reindex(calendar_index)
    value = _mean_cross_sectional_spearman(delay, momentum, train_index)
    if value is not None:
        diagnostics["delay_252_vs_momentum_252"] = value

    volatility = trailing_volatility(returns, 252).reindex(calendar_index)
    value = _mean_cross_sectional_spearman(delay, volatility, train_index)
    if value is not None:
        diagnostics["delay_252_vs_realized_vol_252"] = value

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

    closes = load_or_fetch_closes(products)
    returns = returns_from_closes(closes)

    # Restrict to names with >= MIN_PRICE_OBSERVATIONS valid daily returns.
    valid_counts = returns.notna().sum()
    tradable = [
        symbol for symbol in products if int(valid_counts.get(symbol, 0)) >= MIN_PRICE_OBSERVATIONS
    ]
    if len(tradable) < MIN_ACTIVE_NAMES:
        raise RuntimeError(
            f"tradable delay universe {len(tradable)} < MIN_ACTIVE_NAMES {MIN_ACTIVE_NAMES}"
        )
    products = tradable
    returns = returns.reindex(columns=products)

    if download_only:
        coverage = {
            "symbols_with_enough_history": int(len(tradable)),
            "total_symbols_requested": len(UNIVERSE_SYMBOLS),
            "min_valid_returns": int(valid_counts.reindex(products).min()),
        }
        print(json.dumps(coverage, indent=2))
        return coverage

    features_daily = build_delay_panels(returns, calendar, products)
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

    # Compute collinearity and mechanism separation diagnostics
    collinearity = train_collinearity(features_daily, train_index)

    # For beta separation, reuse H193's beta panels (input-only diagnostic).
    from run_nf_20261121_03_bab_beta import build_beta_panels as build_beta_panels_h193

    beta_features = build_beta_panels_h193(returns, calendar, products)
    separation = train_mechanism_separation(features_daily, beta_features, returns, train_index)

    data_meta = {
        "equity_source": "yfinance auto-adjusted Close (free/public)",
        "delay_source": (
            "trailing Hou-Moskowitz (2005) delay: 1 - R2_restricted/R2_unrestricted "
            "from daily returns vs contemporaneous+lagged market returns (causal)"
        ),
        "market_proxy": "equal-weight mean of tradable universe contemporaneous returns",
        "delay_windows": DELAY_WINDOWS,
        "delay_lags": DELAY_LAGS,
        "universe_symbols": products,
        "universe_size": len(products),
        "excluded_symbols": ["XOM", "BKNG"],
        "symbols_with_enough_history": int(len(tradable)),
        "min_price_observations": MIN_PRICE_OBSERVATIONS,
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
        "train_input_collinearity_delay126_vs_delay252": collinearity,
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
            "pit_rule": "trailing price delay through t only, engine shift(1), monthly refresh",
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
        help="report price-history coverage and exit (no backtest)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only)
