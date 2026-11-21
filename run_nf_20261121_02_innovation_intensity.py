"""NF-20261121-02 / H192 (Cycle 246 pre-registration and execution).

Broad mechanism category: fundamental / corporate investment in intangibles
(innovation intensity). Repo-new root family relative to executed H1-H191: no
executed H-ID uses research-and-development (R&D) spending as a cross-sectional
fundamental.  The closest prior families are H187 (accruals / asset growth --
earnings quality and *total* asset investment), H188 (net share issuance --
external financing), H189 (gross profitability -- confirmed data-blocked on SEC
XBRL, Cycle 234) and H191 (value -- book equity / cash flow scaled by *price*).
R&D intensity is the share of *revenue* a firm reinvests in innovation; it is a
corporate-investment / intangible-capital mechanism, not a valuation, financing
or earnings-quality signal, and it is directionally *opposite* to value (value
firms are cheap on book; high-R&D firms look expensive on book because R&D is
expensed).  That makes it a distinct return-generating mechanism (per directive
sec. 6), not a parameter/universe/market variant of any prior family.

Mechanism / causal chain.  Accounting standards require firms to expense R&D as
incurred, so the firm's reported book equity understates its intangible capital
(Lev & Sougiannis 1996; Chan, Lakonishok & Sottile 1996).  The stock market
underreacts to the information content of current R&D outlays -- the future
payoff of an R&D project arrives years later, after the cash has already been
expensed -- so firms with high R&D intensity subsequently earn higher returns.
The mechanism can persist because the intangible payoff is hard to observe and
the signal is slow-moving (annual 10-K), so arbitrageurs under-weight it.  A
behavioural reading (investors over-extrapolate and neglect intangibles) and a
risk-based reading (high-R&D firms are growth options exposed to a different
risk factor) both predict the same sign.  Prediction (directional): **long the
top-k names by cross-sectional R&D intensity (R&D / revenue), short the
bottom-k (least innovative).**  Null (H0): the R&D-intensity cross-section
carries no predictive power for next-period equity returns after costs -- an
innovation tilt adds nothing over a passive equal-weight book of the same
universe.

Mechanism separation from H187/H188/H189/H191.  H187 (accruals / asset growth)
scales earnings and *total* asset growth by assets -- earnings quality and
empire-building.  H188 (net share issuance) scales equity issuance by shares --
external financing.  H189 (gross profitability) scales gross profit by assets --
current profitability.  H191 (value) scales a *stock* fundamental by *price*
(book-to-price, cash-flow yield) -- valuation.  R&D intensity scales an R&D
*flow* by *revenue* (an income-statement denominator, not assets and not price)
-- innovation investment.  It is therefore a genuinely distinct economic
mechanism, and it is the *opposite* sign to value (high R&D -> low book-to-price
-> value short leg), so it cannot be reproduced as a value variant.

PIT timing.  A row may enter the signal only when ``filed`` (the acceptance date
of the last tag needed for that fiscal year) is ``<= t``; the shared engine then
applies ``shift(1)``.  No fiscal-period ``end`` is ever used as an availability
stamp.  Because the contributing tags can be filed on different accessions, the
row timestamp is the **max** of the contributing ``filed`` dates.

Pre-registration (Cycle 246, written before any forward-return outcome was
computed).  Sample 2011-01-03 -> 2026-11-17; Train -> 2021-12-31; Val
2022-01-01 -> 2023-12-31; Test protected 2024-01-01 -> 2026-11-17.  Universe:
the 100-name S&P 100 snapshot in
``scripts/probe_sec_xbrl_fundamentals.py:UNIVERSE`` minus XOM and BKNG (same
measured exclusions as H187/H188/H191).  Only names with >= 2 annual 10-K
R&D-and-revenue observations are tradeable (measured: 57 of 98, well above the
40-name minimum; H189 was rejected as data-blocked for *lacking* coverage, which
this family does not).  Feature ``rd_intensity`` = ResearchAndDevelopmentExpense
/ Revenues on a common fiscal ``end``; R&D is a us-gaap duration tag (USD) and
revenue falls back to ``RevenueFromContractWithCustomerExcludingAssessedTax`` when
``Revenues`` is absent.  Cross-sectional z on the monthly refresh grid,
winsorized at +/-3, hysteresis entry_z/exit_z, top-k long (highest z) / bottom-k
short (lowest z), gross-normalized to one, forward-filled to the daily calendar
so turnover happens at most monthly.  Grid (bounded, 16): feature {rd_intensity,
rd_to_assets} x entry_z {0.5, 1.0} x exit_z {0.0} x k {5, 10} x vol_target
{0.10, 0.15}; train-only 4-fold walk-forward Sharpe selection.  Costs: 5 bps
one-way per leg
traded (commission + spread); no borrow cost for shorts is modelled -- disclosed
as an optimistic assumption for a long/short equity book (identical to
H187/H191).

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from H187/H190/H191):
Sharpe >= 1.0; trades >= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7;
worst-regime rolling-252 Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with IR
>= 0 vs the passive equal-weight long book of the same universe; OAT +/-20%
perturbation min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same active
leg count, seed 42); inverse signal (anti-innovation); train-block Spearman of
``rd_intensity`` vs ``rd_to_assets`` as an input-collinearity diagnostic.

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors and cross-sectional/hysteresis primitives from
run_nf_20261120_01_equity_accruals.py (H187), which in turn imports
run_nf_20261119_02_commodity_hedging_pressure.py (H186) and
run_nf_20261114_01_commodity_termstructure_carry.py (H184); the SEC XBRL loader
helpers come from scripts/probe_sec_xbrl_fundamentals.py.  Only the R&D/revenue
row loader, the monthly signal refresh and the (long-high) value signal weights
are new code.  Free/public real data only; ``src/qtr`` unchanged.  Artifact under
.experiments/nf_runs/nf_20261121_02_innovation_intensity_<timestamp>/summary.json
+ grid.csv + data_meta.json.
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

EXPERIMENT = "nf_20261121_02_innovation_intensity"
NF_ID = "NF-20261121-02"
HYPOTHESIS = "H192"

START = "2011-01-03"
END = "2026-11-17"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

# Universe: the probe's 100-name S&P 100 snapshot minus XOM and BKNG (same as H187).
UNIVERSE_SYMBOLS = [s for s in xbrl.UNIVERSE if s not in ("XOM", "BKNG")]
assert len(UNIVERSE_SYMBOLS) == 98

COST_ONE_WAY_BPS = 5.0
MIN_ACTIVE_NAMES = 40
MIN_OBSERVATIONS = 2  # minimum annual 10-K rows for a name to be tradeable
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252

GATES = dict(h184.GATES)

FEATURES = ["rd_intensity", "rd_to_assets"]
GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [5, 10],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "xbrl"

# R&D is reported as a us-gaap duration tag in USD; revenue prefers the plain
# ``Revenues`` tag and falls back to the post-ASC-606 contract-revenue tag.
RD_TAG = "ResearchAndDevelopmentExpense"
REVENUE_TAGS = ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax")
ASSETS_TAG = "Assets"


# ---------------------------------------------------------------------------
# Data acquisition: load cached companyfacts and build monthly signal panels
# ---------------------------------------------------------------------------


def load_all_observations(
    symbols: list[str],
    cache_dir: Path = CACHE_DIR,
) -> dict[str, pd.DataFrame]:
    """Load per-symbol R&D-intensity observations from cached companyfacts.

    Returns a dict symbol -> DataFrame with columns
    ['end', 'filed', 'rd', 'revenue', 'assets', 'rd_intensity', 'rd_to_assets']
    for every fiscal year that has a filed R&D and revenue (and, when present,
    assets) observation on the same fiscal ``end``.
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
        obs = innovation_observations(facts)
        if len(obs):
            observations[symbol] = obs
    return observations


def _duration_usd(facts: dict, tag: str) -> pd.DataFrame:
    """Annual 10-K duration rows for one us-gaap USD tag (filed-deduped)."""
    frame = xbrl.tag_rows(facts, tag)
    if frame.empty:
        return frame
    frame = frame[frame["form"] == "10-K"].dropna(subset=["end", "filed", "val"])
    if frame.empty:
        return frame
    days = (frame["end"] - frame["start"]).dt.days
    frame = frame[(days >= xbrl.MIN_ANNUAL_DAYS) & (days <= xbrl.MAX_ANNUAL_DAYS)]
    return frame.sort_values("filed").drop_duplicates("end", keep="first")


def _instant_usd(facts: dict, tag: str) -> pd.DataFrame:
    """Annual 10-K *instant* rows for one us-gaap USD tag (filed-deduped).

    Instant (balance-sheet) tags such as ``Assets`` carry no duration ``start``,
    so the 340-380 day duration filter does not apply; only the ``form == 10-K``
    and filed-date de-duplication are used.
    """
    frame = xbrl.tag_rows(facts, tag)
    if frame.empty:
        return frame
    frame = frame[frame["form"] == "10-K"].dropna(subset=["end", "filed", "val"])
    return frame.sort_values("filed").drop_duplicates("end", keep="first")


def innovation_observations(facts: dict) -> pd.DataFrame:
    """Point-in-time annual innovation rows for one company.

    One row per fiscal-year end that has R&D and revenue (and, when reported,
    assets) on the same ``end``.  ``filed`` is the latest contributing
    acceptance date -- the first date the full row is public.  R&D intensity is
    R&D / revenue; the auxiliary R&D / assets ratio is the collinearity
    diagnostic (not traded).
    """
    columns = [
        "end",
        "filed",
        "rd",
        "revenue",
        "assets",
        "rd_intensity",
        "rd_to_assets",
    ]
    rd = _duration_usd(facts, RD_TAG)
    if rd.empty:
        return pd.DataFrame(columns=columns)
    rd = rd.rename(columns={"val": "rd", "filed": "rd_filed"})

    revenue = pd.DataFrame()
    for tag in REVENUE_TAGS:
        revenue = _duration_usd(facts, tag)
        if len(revenue):
            break
    if revenue.empty:
        return pd.DataFrame(columns=columns)
    revenue = revenue.rename(columns={"val": "revenue", "filed": "rev_filed"})

    assets = _instant_usd(facts, ASSETS_TAG)
    assets = assets.rename(columns={"val": "assets", "filed": "assets_filed"})

    base = rd[["end", "rd", "rd_filed"]].merge(
        revenue[["end", "revenue", "rev_filed"]], on="end", how="inner"
    )
    if base.empty:
        return pd.DataFrame(columns=columns)
    base["filed"] = base[["rd_filed", "rev_filed"]].max(axis=1)
    if len(assets):
        base = base.merge(assets[["end", "assets", "assets_filed"]], on="end", how="left")
        both_filed = base[["rd_filed", "rev_filed", "assets_filed"]]
        base["filed"] = both_filed.max(axis=1)
    else:
        base["assets"] = np.nan
    base = base.sort_values("end").reset_index(drop=True)
    base["rd_intensity"] = (base["rd"] / base["revenue"]).where(base["revenue"] > 0)
    base["rd_to_assets"] = (base["rd"] / base["assets"]).where(base["assets"] > 0)
    base = base.dropna(subset=["filed", "rd_intensity"])
    return base[columns]


def build_innovation_panel(
    observations: dict[str, pd.DataFrame],
    calendar: pd.DatetimeIndex,
    products: list[str],
) -> dict[str, pd.DataFrame]:
    """Construct monthly rd_intensity and rd_to_assets panels (daily-aligned).

    On each month's first business day R, for every symbol with a filed row on or
    before R, the feature is the latest filed value (R&D intensity or R&D/assets).
    The monthly frame is forward-filled to the daily calendar.
    """
    refresh_dates = pd.DatetimeIndex(
        calendar.to_series().groupby(calendar.to_series().dt.to_period("M")).first().values
    )

    def build_feature_frame(column: str) -> pd.DataFrame:
        series: dict[str, pd.Series] = {}
        for symbol in products:
            obs = observations.get(symbol)
            if obs is None or obs.empty:
                continue
            obs = obs.dropna(subset=["filed", column]).sort_values("filed")
            if obs.empty:
                continue
            indexed = obs.set_index("filed")[column]
            values = []
            for rd in refresh_dates:
                usable = indexed[indexed.index <= rd]
                values.append(float(usable.iloc[-1]) if len(usable) else np.nan)
            series[symbol] = pd.Series(values, index=refresh_dates, name=symbol)
        if not series:
            return pd.DataFrame(index=calendar, columns=products, dtype=float)
        # ``pd.DataFrame(dict_of_series)`` already has index=refresh_dates and one
        # column per symbol, which is exactly the layout ``reindex(calendar)``
        # needs.  Transposing here would put symbols on the index and every
        # ``reindex(calendar)`` would match nothing, silently producing an
        # all-NaN panel (a vacuous flat strategy).  Do NOT transpose.
        frame = pd.DataFrame(series)
        return frame.reindex(calendar).ffill().reindex(columns=products)

    return {
        "rd_intensity": build_feature_frame("rd_intensity"),
        "rd_to_assets": build_feature_frame("rd_to_assets"),
    }


# ---------------------------------------------------------------------------
# Signal, sizing and backtest (reuse h184 / h187 primitives)
# ---------------------------------------------------------------------------


def cross_sectional_z(signal: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score with winsorization at +/-3 (h187 contract)."""
    return h187.cross_sectional_z(signal)


def innovation_signal_weights(
    z: pd.DataFrame,
    entry_z: float,
    exit_z: float,
    k: int,
    products: list[str] | None = None,
) -> pd.DataFrame:
    """Hysteresis cross-sectional rank: long top-k (high z) / short bottom-k.

    Innovation direction is **long high R&D intensity (innovative), short low
    (least innovative)**, so -- unlike H187's long-low accruals signal -- the
    highest z is the long leg (identical convention to H191 value).  This is the
    H184 ``signal_weights`` direction (long top-k / short bottom-k) re-used with
    winsorized z; it is defined explicitly here so the signal direction is a
    named, testable contract of this runner rather than an implicit dependency.
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
    weights = innovation_signal_weights(
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
    """Input-only diagnostic: cross-sectional Spearman of R&D intensity vs R&D/assets."""
    left, right = features["rd_intensity"], features["rd_to_assets"]
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

    # Restrict the tradable universe to names with >= MIN_OBSERVATIONS annual rows.
    tradable = [
        symbol
        for symbol in products
        if symbol in observations and len(observations[symbol]) >= MIN_OBSERVATIONS
    ]
    if len(tradable) < MIN_ACTIVE_NAMES:
        raise RuntimeError(
            f"tradable innovation universe {len(tradable)} < MIN_ACTIVE_NAMES {MIN_ACTIVE_NAMES}"
        )
    products = tradable
    observations = {symbol: observations[symbol] for symbol in products}

    closes = load_or_fetch_closes(products)
    returns = closes.reindex(calendar).ffill().pct_change(fill_method=None)
    returns = returns.where(np.isfinite(returns))

    features_daily = build_innovation_panel(observations, calendar, products)
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
        "universe_symbols": products,
        "universe_size": len(products),
        "excluded_symbols": ["XOM", "BKNG"],
        "symbols_with_observations": int(len(observations)),
        "min_observations": MIN_OBSERVATIONS,
        "features": FEATURES,
        "rd_tag": RD_TAG,
        "revenue_tags": list(REVENUE_TAGS),
        "assets_tag": ASSETS_TAG,
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
        "train_input_collinearity_rd_intensity_vs_rd_to_assets": train_collinearity(
            features_daily, train_index
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
            "pit_rule": "max(filed) per fiscal year, engine shift(1), monthly refresh",
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
