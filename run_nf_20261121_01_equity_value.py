"""NF-20261121-01 / H191 (Cycle 245 pre-registration and execution).

Broad mechanism category: fundamental / valuation (price-scaled book equity and
cash flow). Repo-new root family relative to executed H1-H190: no executed H-ID
trades a *valuation* (price-scaled) fundamental.  The closest prior families are
H187 (accruals / asset growth -- earnings quality and corporate investment),
H188 (net share issuance -- external financing), and H189 (gross profitability --
confirmed data-blocked on SEC XBRL, Cycle 234).  Value compares a *stock*
fundamental (book equity, operating cash flow) to its *market* price, which is a
distinct economic mechanism (a risk-based / behavioral value premium; Fama &
French 1993; Lakonishok, Shleifer & Vishny 1994) -- not a variant of accruals,
issuance, or profitability, and not a parameter/universe/market re-run of any of
them.  The accounting STOCK/quality/financing mechanisms (H187/H188/H189) scale a
fundamental by another fundamental (assets); value scales it by PRICE.  That
price denominator is the definitional difference that makes value a new family.

Mechanism / causal chain.  A high book-to-price (or cash-flow-to-price) ratio
means the market prices the firm cheaply relative to its accounting book or
cash generation.  The value premium (Fama-French HML; Lakonishok-Shleifer-Vishny
1994 extrapolation) says such firms subsequently earn higher returns than growth
firms, because (risk story) value firms are more sensitive to bad macro states
and (behavioral story) investors over-extrapolate recent growth and under-react
to fundamentals.  Prediction (directional): **long the top-k names by
cross-sectional book-to-price (and cash-flow yield), short the bottom-k.**  Null
(H0): the valuation cross-section carries no predictive power for next-period
equity returns after costs -- a value tilt adds nothing over a passive
equal-weight book of the same universe.

PIT timing.  A fundamental observation may enter the signal only when ``filed``
(the SEC acceptance date of the accession that supplied it) is ``<= t``; the
shared engine then applies ``shift(1)``, so a position formed at the close of t
earns t -> t+1.  No fiscal-period ``end`` is ever used as an availability stamp.
Market capitalisation at a monthly refresh date R uses the *close on R* (known at
R) times the latest reported share count filed on/before R; book-to-price and
cash-flow yield are then equity (resp. operating cash flow) divided by that
market cap.  The panel refreshes monthly (first business day of each month) and
is forward-filled to the daily calendar, so turnover happens at most monthly.

Pre-registration (Cycle 245, written before any forward-return outcome was
computed).  Sample 2011-01-03 -> 2026-11-17 (the first year in which the universe
has a filed 10-K valuation row; matches H187's window for lineage comparability);
Train -> 2021-12-31; Val 2022-01-01 -> 2023-12-31; Test protected 2024-01-01 ->
2026-11-17.  Universe: the 100-name S&P 100 snapshot in
``scripts/probe_sec_xbrl_fundamentals.py:UNIVERSE``, minus XOM (no 10-K history,
successor entity) and BKNG (book equity tag absent) = 98 names (measured; the same
exclusions H187/H188 used).  Features: ``book_to_price`` = StockholdersEquity /
(shares * close) and ``cash_flow_yield`` = NetCashProvidedByUsedInOperatingActivities
/ (shares * close); shares from us-gaap CommonStockSharesOutstanding, falling back
to WeightedAverageNumberOfSharesOutstandingBasic, then dei
EntityCommonStockSharesOutstanding.  Cross-sectional z on the monthly refresh
grid, winsorized at +/-3, hysteresis entry_z/exit_z, top-k long (highest z) /
bottom-k short (lowest z), gross-normalized to one, forward-filled to the daily
calendar.  Grid (bounded, 16): feature {book_to_price, cash_flow_yield} x entry_z
{0.5, 1.0} x exit_z {0.0} x k {10, 20} x vol_target {0.10, 0.15}; train-only 4-fold
walk-forward Sharpe selection.  Costs: 5 bps one-way per leg traded (commission +
spread); no borrow cost for shorts is modelled -- disclosed as an optimistic
assumption for a long/short equity book (identical to H187).

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from H187/H190): Sharpe >=
1.0; trades >= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7; worst-regime
rolling-252 Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with IR >= 0 vs the
passive equal-weight long book of the same 98 names; OAT +/-20% perturbation min
ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same active
leg count, seed 42); inverse signal (anti-value); train-block Spearman of
book_to_price vs cash_flow_yield as an input-collinearity diagnostic.

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors and cross-sectional/hysteresis primitives from
run_nf_20261120_01_equity_accruals.py (H187), which in turn imports
run_nf_20261119_02_commodity_hedging_pressure.py (H186) and
run_nf_20261114_01_commodity_termstructure_carry.py (H184); the SEC XBRL loader
helpers come from scripts/probe_sec_xbrl_fundamentals.py.  Only the valuation row
loader, the market-cap alignment and the (non-inverted) value signal weights are
new code.  Free/public real data only; ``src/qtr`` unchanged.  Artifact under
.experiments/nf_runs/nf_20261121_01_equity_value_<timestamp>/summary.json +
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

# Import the XBRL probe functions (no forked copy).
_PROBE_PATH = ROOT / "scripts" / "probe_sec_xbrl_fundamentals.py"
_probe_spec = importlib.util.spec_from_file_location("xbrl_probe", _PROBE_PATH)
assert _probe_spec is not None and _probe_spec.loader is not None
xbrl = importlib.util.module_from_spec(_probe_spec)  # type: ignore[arg-type]
sys.modules[_probe_spec.name] = xbrl
_probe_spec.loader.exec_module(xbrl)

EXPERIMENT = "nf_20261121_01_equity_value"
NF_ID = "NF-20261121-01"
HYPOTHESIS = "H191"

START = "2011-01-03"
END = "2026-11-17"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

# Universe: the probe's 100-name S&P 100 snapshot minus XOM and BKNG (same as H187).
UNIVERSE_SYMBOLS = [s for s in xbrl.UNIVERSE if s not in ("XOM", "BKNG")]
assert len(UNIVERSE_SYMBOLS) == 98

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 40
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252

GATES = dict(h184.GATES)

FEATURES = ["book_to_price", "cash_flow_yield"]
GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [10, 20],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "xbrl"

# Equity (book value) tag priority: StockholdersEquity first, then the broader
# "including noncontrolling interest" tag.
EQUITY_TAGS = (
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
)
# Share-count tag priority: (namespace, tag).  All are point-in-time share counts.
SHARE_TAGS = (
    ("us-gaap", "CommonStockSharesOutstanding"),
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
    ("dei", "EntityCommonStockSharesOutstanding"),
)


# ---------------------------------------------------------------------------
# Data acquisition: load cached companyfacts and build monthly signal panels
# ---------------------------------------------------------------------------


def load_all_observations(
    symbols: list[str],
    cache_dir: Path = CACHE_DIR,
) -> dict[str, pd.DataFrame]:
    """Load per-symbol valuation observations from cached companyfacts.

    Returns a dict symbol -> DataFrame with columns
    ['end', 'filed', 'equity', 'cfo', 'shares'] for every fiscal year that has a
    filed StockholdersEquity, operating-cash-flow and share-count observation on
    the same fiscal ``end``.
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
        obs = value_observations(facts)
        if len(obs):
            observations[symbol] = obs
    return observations


def _instant_usd(facts: dict, tag: str) -> pd.DataFrame:
    """Annual 10-K instant rows for one us-gaap USD tag (filed-deduped)."""
    frame = xbrl.tag_rows(facts, tag)
    if frame.empty:
        return frame
    frame = frame[frame["form"] == "10-K"].dropna(subset=["end", "filed", "val"])
    return frame.sort_values("filed").drop_duplicates("end", keep="first")


def _duration_usd(facts: dict, tag: str) -> pd.DataFrame:
    """Annual 10-K duration rows for one us-gaap USD tag (filed-deduped)."""
    return _instant_usd(facts, tag)


def _share_rows(facts: dict, namespace: str, tag: str) -> pd.DataFrame:
    """Annual-ish share-count rows for one (namespace, tag), any share unit."""
    units = facts.get("facts", {}).get(namespace, {}).get(tag, {}).get("units", {})
    rows = None
    for unit_key in ("shares", "pure"):
        if unit_key in units:
            rows = units[unit_key]
            break
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    for column in ("end", "filed"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    if "val" in frame.columns:
        frame["val"] = pd.to_numeric(frame["val"], errors="coerce")
    return frame


def value_observations(facts: dict) -> pd.DataFrame:
    """Point-in-time annual valuation rows for one company.

    One row per fiscal-year end that has StockholdersEquity, operating cash flow
    and a share count reported on the same ``end``.  ``filed`` is the latest of
    the three contributing acceptance dates -- the first date the full row is
    public.
    """
    columns = ["end", "filed", "equity", "cfo", "shares"]

    equity = pd.DataFrame()
    for tag in EQUITY_TAGS:
        equity = _instant_usd(facts, tag)
        if len(equity):
            break
    cfo = _duration_usd(facts, "NetCashProvidedByUsedInOperatingActivities")
    if equity.empty or cfo.empty:
        return pd.DataFrame(columns=columns)

    shares = pd.DataFrame()
    for namespace, tag in SHARE_TAGS:
        candidate = _share_rows(facts, namespace, tag)
        candidate = (
            candidate.dropna(subset=["end", "filed", "val"]) if len(candidate) else candidate
        )
        if len(candidate):
            shares = candidate.sort_values("filed").drop_duplicates("end", keep="first")
            break
    if shares.empty:
        return pd.DataFrame(columns=columns)

    eq = equity[["end", "val", "filed"]].rename(columns={"val": "equity", "filed": "eq_filed"})
    cf = cfo[["end", "val", "filed"]].rename(columns={"val": "cfo", "filed": "cfo_filed"})
    sh = shares[["end", "val", "filed"]].rename(columns={"val": "shares", "filed": "sh_filed"})
    base = eq.merge(cf, on="end", how="inner").merge(sh, on="end", how="inner")
    if base.empty:
        return pd.DataFrame(columns=columns)
    base["filed"] = base[["eq_filed", "cfo_filed", "sh_filed"]].max(axis=1)
    base = base.sort_values("end").reset_index(drop=True)
    return base[columns]


def build_value_panel(
    observations: dict[str, pd.DataFrame],
    closes: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> dict[str, pd.DataFrame]:
    """Construct monthly book-to-price and cash-flow-yield panels (daily-aligned).

    On each month's first business day R, for every symbol with a valuation row
    filed on/before R, market cap = (latest filed shares) * (close on R) and the
    feature = equity (resp. operating cash flow) / market cap.  The monthly frame
    is forward-filled to the daily calendar.
    """
    closes_cal = closes.reindex(calendar).ffill().reindex(columns=UNIVERSE_SYMBOLS)

    month_starts = calendar.to_series().groupby(calendar.to_series().dt.to_period("M")).first()
    refresh_dates = pd.DatetimeIndex(month_starts.values)
    close_at_refresh = closes_cal.reindex(refresh_dates)

    bp_series: dict[str, pd.Series] = {}
    cfy_series: dict[str, pd.Series] = {}
    for symbol, obs in observations.items():
        if obs.empty:
            continue
        obs = obs.dropna(subset=["filed", "equity", "shares"]).sort_values("filed")
        if obs.empty:
            continue
        bp_values: list[float] = []
        cfy_values: list[float] = []
        for rd in refresh_dates:
            usable = obs[obs["filed"] <= rd]
            if not len(usable):
                bp_values.append(np.nan)
                cfy_values.append(np.nan)
                continue
            row = usable.iloc[-1]
            price = (
                float(close_at_refresh.at[rd, symbol]) if rd in close_at_refresh.index else np.nan
            )
            shares = float(row["shares"])
            if np.isfinite(price) and price > 0.0 and np.isfinite(shares) and shares > 0.0:
                market_cap = shares * price
                equity = float(row["equity"])
                bp_values.append(equity / market_cap if market_cap > 0.0 else np.nan)
                cfo = row.get("cfo", np.nan)
                cfy_values.append(
                    float(cfo) / market_cap if pd.notna(cfo) and market_cap > 0.0 else np.nan
                )
            else:
                bp_values.append(np.nan)
                cfy_values.append(np.nan)
        bp_series[symbol] = pd.Series(bp_values, index=refresh_dates)
        cfy_series[symbol] = pd.Series(cfy_values, index=refresh_dates)

    def to_daily(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(index=calendar, columns=UNIVERSE_SYMBOLS, dtype=float)
        return frame.reindex(calendar).ffill().reindex(columns=UNIVERSE_SYMBOLS)

    # ``pd.DataFrame(dict_of_series)`` is already indexed by refresh date with one
    # column per symbol, which is exactly the layout ``to_daily`` reindexes onto the
    # calendar.  Transposing here would put symbols on the index and every
    # ``reindex(calendar)`` would match nothing, silently producing an all-NaN panel
    # (a vacuous flat strategy).  Do NOT transpose.
    return {
        "book_to_price": to_daily(pd.DataFrame(bp_series)),
        "cash_flow_yield": to_daily(pd.DataFrame(cfy_series)),
    }


# ---------------------------------------------------------------------------
# Signal, sizing and backtest (reuse h184 / h187 primitives)
# ---------------------------------------------------------------------------


def cross_sectional_z(signal: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score with winsorization at +/-3 (h187 contract)."""
    return h187.cross_sectional_z(signal)


def value_signal_weights(
    z: pd.DataFrame,
    entry_z: float,
    exit_z: float,
    k: int,
    products: list[str] | None = None,
) -> pd.DataFrame:
    """Hysteresis cross-sectional rank: long top-k (high z) / short bottom-k.

    Value direction is **long high book-to-price (cheap), short low (expensive)**,
    so -- unlike H187's long-low accruals signal -- the highest z is the long leg.
    Exit a long when z falls to/below ``exit_z``; exit a short when z rises to/above
    ``exit_z``.
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
            if state[product] == 1 and value <= exit_z:
                new[product] = 0
            elif state[product] == -1 and value >= exit_z:
                new[product] = 0
            elif state[product] == 0:
                if value >= entry_z:
                    long_candidates.append((product, value))
                elif value <= -entry_z:
                    short_candidates.append((product, value))
        held_longs = [product for product in products if new[product] == 1]
        held_shorts = [product for product in products if new[product] == -1]
        # Add new longs (most positive z first)
        for product, _ in sorted(long_candidates, key=lambda item: item[1], reverse=True):
            if len(held_longs) >= k:
                break
            new[product] = 1
            held_longs.append(product)
        # Add new shorts (most negative z first)
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
    """Cross-sectional z + hysteresis on daily features, vol-target scaled."""
    z = cross_sectional_z(feature_daily)
    active_counts = z.notna().sum(axis=1)
    weights = value_signal_weights(
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
    """Input-only diagnostic: cross-sectional Spearman of B/P vs CFO yield."""
    left, right = features["book_to_price"], features["cash_flow_yield"]
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

    observations = load_all_observations(UNIVERSE_SYMBOLS)
    if download_only:
        coverage = {
            "symbols_with_observations": int(len(observations)),
            "total_symbols_requested": len(UNIVERSE_SYMBOLS),
            "first_end": str(min(obs["end"].min() for obs in observations.values())).split()[0]
            if observations
            else "",
        }
        print(json.dumps(coverage, indent=2))
        return coverage

    closes = load_or_fetch_closes(products)
    returns = closes.reindex(calendar).ffill().pct_change(fill_method=None)
    returns = returns.where(np.isfinite(returns))

    features_daily = build_value_panel(observations, closes, calendar)
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

    data_meta = {
        "xbrl_source": "SEC XBRL companyfacts (free/public/PIT)",
        "xbrl_url_template": xbrl.COMPANYFACTS_URL,
        "ticker_map_url": xbrl.TICKER_MAP_URL,
        "pit_field": "filed (acceptance date per reported fact)",
        "universe_symbols": UNIVERSE_SYMBOLS,
        "excluded_symbols": ["XOM", "BKNG"],
        "universe_size": len(UNIVERSE_SYMBOLS),
        "symbols_with_observations": int(len(observations)),
        "features": FEATURES,
        "min_active_names": MIN_ACTIVE_NAMES,
        "equity_tags": list(EQUITY_TAGS),
        "share_tags": [f"{ns}:{tag}" for ns, tag in SHARE_TAGS],
        "equity_source": "yfinance auto-adjusted Close (free/public)",
        "cost_one_way_bps": COST_ONE_WAY_BPS,
        "borrow_cost_modelled": False,
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
        "train_input_collinearity_bp_vs_cfy": train_collinearity(features_daily, train_index),
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
        help="report observation coverage and exit (no prices, no backtest)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only)
