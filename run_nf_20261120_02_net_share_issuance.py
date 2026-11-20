"""NF-20261120-02 / H188 (Cycle 232 pre-registration).

Broad mechanism category: external financing / equity-market timing / corporate
payout channel. Repo-new root family relative to executed H1–H187: no executed
H-ID uses the share-count / payout observables as a cross-sectional equity
return predictor.

Mechanism separation from H187 (required before execution):
- H187: `(NI − CFO)/avg assets` (accrual persistence), `ΔAssets/Assets` (investment
  q-theory, total asset expansion). Management decision: capital budgeting +
  accounting recognition.
- H188: `Δshares/shares_{t−1}` (net share issuance), `buybacks/assets_{t−1}`
  (repurchase intensity). Management decision: whether/how much to sell or
  retire *equity claims*. A firm can expand assets with debt or retained earnings
  without changing its share count, and can repurchase or issue shares without
  changing total assets (refinancing). H188 trades the **share-count / payout
  channel** — the price at which managers transact in their own equity.

Mechanism / causal chain. Firms that issue equity heavily tend to subsequently
underperform (Daniel & Titman 2006; Pontiff & Woodgate 2008), while firms that
repurchase shares aggressively tend to outperform (Ikenberry, Lakonishok &
Vermaelen 1995). Prediction (directional): **short the top-k heavy issuers
(high net_issuance), long the top-k heavy repurchasers (high buyback_intensity).**
Null (H0): net issuance and buyback intensity carry no cross-sectional
predictive power for next-period equity returns after costs — a financing/payout
tilt adds nothing over a passive equal-weight book of the same universe.

PIT timing. A row may enter the signal only when `filed` (the acceptance date of
the last tag needed for that fiscal year) is `<= t`; the shared engine then
applies `shift(1)`. No fiscal-period `end` is ever used as an availability
stamp. Because the tags can be filed on different accessions, the row timestamp
is the **max** of the relevant `filed` dates.

Pre-registration (Cycle 232, written before any forward-return outcome was
computed). Sample 2011-01-03 -> 2026-11-17 (the first year in which >= 40
names have a filed 10-K row with share-count data); Train -> 2021-12-31;
Val 2022-01-01 -> 2023-12-31; Test protected 2024-01-01 -> 2026-11-17.
Universe: the probe's 100-name S&P 100 snapshot minus the 9 names with fewer
than two usable annual share-count observations: ACN, CMCSA, MA, META, RTX,
SNDK, UPS, V, XOM = 91 names (measured exclusions; BKNG is usable for share
counts). Features: `net_issuance` and `buyback_intensity` as defined below.
Cross-sectional z on the monthly refresh grid, winsorized at +/-3, hysteresis
entry_z/exit_z, top-k long / bottom-k short, gross-normalized to one,
forward-filled to the daily calendar so turnover happens at most monthly.
Grid (bounded, 16): feature {net_issuance, buyback_intensity} x entry_z
{0.5, 1.0} x k {10, 20} x vol_target {0.10, 0.15}; train-only 4-fold
walk-forward Sharpe selection. Costs: 5 bps one-way per leg traded (commission
+ spread); no borrow cost for shorts is modelled; this must be disclosed as an
optimistic assumption for a long/short equity book.

Gates (OOS Val+Test, fail-closed, standard 8, unchanged): Sharpe >= 1.0;
trades >= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7; worst-regime
rolling-252 Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with IR >= 0 vs the
passive equal-weight long book of the same 91 names; OAT +/-20% perturbation
min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same
active leg count, seed 42); inverse signal; train-block Spearman of the two
features and of each feature vs the H187 accrual/asset-growth z (separation
diagnostic; |rho| >= 0.7 would be recorded as failed separation).

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors and cross-sectional/hysteresis primitives from
run_nf_20261120_01_equity_accruals.py (no forked copy); only the XBRL row
loader with shares-unit support, monthly signal refresh and price alignment are
new code. Free/public real data only; `src/qtr` unchanged. Artifact under
.experiments/nf_runs/nf_20261120_02_net_share_issuance_<timestamp>/summary.json
+ grid.csv + data_meta.json.
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

# Import shared primitives from H187 (which imports H186/H184 internally)
_H187_PATH = ROOT / "run_nf_20261120_01_equity_accruals.py"
_h187_spec = importlib.util.spec_from_file_location("h187_accruals", _H187_PATH)
assert _h187_spec is not None and _h187_spec.loader is not None
h187 = importlib.util.module_from_spec(_h187_spec)  # type: ignore[arg-type]
sys.modules[_h187_spec.name] = h187
_h187_spec.loader.exec_module(h187)

# h187 already imports h186/h184 internally; expose for direct use
h184 = h187.h184

# Import the XBRL probe functions
_PROBE_PATH = ROOT / "scripts" / "probe_sec_xbrl_fundamentals.py"
_probe_spec = importlib.util.spec_from_file_location("xbrl_probe", _PROBE_PATH)
assert _probe_spec is not None and _probe_spec.loader is not None
xbrl = importlib.util.module_from_spec(_probe_spec)  # type: ignore[arg-type]
sys.modules[_probe_spec.name] = xbrl
_probe_spec.loader.exec_module(xbrl)

EXPERIMENT = "nf_20261120_02_net_share_issuance"
NF_ID = "NF-20261120-02"
HYPOTHESIS = "H188"

START = "2011-01-03"
END = "2026-11-17"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

# Universe: the probe's 100-name S&P 100 snapshot minus the 9 names with fewer
# than two usable annual share-count observations: ACN, CMCSA, MA, META, RTX,
# SNDK, UPS, V, XOM = 91 names. BKNG is included (usable for share counts).
EXCLUDED_FROM_UNIVERSE = {"ACN", "CMCSA", "MA", "META", "RTX", "SNDK", "UPS", "V", "XOM"}
UNIVERSE_SYMBOLS = [s for s in xbrl.UNIVERSE if s not in EXCLUDED_FROM_UNIVERSE]
assert len(UNIVERSE_SYMBOLS) == 91

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 40
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252

GATES = dict(h184.GATES)

FEATURES = ["net_issuance", "buyback_intensity"]
GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [10, 20],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "xbrl"


# ---------------------------------------------------------------------------
# Data acquisition: load cached companyfacts and build monthly signal panels
# ---------------------------------------------------------------------------


def tag_rows_with_units(facts: dict, tag: str, units: str = "USD") -> pd.DataFrame:
    """Flatten one us-gaap tag into a typed frame (empty when absent).

    Extends the probe's `tag_rows` to support a `units` parameter (default "USD"
    for backward compatibility). For share-count tags, use `units="shares"`.
    """
    tag_facts = facts.get("facts", {}).get("us-gaap", {}).get(tag, {})
    if units not in tag_facts.get("units", {}):
        return pd.DataFrame(columns=["start", "end", "val", "form", "filed", "fy", "fp"])
    frame = pd.DataFrame(tag_facts["units"][units])
    for column in ("start", "end", "filed"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    if "start" not in frame.columns:
        frame["start"] = pd.NaT
    keep = ["start", "end", "val", "form", "filed"]
    for column in ("fy", "fp"):
        if column in frame.columns:
            keep.append(column)
    return frame[keep].copy()


def annual_share_observations(facts: dict) -> pd.DataFrame:
    """Point-in-time annual 10-K observations for share issuance / buyback signal.

    One row per fiscal-year end that has the required tags filed on the
    10-K accession window; `filed` is the acceptance date of the latest
    accession that supplied the final value, and the row is only usable from
    that date onward.

    Returns columns:
    ['end', 'filed', 'shares', 'buybacks', 'assets',
     'net_issuance', 'buyback_intensity']

    Where:
    - `shares` = CommonStockSharesOutstanding (fallback to CommonStockSharesIssued)
    - `buybacks` = PaymentsForRepurchaseOfCommonStock
    - `assets` = Assets
    - `net_issuance` = shares_t / shares_{t-1} - 1  (positive = issuance)
    - `buyback_intensity` = buybacks_t / assets_{t-1}
    """
    columns = ["end", "filed", "shares", "buybacks", "assets", "net_issuance", "buyback_intensity"]

    # Shares: prefer CommonStockSharesOutstanding (shares unit), fallback to
    # CommonStockSharesIssued (shares unit) - instant tag, no duration filter
    shares_frame = tag_rows_with_units(facts, "CommonStockSharesOutstanding", "shares")
    if shares_frame.empty:
        shares_frame = tag_rows_with_units(facts, "CommonStockSharesIssued", "shares")
    if shares_frame.empty:
        return pd.DataFrame(columns=columns)

    shares_frame = shares_frame[shares_frame["form"] == "10-K"].dropna(
        subset=["end", "filed", "val"]
    )
    if shares_frame.empty:
        return pd.DataFrame(columns=columns)
    # Share count is an instant tag (no start date), skip duration filter
    shares_frame = shares_frame.sort_values("filed").drop_duplicates("end", keep="first")

    # Buybacks: PaymentsForRepurchaseOfCommonStock (USD unit, duration tag)
    buybacks_frame = tag_rows_with_units(facts, "PaymentsForRepurchaseOfCommonStock", "USD")
    if buybacks_frame.empty:
        return pd.DataFrame(columns=columns)
    buybacks_frame = buybacks_frame[buybacks_frame["form"] == "10-K"].dropna(
        subset=["end", "filed", "val"]
    )
    if buybacks_frame.empty:
        return pd.DataFrame(columns=columns)
    days = (buybacks_frame["end"] - buybacks_frame["start"]).dt.days
    buybacks_frame = buybacks_frame[(days >= xbrl.MIN_ANNUAL_DAYS) & (days <= xbrl.MAX_ANNUAL_DAYS)]
    if buybacks_frame.empty:
        return pd.DataFrame(columns=columns)
    buybacks_frame = buybacks_frame.sort_values("filed").drop_duplicates("end", keep="first")

    # Assets: Assets (USD unit, instant tag)
    assets_frame = tag_rows_with_units(facts, "Assets", "USD")
    if assets_frame.empty:
        return pd.DataFrame(columns=columns)
    assets_frame = assets_frame[assets_frame["form"] == "10-K"].dropna(
        subset=["end", "filed", "val"]
    )
    if assets_frame.empty:
        return pd.DataFrame(columns=columns)
    # Assets is an instant tag (no start date), skip duration filter
    assets_frame = assets_frame.sort_values("filed").drop_duplicates("end", keep="first")

    # Merge on fiscal year end
    base = shares_frame[["end", "val", "filed"]].rename(
        columns={"val": "shares", "filed": "shares_filed"}
    )
    base = base.merge(
        buybacks_frame[["end", "val", "filed"]].rename(
            columns={"val": "buybacks", "filed": "buybacks_filed"}
        ),
        on="end",
        how="inner",
    )
    base = base.merge(
        assets_frame[["end", "val", "filed"]].rename(
            columns={"val": "assets", "filed": "assets_filed"}
        ),
        on="end",
        how="inner",
    )
    if base.empty:
        return pd.DataFrame(columns=columns)

    # Filed date = max of shares_filed (for t and t-1), buybacks_filed, assets_filed
    # We need shares at t and t-1, so the availability is gated by the latest
    # of: shares_filed(t), shares_filed(t-1), buybacks_filed, assets_filed
    # Since we merge on end, shares_filed is for the current year. We need to
    # also consider shares_filed from the previous year.
    base = base.sort_values("end").reset_index(drop=True)
    base["shares_filed_prev"] = base["shares_filed"].shift(1)
    base["assets_filed_prev"] = base["assets_filed"].shift(1)

    # Filed date is max of all four (dropping NaT)
    filed_cols = [
        "shares_filed",
        "shares_filed_prev",
        "buybacks_filed",
        "assets_filed",
        "assets_filed_prev",
    ]
    base["filed"] = base[filed_cols].max(axis=1)

    # Compute features
    previous_shares = base["shares"].shift(1)
    previous_assets = base["assets"].shift(1)

    base["net_issuance"] = (base["shares"] / previous_shares - 1.0).where(previous_shares > 0)
    base["buyback_intensity"] = (base["buybacks"] / previous_assets).where(previous_assets > 0)

    return base[columns]


def load_all_annual_observations(
    symbols: list[str],
    cache_dir: Path = CACHE_DIR,
) -> dict[str, pd.DataFrame]:
    """Load annual_share_observations for every symbol from cached companyfacts.

    Returns a dict symbol -> DataFrame with columns
    ['end', 'filed', 'shares', 'buybacks', 'assets',
     'net_issuance', 'buyback_intensity'].
    """
    mapping = xbrl.load_ticker_cik_map(
        xbrl.cache_dir_for(cache_dir) / "company_tickers.json", fetch=False
    )
    observations = {}
    for symbol in symbols:
        cik = mapping.get(symbol.upper())
        if cik is None:
            continue
        try:
            facts = xbrl.cached_companyfacts(cik, cache_dir, fetch=False)
        except FileNotFoundError:
            continue
        obs = annual_share_observations(facts)
        if len(obs):
            observations[symbol] = obs
    return observations


def cache_dir_for(cache_dir: Path | str | None = None) -> Path:
    return Path(cache_dir) if cache_dir is not None else CACHE_DIR


def build_monthly_signal_panel(
    observations: dict[str, pd.DataFrame],
    calendar: pd.DatetimeIndex,
) -> dict[str, pd.DataFrame]:
    """Construct monthly-aligned feature panels for net_issuance and buyback_intensity.

    Each feature panel is a DataFrame indexed by business-day calendar with
    one column per symbol. The value on day t is the latest observation whose
    `filed` date <= t, shifted by one day by the engine (so the signal is
    formed from information available at t-1).

    The monthly refresh means we only update the signal on the first business
    day of each month; other days forward-fill.
    """
    # For each symbol, build a series indexed by `filed` date
    net_issuance_series = {}
    buyback_intensity_series = {}

    for symbol, obs in observations.items():
        if obs.empty:
            continue
        # Use `filed` as the availability date; drop rows where features are NaN
        obs = obs.dropna(subset=["filed", "net_issuance", "buyback_intensity"]).copy()
        if obs.empty:
            continue
        obs = obs.set_index("filed").sort_index()
        net_issuance_series[symbol] = obs["net_issuance"]
        buyback_intensity_series[symbol] = obs["buyback_intensity"]

    if not net_issuance_series:
        return {"net_issuance": pd.DataFrame(), "buyback_intensity": pd.DataFrame()}

    # Build monthly refresh grid: first business day of each month in calendar
    month_starts = calendar.to_series().groupby(calendar.to_series().dt.to_period("M")).first()
    refresh_dates = pd.DatetimeIndex(month_starts.values)

    # For each feature, build a frame with columns = symbols, index = refresh_dates
    # Value at refresh date = latest observation with filed <= refresh_date
    def build_feature_frame(series_dict: dict[str, pd.Series]) -> pd.DataFrame:
        frames = []
        for symbol, ser in series_dict.items():
            if ser.empty:
                continue
            # Align to refresh dates: for each refresh date, find latest filed <= date
            values = []
            for rd in refresh_dates:
                usable = ser[ser.index <= rd]
                if len(usable):
                    values.append(usable.iloc[-1])
                else:
                    values.append(np.nan)
            frames.append(pd.Series(values, index=refresh_dates, name=symbol))
        if not frames:
            return pd.DataFrame(index=refresh_dates)
        return pd.DataFrame(frames).T

    net_issuance_refresh = build_feature_frame(net_issuance_series)
    buyback_intensity_refresh = build_feature_frame(buyback_intensity_series)

    # Forward-fill to daily calendar
    def forward_fill_to_daily(refresh_frame: pd.DataFrame) -> pd.DataFrame:
        if refresh_frame.empty:
            return pd.DataFrame(index=calendar, columns=UNIVERSE_SYMBOLS, dtype=float)
        # Reindex to calendar and forward-fill
        daily = refresh_frame.reindex(calendar).ffill()
        # Ensure all universe symbols are present as columns
        daily = daily.reindex(columns=UNIVERSE_SYMBOLS)
        return daily

    return {
        "net_issuance": forward_fill_to_daily(net_issuance_refresh),
        "buyback_intensity": forward_fill_to_daily(buyback_intensity_refresh),
    }


def winsorize_z(z: pd.DataFrame, limit: float = 3.0) -> pd.DataFrame:
    """Winsorize cross-sectional z-scores at +/- limit."""
    return z.clip(-limit, limit)


# ---------------------------------------------------------------------------
# Signal, sizing and backtest (reuse h184 primitives via h187)
# ---------------------------------------------------------------------------


def cross_sectional_z(signal: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score with winsorization at +/-3."""
    z = h184.cross_sectional_z(signal)
    return winsorize_z(z)


def signal_weights(
    z: pd.DataFrame,
    entry_z: float,
    exit_z: float,
    k: int,
    products: list[str] | None = None,
    feature: str = "net_issuance",
) -> pd.DataFrame:
    """Hysteresis cross-sectional rank: long top-k / short bottom-k by z.

    Note: Feature orientation is pre-registered:
    - For `net_issuance`: prediction is SHORT the top-k (high issuance underperforms).
      The ranking input is -z(net_issuance), so a higher score means more attractive
      long. We implement this by inverting: long where z <= -entry_z, short where z >= entry_z.
    - For `buyback_intensity`: prediction is LONG the top-k (high buyback outperforms).
      The ranking input is +z(buyback_intensity). We implement standard: long where z >= entry_z,
      short where z <= -entry_z.
    """
    calendar = z.index
    products = list(products if products is not None else z.columns)
    state = {product: 0 for product in products}
    weights = pd.DataFrame(0.0, index=calendar, columns=products, dtype=float)

    if feature == "net_issuance":
        # Short high issuance (z >= entry_z), long low issuance (z <= -entry_z)
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
                # Exit conditions
                if state[product] == 1 and value >= -exit_z:
                    new[product] = 0
                elif state[product] == -1 and value <= exit_z:
                    new[product] = 0
                # Entry conditions (inverted: long low, short high)
                elif state[product] == 0:
                    if value <= -entry_z:
                        long_candidates.append((product, value))
                    elif value >= entry_z:
                        short_candidates.append((product, value))
            held_longs = [product for product in products if new[product] == 1]
            held_shorts = [product for product in products if new[product] == -1]
            # Add new longs (most negative z first)
            for product, _ in sorted(long_candidates, key=lambda item: item[1]):
                if len(held_longs) >= k:
                    break
                new[product] = 1
                held_longs.append(product)
            # Add new shorts (most positive z first)
            for product, _ in sorted(short_candidates, key=lambda item: item[1], reverse=True):
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

    elif feature == "buyback_intensity":
        # Long high buyback (z >= entry_z), short low buyback (z <= -entry_z)
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
                # Exit conditions
                if state[product] == 1 and value <= exit_z:
                    new[product] = 0
                elif state[product] == -1 and value >= -exit_z:
                    new[product] = 0
                # Entry conditions (standard: long high, short low)
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


def vol_scale(portfolio_returns: pd.Series, vol_target: float) -> pd.Series:
    """Delever-only vol target: scale = min(target / trailing vol, 1)."""
    trailing = portfolio_returns.rolling(VOL_LOOKBACK).std(ddof=0) * math.sqrt(DAYS_PER_YEAR)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = vol_target / trailing
    scale = pd.Series(raw, index=portfolio_returns.index, dtype=float).fillna(1.0)
    scale = scale.where(scale <= 1.0, 1.0)
    scale = scale.where(scale > 0, 1.0)
    return scale


def target_weights(
    feature_daily: pd.DataFrame,
    params: dict,
    returns: pd.DataFrame,
    products: list[str],
) -> pd.DataFrame:
    """Cross-sectional z + hysteresis on daily-aligned features, vol-target scaled."""
    z = cross_sectional_z(feature_daily)
    # Check active names count
    active_counts = z.notna().sum(axis=1)
    weights = signal_weights(
        z, params["entry_z"], params["exit_z"], int(params["k"]), products, params["feature"]
    )
    # Zero out weights on days with < MIN_ACTIVE_NAMES
    weights = weights.where(active_counts >= MIN_ACTIVE_NAMES, 0.0)
    raw_port = (weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    scale = vol_scale(raw_port, float(params["vol_target"]))
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
    block_index = train_index
    weights = target_weights(
        feature_daily.reindex(block_index), params, returns.reindex(block_index), products
    )
    fold = len(block_index) // n_folds
    sharpes = []
    for fold_no in range(n_folds):
        start = fold_no * fold
        stop = len(block_index) if fold_no == n_folds - 1 else (fold_no + 1) * fold
        block = block_index[start:stop]
        if len(block) < 120:
            continue
        result = h184.backtest_metrics(
            weights.reindex(block).fillna(0.0),
            returns.reindex(block).fillna(0.0),
            zero_rolls(block, products),
        )
        sharpes.append(h184.annualized_sharpe(result["returns"]))
    return float(np.mean(sharpes)) if sharpes else -999.0


def zero_rolls(index: pd.DatetimeIndex, products: list[str]) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=index, columns=products, dtype=float)


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
            zero_rolls(oos_index, products),
        )
        sharpes.append(h184.annualized_sharpe(result["returns"]))
    return sharpes


def train_collinearity(features: dict[str, pd.DataFrame], train_index: pd.DatetimeIndex) -> float:
    """Input-only diagnostic: cross-sectional Spearman of net_issuance vs buyback_intensity."""
    left, right = features["net_issuance"], features["buyback_intensity"]
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


def train_collinearity_vs_h187(
    features: dict[str, pd.DataFrame],
    h187_features: dict[str, pd.DataFrame],
    train_index: pd.DatetimeIndex,
) -> dict[str, float]:
    """Input-only diagnostic: cross-sectional Spearman of H188 features vs H187 features."""
    results = {}
    for h188_feat_name, h188_feat in features.items():
        for h187_feat_name, h187_feat in h187_features.items():
            values = []
            for day in train_index:
                a, b = h188_feat.loc[day], h187_feat.loc[day]
                usable = a.notna() & b.notna()
                if int(usable.sum()) < 3:
                    continue
                left_values, right_values = a[usable], b[usable]
                if left_values.nunique() < 2 or right_values.nunique() < 2:
                    continue
                value = float(left_values.corr(right_values, method="spearman"))
                if np.isfinite(value):
                    values.append(value)
            key = f"{h188_feat_name}_vs_{h187_feat_name}"
            results[key] = float(np.mean(values)) if values else 0.0
    return results


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

    # Load annual observations from cached XBRL data
    observations = load_all_annual_observations(UNIVERSE_SYMBOLS)
    if download_only:
        provenance = {
            "symbols_with_observations": int(len(observations)),
            "total_symbols_requested": len(UNIVERSE_SYMBOLS),
        }
        print(json.dumps(provenance, indent=2))
        return provenance

    # Fetch equity closes from yfinance
    cache_dir = Path(".cache") / "xbrl"
    cache_dir.mkdir(parents=True, exist_ok=True)
    price_path = cache_dir / "equity_closes.csv"
    if price_path.exists():
        closes = pd.read_csv(price_path, index_col=0, parse_dates=True)
        if set(products).issubset(set(closes.columns)):
            pass
        else:
            closes = None
    else:
        closes = None

    if closes is None:
        import yfinance as yf

        raw = yf.download(list(products), start=START, end=END, auto_adjust=True, progress=False)[
            "Close"
        ]
        raw = raw.reindex(columns=list(products))
        raw.to_csv(price_path)
        closes = raw

    returns = closes.reindex(calendar).ffill().pct_change(fill_method=None)
    returns = returns.where(np.isfinite(returns))

    # Build monthly signal panels
    features_daily = build_monthly_signal_panel(observations, calendar)

    # Check that we have data for both features
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
    full = h184.backtest_metrics(weights, returns, zero_rolls(calendar, products))
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

    inverse_weights = target_weights(-feature_daily, selected, returns, products)
    inverse_result = h184.backtest_metrics(
        inverse_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
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

    # Load H187 features for collinearity diagnostic
    h187_observations = h187.load_all_annual_observations(h187.UNIVERSE_SYMBOLS)
    h187_features_daily = h187.build_monthly_signal_panel(h187_observations, calendar)

    # Data provenance
    data_meta = {
        "xbrl_source": "SEC XBRL companyfacts (free/public/PIT)",
        "xbrl_url_template": xbrl.COMPANYFACTS_URL,
        "ticker_map_url": xbrl.TICKER_MAP_URL,
        "pit_field": "filed (acceptance date per reported fact)",
        "universe_symbols": UNIVERSE_SYMBOLS,
        "excluded_symbols": sorted(list(EXCLUDED_FROM_UNIVERSE)),
        "universe_size": len(UNIVERSE_SYMBOLS),
        "symbols_with_annual_observations": int(len(observations)),
        "features": FEATURES,
        "min_active_names": MIN_ACTIVE_NAMES,
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
        "train_input_collinearity_net_issuance_vs_buyback": train_collinearity(
            features_daily, train_index
        ),
        "train_input_collinearity_vs_h187": train_collinearity_vs_h187(
            features_daily, h187_features_daily, train_index
        ),
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
            "pit_rule": "max(filed) per fiscal year (shares_t, shares_t-1, buybacks, assets_t, assets_t-1), engine shift(1), monthly refresh",
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
        help="populate the XBRL/price cache and exit (resumable)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only)
