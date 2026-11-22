"""NF-20261122-02 / H197 (Cycle 253 pre-registration and execution).

Broad mechanism category: capital structure / financial distress (stock-level
balance-sheet leverage and default distance). Repo-new root family relative to
executed H1-H196: no executed H-ID sorts single stocks by a *leverage /
default-distance* (capital-structure) characteristic into a cross-section. The
closest prior families are H187 (accruals / asset growth -- earnings quality),
H188 (net share issuance -- external financing), H189 (gross profitability --
data-blocked), H191 (valuation -- book-to-price / cash-flow yield), H192
(innovation intensity), H193 (beta / betting-against-beta), H194 (coskewness),
H195 (price delay) and H196 (share turnover / liquidity). A capital-structure
sort ranks on **how levered a firm is and how far its asset value sits above
its default barrier** -- a solvency / bankruptcy-risk characteristic -- which is
none of a past return, an accounting-quality accrual, an external-financing flow,
a valuation price-ratio, an innovation input, a systematic-risk beta, a higher
moment, a response-speed friction, or a trading-activity liquidity proxy. The
tradeable hypothesis is the **distress / leverage cross-section**, a distinct
return-generating mechanism (Campbell, Hilscher & Szilagyi 2008; Merton 1974
distance-to-default; Fama & French 1993 distress), not a parameter / universe /
market variant of any prior family.

Mechanism / causal chain.  Two well-documented, directionally-consistent
channels connect capital structure to subsequent equity returns. (i) Distress
risk (Campbell-Hilscher-Szilagyi 2008; Merton 1974): a firm whose asset value
sits close to its default barrier (low distance-to-default) carries high
bankruptcy risk; in the post-1980 U.S. cross-section such high-distress firms
subsequently *under*perform, so low-distress (high-DD, low-leverage) names earn
higher returns -- the "distress factor" is negative. (ii) Leverage / distress
premium: highly levered equities have more volatile, more option-like payoffs
that lose value after issuance / de-leveraging episodes, again predicting that
conservatively financed (low-leverage, high-equity-to-debt) names subsequently
outperform. Both channels predict the same sign: **long the safest names (lowest
leverage / highest distance-to-default), short the most distressed (highest
leverage / lowest distance-to-default).** Null (H0): the capital-structure
cross-section carries no predictive power for next-period equity returns after
costs -- a solvency tilt adds nothing over a passive equal-weight long book of
the same universe.

Mechanism separation.  H191 value scales a fundamental by PRICE (book equity /
market cap); H197 scales a *liability* by equity and a log-returns gap by
volatility (leverage / default distance) -- a solvency characteristic, not a
cheapness ratio. H187 accruals and H188 issuance are earnings-quality / financing
flows; H197 is a *balance-sheet stock* of obligations. H193 beta, H194 coskewness
and H196 turnover are traded-security characteristics; H197 is a firm-fundamental
solvency characteristic. The run reports train-block cross-sectional Spearman of
``equity_to_debt`` vs ``distance_to_default`` (input collinearity) and of the
traded distress signal vs H193 beta and vs trailing 252-day momentum / volatility
(mechanism-separation diagnostics).

PIT / causality.  A fundamental row may enter the signal only when ``filed`` (the
SEC acceptance date of the accession that supplied the LAST tag needed for that
fiscal year) is ``<= t``; the shared engine then applies ``shift(1)``, so a
position formed at close t earns t -> t+1 -- strictly causal. No fiscal-period
``end`` is ever used as an availability stamp. At a monthly refresh date R,
market equity = (latest filed shares on/before R) * (close on R); book
liabilities = latest filed 10-K ``Liabilities`` on/before R; trailing equity
volatility = annualised standard deviation of the prior 252 daily returns known
at R. The panel refreshes on the first business day of each month and is
forward-filled to the daily calendar (leverage / DD update at most monthly).

Pre-registration (Cycle 253, written before any forward-return outcome was
computed).  Sample 2011-01-03 -> 2026-11-21; Train -> 2021-12-31; Val
2022-01-01 -> 2023-12-31; Test protected 2024-01-01 -> 2026-11-21.  Universe:
the 100-name S&P 100 snapshot in
``scripts/probe_sec_xbrl_fundamentals.py:UNIVERSE`` minus XOM and BKNG (same
measured exclusions as H187/H188/H191/H192/H193/H194/H195/H196) = 98 names; only
names with >= 2 annual ``Liabilities``+share observations AND >= 252 valid daily
returns are tradeable (measured below, well above the 40-name minimum).  Features
(both oriented "high = safest", long-high / short-low): ``equity_to_debt`` =
market equity / book liabilities and ``distance_to_default`` = (ln(E/F) - 0.5 *
sigma^2) / sigma, sigma = trailing-252 annualised equity volatility, E/F =
market equity / book liabilities -- the classic simplified Merton default
distance with a one-year horizon and zero risk-free drift.  Cross-sectional z on
the monthly refresh grid, winsorized at +/-3, hysteresis entry_z/exit_z, long
top-k (highest z = safest) / short bottom-k (lowest z = most distressed),
gross-normalized, forward-filled to the daily calendar.  Grid (bounded, 16):
feature {equity_to_debt, distance_to_default} x entry_z {0.5, 1.0} x exit_z
{0.0} x k {5, 10} x vol_target {0.10, 0.15}; train-only 4-fold walk-forward
Sharpe selection.  Costs: 5 bps one-way per leg traded; no borrow cost for shorts
is modelled -- disclosed as an optimistic assumption for a long/short equity book
(identical to H187/H191/H192/H193/H194/H195/H196).

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from
H187/H190/H191/H192/H193/H194/H195/H196): Sharpe >= 1.0; trades >= 50; PF >= 1.3;
maxDD <= 15%; WF stability >= 0.7; worst-regime rolling-252 Sharpe >= 0.3;
benchmark p <= 0.05 (two-sided) with IR >= 0 vs the passive equal-weight long
book of the same universe; OAT +/-20% perturbation min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same active
leg count, seed 42); inverse signal (anti-distress, i.e. long most-distressed /
short safest); train-block Spearman of ``equity_to_debt`` vs
``distance_to_default`` as an input-collinearity diagnostic; cross-sectional
Spearman of the traded distress signal vs beta (H193), trailing 252-day return
(momentum) and trailing 252-day volatility as mechanism-separation diagnostics.

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors, share-count loader and cross-sectional/hysteresis
primitives from run_nf_20261121_01_equity_value.py (H191), which in turn imports
run_nf_20261120_01_equity_accruals.py (H187) and
run_nf_20261114_01_commodity_termstructure_carry.py (H184).  Only the distress
row loader and the market-leverage / default-distance panel construction are new
code.  Free/public real data only (SEC XBRL companyfacts ``Liabilities`` and
share counts + yfinance daily auto-adjusted Close); ``src/qtr`` unchanged.
Artifact under
.experiments/nf_runs/nf_20261122_02_financial_distress_<timestamp>/summary.json +
grid.csv + data_meta.json.
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

# Reuse the H191 equity-value runner (which exposes h187 / h184 / the XBRL probe,
# the share-count loader, the cross-sectional / hysteresis primitives and the
# long-high value weights). Only the distress panel is new code.
_H191_PATH = ROOT / "run_nf_20261121_01_equity_value.py"
_h191_spec = importlib.util.spec_from_file_location("h191_value", _H191_PATH)
assert _h191_spec is not None and _h191_spec.loader is not None
h191 = importlib.util.module_from_spec(_h191_spec)  # type: ignore[arg-type]
sys.modules[_h191_spec.name] = h191
_h191_spec.loader.exec_module(h191)

h187 = h191.h187
h184 = h191.h184
xbrl = h191.xbrl

EXPERIMENT = "nf_20261122_02_financial_distress"
NF_ID = "NF-20261122-02"
HYPOTHESIS = "H197"

START = "2011-01-03"
END = "2026-11-21"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

# Universe: the probe's 100-name S&P 100 snapshot minus XOM and BKNG (same as
# H187/H188/H191/H192/H193/H194/H195/H196).
UNIVERSE_SYMBOLS = [s for s in xbrl.UNIVERSE if s not in ("XOM", "BKNG")]
assert len(UNIVERSE_SYMBOLS) == 98

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 40
MIN_SHARE_OBSERVATIONS = 2
MIN_LIAB_OBSERVATIONS = 2
MIN_PRICE_OBSERVATIONS = 252
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252
DISTRESS_VOL_WINDOW = 252

GATES = dict(h184.GATES)

FEATURES = ["equity_to_debt", "distance_to_default"]
GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [5, 10],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "xbrl"

# Share-count tag priority (same as H191/H196): (namespace, tag).
SHARE_TAGS = h191.SHARE_TAGS

# Book-liability tags, in priority order.  ``Liabilities`` is the balance-sheet
# total-liabilities instant (reported by 74/100 bundles); the fallback captures
# firms that only tag liabilities-and-equity.
LIABILITY_TAGS = (
    "Liabilities",
    "LiabilitiesAndStockholdersEquity",
)


# ---------------------------------------------------------------------------
# Data acquisition: load cached share counts and book liabilities, build monthly
# distress panels.
# ---------------------------------------------------------------------------


def distress_observations(facts: dict) -> pd.DataFrame:
    """Point-in-time annual capital-structure rows for one company.

    One row per fiscal-year end that has both a filed 10-K ``Liabilities`` value
    and a filed share count.  ``filed`` is the latest of the two contributing
    SEC acceptance dates -- the first date the full row is public.  Share counts
    use the same (namespace, tag) priority and per-``end`` filed-dedup as H191.
    """
    columns = ["end", "filed", "liabilities", "shares"]

    liabilities = pd.DataFrame()
    for tag in LIABILITY_TAGS:
        candidate = h191._instant_usd(facts, tag)
        if len(candidate):
            liabilities = candidate
            break
    if liabilities.empty:
        return pd.DataFrame(columns=columns)

    shares = pd.DataFrame()
    for namespace, tag in SHARE_TAGS:
        candidate = h191._share_rows(facts, namespace, tag)
        candidate = (
            candidate.dropna(subset=["end", "filed", "val"]) if len(candidate) else candidate
        )
        if len(candidate):
            shares = candidate.sort_values("filed").drop_duplicates("end", keep="first")
            break
    if shares.empty:
        return pd.DataFrame(columns=columns)

    li = liabilities[["end", "val", "filed"]].rename(
        columns={"val": "liabilities", "filed": "liab_filed"}
    )
    sh = shares[["end", "val", "filed"]].rename(columns={"val": "shares", "filed": "sh_filed"})
    base = li.merge(sh, on="end", how="inner")
    if base.empty:
        return pd.DataFrame(columns=columns)
    base["filed"] = base[["liab_filed", "sh_filed"]].max(axis=1)
    base = base.sort_values("end").reset_index(drop=True)
    return base[columns]


def load_all_observations(
    symbols: list[str],
    cache_dir: Path = CACHE_DIR,
) -> dict[str, pd.DataFrame]:
    """Load per-symbol capital-structure observations from cached companyfacts.

    Fetches on demand (the cache is git-ignored and empty on a fresh clone) and
    skips symbols whose companyfacts cannot be retrieved or lack both a liability
    and a share tag.  Keeps only symbols with at least
    ``MIN_LIAB_OBSERVATIONS`` annual rows.
    """
    mapping = xbrl.load_ticker_cik_map(Path(cache_dir) / "company_tickers.json", fetch=False)
    observations: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        cik = mapping.get(symbol.upper())
        if cik is None:
            continue
        try:
            facts = xbrl.cached_companyfacts(cik, cache_dir, fetch=False)
        except FileNotFoundError:
            continue
        obs = distress_observations(facts)
        if len(obs) >= MIN_LIAB_OBSERVATIONS:
            observations[symbol] = obs
    return observations


def returns_from_closes(closes: pd.DataFrame) -> pd.DataFrame:
    """Daily simple returns, non-finite -> NaN (first row is all-NaN by design)."""
    returns = closes.pct_change(fill_method=None)
    return returns.replace([np.inf, -np.inf], np.nan)


def _refresh_dates(calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First business day of each month in ``calendar`` (monthly refresh grid)."""
    series = calendar.to_series()
    return pd.DatetimeIndex(series.groupby(series.dt.to_period("M")).first().values)


def build_distress_panels(
    observations: dict[str, pd.DataFrame],
    closes: pd.DataFrame,
    returns: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> dict[str, pd.DataFrame]:
    """Construct monthly-refreshed distress panels (daily-aligned).

    At each month's first business day R, for every symbol with a capital-
    structure row filed on/before R: market equity E = (latest filed shares) *
    (close on R); book liabilities F = latest filed 10-K ``Liabilities``;
    ``equity_to_debt`` = E / F and ``distance_to_default`` = (ln(E/F) -
    0.5 * sigma^2) / sigma, sigma = trailing-252 annualised equity volatility
    (known at R).  Both features are oriented "high = safest".  The monthly
    frame is forward-filled to the daily calendar.
    """
    closes_cal = closes.reindex(calendar).ffill()
    annual_vol = returns.reindex(calendar).rolling(
        DISTRESS_VOL_WINDOW, min_periods=DISTRESS_VOL_WINDOW
    ).std(ddof=0) * math.sqrt(DAYS_PER_YEAR)

    refresh = _refresh_dates(calendar)
    close_at_refresh = closes_cal.reindex(refresh)
    vol_at_refresh = annual_vol.reindex(refresh)

    e2d_series: dict[str, pd.Series] = {}
    dd_series: dict[str, pd.Series] = {}
    for symbol, obs in observations.items():
        if obs.empty:
            continue
        obs = obs.dropna(subset=["filed", "liabilities", "shares"]).sort_values("filed")
        if obs.empty:
            continue
        e2d_values: list[float] = []
        dd_values: list[float] = []
        for rd in refresh:
            usable = obs[obs["filed"] <= rd]
            if not len(usable):
                e2d_values.append(np.nan)
                dd_values.append(np.nan)
                continue
            row = usable.iloc[-1]
            price = (
                float(close_at_refresh.at[rd, symbol])
                if symbol in close_at_refresh.columns and rd in close_at_refresh.index
                else np.nan
            )
            shares = float(row["shares"])
            liabilities = float(row["liabilities"])
            if not (
                np.isfinite(price)
                and price > 0.0
                and np.isfinite(shares)
                and shares > 0.0
                and np.isfinite(liabilities)
                and liabilities > 0.0
            ):
                e2d_values.append(np.nan)
                dd_values.append(np.nan)
                continue
            market_equity = shares * price
            ratio = market_equity / liabilities
            e2d_values.append(ratio)
            sigma = (
                float(vol_at_refresh.at[rd, symbol])
                if symbol in vol_at_refresh.columns and rd in vol_at_refresh.index
                else np.nan
            )
            if np.isfinite(sigma) and sigma > 0.0:
                dd_values.append((math.log(ratio) - 0.5 * sigma * sigma) / sigma)
            else:
                dd_values.append(np.nan)
        e2d_series[symbol] = pd.Series(e2d_values, index=refresh)
        dd_series[symbol] = pd.Series(dd_values, index=refresh)

    def to_daily(frame: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(index=calendar, columns=symbols, dtype=float)
        return frame.reindex(calendar).ffill().reindex(columns=symbols)

    panel_symbols = list(observations.keys())
    return {
        "equity_to_debt": to_daily(pd.DataFrame(e2d_series), panel_symbols),
        "distance_to_default": to_daily(pd.DataFrame(dd_series), panel_symbols),
    }


# ---------------------------------------------------------------------------
# Signal, sizing and backtest (reuse h191 / h184 primitives; long-high = safest)
# ---------------------------------------------------------------------------


def target_weights(
    feature_daily: pd.DataFrame,
    params: dict,
    returns: pd.DataFrame,
    products: list[str],
) -> pd.DataFrame:
    """Cross-sectional z + long-high hysteresis on daily distress, vol-target scaled.

    Distress direction is long the *safest* names (highest z: lowest leverage /
    highest distance-to-default) and short the *most distressed* (lowest z),
    which is exactly h191's long-high value convention (``value_signal_weights``:
    long where z >= entry_z, short where z <= -entry_z).  The z-score is
    winsorized at +/-3 (h187 contract).
    """
    return h191.target_weights(feature_daily, params, returns, products)


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
    """Input-only diagnostic: cross-sectional Spearman of e2d vs distance-to-default."""
    left, right = features["equity_to_debt"], features["distance_to_default"]
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
    distress_features: dict[str, pd.DataFrame],
    beta_features: dict[str, pd.DataFrame] | None,
    returns: pd.DataFrame,
    train_index: pd.DatetimeIndex,
) -> dict[str, float]:
    """Cross-sectional Spearman of distance_to_default vs beta, momentum and vol."""
    diagnostics: dict[str, float] = {}
    distress = distress_features["distance_to_default"]
    calendar_index = distress.index

    if beta_features is not None:
        beta = beta_features.get("beta_252")
        if beta is not None:
            value = _mean_cross_sectional_spearman(distress, beta, train_index)
            if value is not None:
                diagnostics["distance_to_default_vs_beta_252"] = value

    momentum = trailing_total_return(returns, 252).reindex(calendar_index)
    value = _mean_cross_sectional_spearman(distress, momentum, train_index)
    if value is not None:
        diagnostics["distance_to_default_vs_momentum_252"] = value

    volatility = trailing_volatility(returns, 252).reindex(calendar_index)
    value = _mean_cross_sectional_spearman(distress, volatility, train_index)
    if value is not None:
        diagnostics["distance_to_default_vs_realized_vol_252"] = value

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


def load_or_fetch_closes(products: list[str]) -> pd.DataFrame:
    """Load cached equity closes, fetching from yfinance if absent."""
    cache_dir = Path(".cache") / "xbrl"
    cache_dir.mkdir(parents=True, exist_ok=True)
    price_path = cache_dir / "equity_closes.csv"
    if price_path.exists():
        closes = pd.read_csv(price_path, index_col=0, parse_dates=True)
        if set(products).issubset(set(closes.columns)):
            return closes
    import yfinance as yf

    raw = yf.download(list(products), start=START, end=END, auto_adjust=True, progress=False)[
        "Close"
    ]
    raw = raw.reindex(columns=list(products))
    raw.to_csv(price_path)
    return raw


def main(out: str | None = None, download_only: bool = False) -> dict:
    started = time.time()
    calendar = pd.bdate_range(START, END)
    products = list(UNIVERSE_SYMBOLS)

    observations = load_all_observations(products)
    if download_only:
        coverage = {
            "symbols_with_capital_structure_observations": int(len(observations)),
            "total_symbols_requested": len(UNIVERSE_SYMBOLS),
            "min_liab_observations": int(
                min((len(obs) for obs in observations.values()), default=0)
            ),
        }
        print(json.dumps(coverage, indent=2))
        return coverage

    if len(observations) < MIN_ACTIVE_NAMES:
        raise RuntimeError(
            f"capital-structure universe {len(observations)} < MIN_ACTIVE_NAMES {MIN_ACTIVE_NAMES}"
        )

    closes = load_or_fetch_closes(products)
    # Calendar-aligned, forward-filled closes so daily returns are defined on
    # every business day (holidays get a 0% return) -- the H191 convention.  A
    # raw pct_change on the unaligned yfinance grid would put NaNs on every
    # market holiday, and a 252-day rolling volatility over such a grid never
    # reaches min_periods, silently zeroing the distance-to-default panel.
    returns = returns_from_closes(closes.reindex(calendar).ffill())

    # Restrict to names with >= MIN_PRICE_OBSERVATIONS valid daily returns and
    # >= MIN_LIAB_OBSERVATIONS capital-structure observations.
    valid_counts = returns.notna().sum()
    products = [
        symbol
        for symbol in observations
        if int(valid_counts.get(symbol, 0)) >= MIN_PRICE_OBSERVATIONS
    ]
    if len(products) < MIN_ACTIVE_NAMES:
        raise RuntimeError(
            f"tradable distress universe {len(products)} < MIN_ACTIVE_NAMES {MIN_ACTIVE_NAMES}"
        )
    observations = {symbol: observations[symbol] for symbol in products}
    closes = closes.reindex(columns=products)
    returns = returns.reindex(columns=products)

    features_daily = build_distress_panels(observations, closes, returns, calendar)
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
        score = h191.walk_forward_score(
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
        for value in h191.perturbation_sharpes(
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
        "equity_source": "yfinance auto-adjusted Close (free/public)",
        "liabilities_source": "SEC XBRL companyfacts Liabilities, PIT by filed date (free/public)",
        "shares_source": "SEC XBRL companyfacts share counts, PIT by filed date (free/public)",
        "distress_definition": (
            "equity_to_debt = market equity / book liabilities; "
            "distance_to_default = (ln(E/F) - 0.5*sigma^2)/sigma, sigma = trailing-252 annualised equity vol"
        ),
        "equity_to_debt_feature": "equity_to_debt",
        "distance_to_default_feature": "distance_to_default",
        "distress_vol_window": DISTRESS_VOL_WINDOW,
        "universe_symbols": products,
        "universe_size": len(products),
        "excluded_symbols": ["XOM", "BKNG"],
        "symbols_with_capital_structure_observations": int(len(observations)),
        "min_price_observations": MIN_PRICE_OBSERVATIONS,
        "min_liab_observations": MIN_LIAB_OBSERVATIONS,
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
        "train_input_collinearity_equity_to_debt_vs_distance_to_default": collinearity,
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
            "pit_rule": "max(filed) per fiscal year, market cap at monthly-refresh close, engine shift(1)",
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
        help="report capital-structure coverage and exit (no backtest)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only)
