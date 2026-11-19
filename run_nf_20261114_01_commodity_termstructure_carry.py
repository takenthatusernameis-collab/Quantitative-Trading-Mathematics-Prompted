"""NF-20261114-01 / H184 (Cycle 214 pre-registration, Cycle 215 execution).

Broad mechanism category: carry / commodity term structure (roll yield on
physically delivered futures).  Repo-new root family relative to executed
H1-H183: no executed H-ID trades the per-contract roll-yield slope; H23 tested
directional crypto TSMOM on perpetual futures (rejected) and H183 tested
delta-neutral funding carry (rejected) -- different instrument, signal, and
return source.  Parameter, timeframe, universe and market variations are
explicitly not new families; this is roll-yield capture on physically delivered
commodity futures, not perpetual funding accrual.

Mechanism / causal chain.  Physically delivered futures embed inventory carry:
a curve sloping down (front above deferred, backwardation) pays a long position
positive roll yield as contracts age toward delivery; hedgers pay speculators
to warehouse.  Null (H0): the front/second settlement slope known at day t's
settle has no predictive power for next-period roll-adjusted returns after CNY
costs -- timing adds nothing over a passive front-month long book.

PIT timing.  Each cross-section file is the official settlement record for
trade date t and is knowable at t's settle.  The signal is computed from day-t
settlements only; positions are formed no earlier than t+1 via an explicit
``shift(1)`` in ``backtest_metrics``.  ``held_returns`` prices the contract that
was *known* at t-1 and held into day t, so no day-t settlement enters the day-t
signal and no future contract enters the day-t return.

Pre-registration (Cycle 214, before any forward-return inspection).
NF-ID NF-20261114-01 (H184).  Sample 2016-01-04 -> 2026-11-17 (bounded first
scope).  Train ->2023-06-30; Val 2023-07-01 -> 2024-12-31; Test protected
2025-01-01 -> 2026-11-17.  Universe: SHFE RB, CU, AL, ZN, AU, AG (from
2016-01-04) and INE SC (from 2018-03-26); exclude any contract whose delivery
month equals the current month.  Signal: annualized slope
``ln(F1/F2) * 12 / months_between(F1, F2)`` from the two nearest contracts with
settlement > 0 and open interest >= OI_FLOOR, using day-t settlements.
Cross-sectional rank: long top-k / short bottom-k by z-scored slope, equal
weight, hysteresis entry/exit on z.  Grid (bounded, 24):
entry_z {0.5, 1.0, 1.5} x exit_z {0.0, 0.5} x k {1, 3, 5} x
vol_target {0.10, 0.15}; train-only 4-fold walk-forward Sharpe selection;
Test protected.  Costs (CNY, explicit): commission 2 bps + slippage 3 bps per
one-way side per leg (5 bps one-way per contract traded), roll crossing 1 bps
when the held front contract changes.  Vol targeting scales exposure down to
target, never up.

Gates (OOS Val+Test, fail-closed, standard 8): Sharpe >= 1.0; trades >= 50;
PF >= 1.3; maxDD <= 15%; WF stability >= 0.7; worst-regime rolling-252 Sharpe
>= 0.3; benchmark p <= 0.05 (two-sided, the published statistic) with IR >= 0
vs the passive front-month long book; perturbation min ratio >= 0.5.

Ablations/falsifiers: passive front-month long book; random ranking (same
active contract-days, seed 42); inverse-slope signal; OAT +/-20% perturbation.

Implementation constraints: resumable on-disk cache under
.cache/commodity_settlements/ (skip existing files, 404 markers included); one
request per trade date per venue; tolerate 404 holidays; record per-product
first available dates; parsers/URL builders imported from
scripts/probe_commodity_termstructure_availability.py (no forked copy).
Artifact under .experiments/nf_runs/<experiment>_<timestamp>/summary.json +
grid.csv.  ``src/qtr`` unchanged; free/public real data only.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

try:
    from qtr.validation.statistics import benchmark_significance_gate, compare_to_benchmark
except ImportError:  # allow `python run_nf_*.py` with no editable install
    sys.path.insert(0, str(ROOT / "src"))
    from qtr.validation.statistics import benchmark_significance_gate, compare_to_benchmark

# Single source of truth for the Chinese exchange cross-sections: import the
# probe's URL builders and parsers instead of forking a second copy.
_PROBE_PATH = ROOT / "scripts" / "probe_commodity_termstructure_availability.py"
_probe_spec = importlib.util.spec_from_file_location("commodity_probe", _PROBE_PATH)
assert _probe_spec is not None and _probe_spec.loader is not None
_probe = importlib.util.module_from_spec(_probe_spec)  # type: ignore[arg-type]
sys.modules[_probe_spec.name] = _probe
_probe_spec.loader.exec_module(_probe)

source_url = _probe.source_url
fetch = _probe.fetch
FetchError = _probe.FetchError
parse_exchange_json = _probe.parse_exchange_json
parse_pipe_text = _probe.parse_pipe_text
parse_cffex_csv = _probe.parse_cffex_csv

EXPERIMENT = "nf_20261114_01_commodity_termstructure_carry"
NF_ID = "NF-20261114-01"
HYPOTHESIS = "H184"

START = "2016-01-04"
END = "2026-11-17"
TRAIN_END = "2023-06-30"
VAL_END = "2024-12-31"

# Declared first available dates (pre-registration universe).  A product is
# eligible only from its venue's first available date; the first date actually
# observed in the cached data is recorded in provenance and the later of the
# two is used.
FIRST_DATE = {
    ("SHFE", "RB"): "2016-01-04",
    ("SHFE", "CU"): "2016-01-04",
    ("SHFE", "AL"): "2016-01-04",
    ("SHFE", "ZN"): "2016-01-04",
    ("SHFE", "AU"): "2016-01-04",
    ("SHFE", "AG"): "2016-01-04",
    ("INE", "SC"): "2018-03-26",
}

UNIVERSE = [("SHFE", code) for code in ("RB", "CU", "AL", "ZN", "AU", "AG")] + [("INE", "SC")]

OI_FLOOR = 100.0  # contracts; both front and second must clear it
OPEN_INTEREST_FLOOR = OI_FLOOR
COST_ONE_WAY_BPS = 5.0  # commission 2 bps + slippage 3 bps per one-way side
SIDE_BPS = COST_ONE_WAY_BPS
ROLL_CROSS_BPS = 1.0  # when the held front contract changes
DAYS_PER_YEAR = 252
VOL_LOOKBACK = 60  # trailing days for the delever-only vol target
SEED = 42
WORKERS = 4
CACHE_DIR = Path(".cache") / "commodity_settlements"

GRID = {
    "entry_z": [0.5, 1.0, 1.5],
    "exit_z": [0.0, 0.5],
    "k": [1, 3, 5],
    "vol_target": [0.10, 0.15],
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

PARSER_BY_SOURCE = {
    "SHFE": parse_exchange_json,
    "INE": parse_exchange_json,
    "CZCE": parse_pipe_text,
    "CFFEX": parse_cffex_csv,
}


# ---------------------------------------------------------------------------
# Cache / download
# ---------------------------------------------------------------------------


def cache_dir_for(cache_dir: Path | str | None) -> Path:
    return Path(cache_dir) if cache_dir is not None else CACHE_DIR


def cache_path(source: str, day, cache_dir: Path | str | None = None) -> Path:
    return cache_dir_for(cache_dir) / source / f"{pd.Timestamp(day).strftime('%Y%m%d')}.dat"


def miss_path(source: str, day, cache_dir: Path | str | None = None) -> Path:
    return cache_dir_for(cache_dir) / source / f"{pd.Timestamp(day).strftime('%Y%m%d')}.miss"


def fetch_into_cache(
    source: str,
    day,
    cache_dir: Path | str | None = None,
    retries: int = 2,
    retry_delay: float = 1.0,
) -> str:
    """Ensure one cross-section is cached; returns HIT / OK / MISSING / ERROR.

    ``404`` (holiday or pre-listing date) writes a ``.miss`` marker so later
    runs do not re-request it.  Existing ``.dat`` files are never re-downloaded,
    which makes the download resumable across sessions.
    """
    path = cache_path(source, day, cache_dir)
    if path.exists():
        return "HIT"
    if miss_path(source, day, cache_dir).exists():
        return "MISSING"
    attempt = 0
    while True:
        try:
            payload = fetch(source, day, retries=0)
        except FetchError:
            if attempt >= retries:
                return "ERROR"
            attempt += 1
            time.sleep(retry_delay)
            continue
        if payload is None:
            marker = miss_path(source, day, cache_dir)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("404\n")
            return "MISSING"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return "OK"


def source_dates(source: str, calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Trading calendar for one venue, bounded by its pre-registered start."""
    starts = [pd.Timestamp(first) for (src, _), first in FIRST_DATE.items() if src == source]
    start = max([pd.Timestamp(START)] + starts)
    return calendar[calendar >= start]


def ensure_cached(
    universe: list[tuple[str, str]],
    calendar: pd.DatetimeIndex,
    cache_dir: Path | str | None = None,
    workers: int = WORKERS,
) -> dict:
    """Download every (venue, date) cross-section once; resumable and deduped."""
    sources = sorted({source for source, _ in universe})
    jobs = [(source, day) for source in sources for day in source_dates(source, calendar)]
    counts: dict[str, dict[str, int]] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_into_cache, source, day, cache_dir): (source, day)
            for source, day in jobs
        }
        for future in as_completed(futures):
            source, _ = futures[future]
            bucket = counts.setdefault(source, {})
            status = future.result()
            bucket[status] = bucket.get(status, 0) + 1
    return {
        "requests": int(len(jobs)),
        "status_counts": counts,
        "url_patterns": {
            source: source_url(source, pd.Timestamp(END)).replace(
                pd.Timestamp(END).strftime("%Y%m%d"), "{YYYYMMDD}"
            )
            for source in sources
        },
    }


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------


def normalize_delivery(raw: object, trade_day) -> str:
    """Normalize a contract delivery code to ``YYYYMM``.

    SHFE/INE publish ``YYMM`` (``"2402"``); CZCE/CFFEX publish 4-digit years.
    The decade is resolved against the cross-section's own trade date, which is
    the documented convention of the probe parser.
    """
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    reference = pd.Timestamp(trade_day)
    if len(digits) == 6:
        return digits
    if len(digits) != 4:
        return ""
    century = (reference.year // 100) * 100
    year = century + int(digits[:2])
    if year < reference.year - 5:
        year += 100
    return f"{year:04d}{digits[2:]}"


def months_between(near: str, far: str) -> int:
    """Whole months from ``near`` to ``far`` (both ``YYYYMM``)."""
    return (int(far[:4]) - int(near[:4])) * 12 + (int(far[4:6]) - int(near[4:6]))


def parse_cross_section(source: str, raw: bytes, day) -> pd.DataFrame:
    parser = PARSER_BY_SOURCE[source]
    if source == "CZCE":
        frame = parser(raw, reference=pd.Timestamp(day).date())
    else:
        frame = parser(raw)
    frame = frame.copy()
    frame["delivery"] = [normalize_delivery(value, day) for value in frame["delivery"]]
    frame = frame[frame["delivery"].str.len() == 6]
    return frame.reset_index(drop=True)


def load_product_data(
    universe: list[tuple[str, str]],
    calendar: pd.DatetimeIndex,
    cache_dir: Path | str | None = None,
) -> dict[str, dict[str, pd.DataFrame]]:
    """Read cached cross-sections into per-product (settle, open interest) panels.

    Each panel is indexed by ``calendar`` with one column per delivery month.
    Only the universe products of each venue are materialized.
    """
    codes_by_source: dict[str, list[str]] = {}
    for source, code in universe:
        codes_by_source.setdefault(source, []).append(code.upper())

    settle_maps: dict[str, dict] = {}
    oi_maps: dict[str, dict] = {}
    for source, codes in codes_by_source.items():
        for key in (f"{source}:{code}" for code in codes):
            settle_maps[key] = {}
            oi_maps[key] = {}
        for day in source_dates(source, calendar):
            path = cache_path(source, day, cache_dir)
            if not path.exists():
                continue
            try:
                frame = parse_cross_section(source, path.read_bytes(), day)
            except Exception:
                continue
            for code in codes:
                key = f"{source}:{code}"
                sub = frame[frame["product"] == code]
                if sub.empty:
                    continue
                trade_ymm = day.strftime("%Y%m")
                settle = {}
                oi = {}
                for delivery, settlement, open_interest in zip(
                    sub["delivery"], sub["settlement"], sub["open_interest"]
                ):
                    if delivery == trade_ymm:
                        continue
                    settle[str(delivery)] = float(settlement)
                    oi[str(delivery)] = float(open_interest)
                if settle:
                    settle_maps[key][day] = settle
                    oi_maps[key][day] = oi
    panels = {}
    for key in settle_maps:
        settle = pd.DataFrame.from_dict(settle_maps[key], orient="index").sort_index()
        oi = pd.DataFrame.from_dict(oi_maps[key], orient="index").sort_index()
        settle = settle.reindex(calendar)
        oi = oi.reindex(calendar).reindex(columns=settle.columns)
        panels[key] = {
            "settle": settle.apply(pd.to_numeric, errors="coerce").astype(float),
            "oi": oi.apply(pd.to_numeric, errors="coerce").astype(float),
        }
    return panels


def front_second(
    settle: pd.Series, oi: pd.Series, floor: float = OI_FLOOR
) -> tuple[str, str, float, float] | None:
    """Two nearest tradable contracts and their settlements.

    Tradable means settlement > 0 and open interest >= ``floor``.  Contracts
    whose delivery month equals the cross-section's month were already dropped
    during assembly.
    """
    usable = [
        (delivery, float(settle[delivery]))
        for delivery in settle.index
        if pd.notna(settle[delivery])
        and settle[delivery] > 0
        and pd.notna(oi.get(delivery))
        and float(oi.get(delivery)) >= floor
    ]
    usable.sort(key=lambda item: item[0])
    if len(usable) < 2:
        return None
    (front, front_settle), (second, second_settle) = usable[0], usable[1]
    if months_between(front, second) <= 0:
        return None
    return front, second, front_settle, second_settle


def term_panel(panel: dict[str, pd.DataFrame], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Per-day front/second contracts, front settlement and annualized slope."""
    settle, oi = panel["settle"], panel["oi"]
    rows = []
    for day in calendar:
        if day not in settle.index:
            rows.append((None, None, np.nan, np.nan))
            continue
        pick = front_second(settle.loc[day], oi.loc[day])
        if pick is None:
            rows.append((None, None, np.nan, np.nan))
            continue
        front, second, front_settle, second_settle = pick
        slope = math.log(front_settle / second_settle) * 12.0 / months_between(front, second)
        rows.append((front, second, front_settle, slope))
    term = pd.DataFrame(rows, index=calendar, columns=["front", "second", "front_settle", "slope"])
    term["active"] = term["slope"].notna()
    return term


def held_returns(
    panel: dict[str, pd.DataFrame], term: pd.DataFrame, calendar: pd.DatetimeIndex
) -> pd.DataFrame:
    """Roll-adjusted return of the contract held on each day, plus a roll flag.

    The contract held during day t is the front contract *known at t-1*, so the
    return is the price change of that same contract between t-1 and t.  A
    spliced front-series return would book the calendar spread as a price jump
    on every roll and double-count the very carry the signal trades.
    """
    settle = panel["settle"]
    front_known = term["front"].shift(1)
    returns = pd.Series(np.nan, index=calendar, dtype=float)
    rolls = pd.Series(0.0, index=calendar, dtype=float)
    previous_contract = None
    for i, day in enumerate(calendar):
        contract = front_known.iloc[i]
        if previous_contract is not None and contract != previous_contract:
            rolls.iloc[i] = 1.0
        previous_contract = contract
        if not isinstance(contract, str) or i == 0:
            continue
        prior_day = calendar[i - 1]
        if contract not in settle.columns:
            continue
        now = settle.at[day, contract] if day in settle.index else np.nan
        before = settle.at[prior_day, contract] if prior_day in settle.index else np.nan
        if pd.notna(now) and pd.notna(before) and before > 0:
            returns.iloc[i] = float(now / before - 1.0)
    return pd.DataFrame({"return": returns, "roll": rolls}, index=calendar)


# ---------------------------------------------------------------------------
# Signal, sizing and backtest
# ---------------------------------------------------------------------------


def cross_sectional_z(slope: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score of the slope across active products each day."""
    values = slope.to_numpy(dtype=float)
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
    return pd.DataFrame(z, index=slope.index, columns=slope.columns)


def signal_weights(
    z: pd.DataFrame, entry_z: float, exit_z: float, k: int, products: list[str] | None = None
) -> pd.DataFrame:
    """Hysteresis cross-sectional rank: long top-k / short bottom-k by z.

    Uses day-t information only and returns target weights for day t; the
    caller applies ``shift(1)`` before earning any return.  Weights are equal
    sized and gross-normalized to one across the open legs.
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
            elif state[product] == -1 and value >= -exit_z:
                new[product] = 0
            elif state[product] == 0:
                if value >= entry_z:
                    long_candidates.append((product, value))
                elif value <= -entry_z:
                    short_candidates.append((product, value))
        held_longs = [product for product in products if new[product] == 1]
        held_shorts = [product for product in products if new[product] == -1]
        for product, _ in sorted(long_candidates, key=lambda item: item[1], reverse=True):
            if len(held_longs) >= k:
                break
            new[product] = 1
            held_longs.append(product)
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


def backtest_metrics(
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    rolls: pd.DataFrame,
    side_bps: float = COST_ONE_WAY_BPS,
    roll_bps: float = ROLL_CROSS_BPS,
) -> dict:
    """Shift(1) the target weights, charge CNY turnover and roll-crossing costs."""
    shifted = weights.shift(1).fillna(0.0)
    gross = (shifted * returns).sum(axis=1)
    turnover = shifted.diff().abs().sum(axis=1)
    if len(turnover):
        turnover.iloc[0] = float(shifted.iloc[0].abs().sum())
    trade_cost = turnover * (side_bps / 1e4)
    roll_cost = (shifted.abs() * rolls).sum(axis=1) * (roll_bps / 1e4)
    net = (gross - trade_cost - roll_cost).fillna(0.0)
    equity = (1.0 + net).cumprod()
    trades = int((shifted.diff().abs().fillna(shifted.abs()) > 1e-12).sum().sum())
    return {
        "returns": net,
        "equity": equity,
        "trades": trades,
        "gross_returns": gross.fillna(0.0),
        "cost": (trade_cost + roll_cost).fillna(0.0),
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


# ---------------------------------------------------------------------------
# Portfolio construction helpers
# ---------------------------------------------------------------------------


def scaled_weights(
    slope: pd.DataFrame, params: dict, returns: pd.DataFrame, products: list[str]
) -> tuple[pd.DataFrame, pd.Series]:
    """Target weights and delever-only scale for one parameter combination."""
    z = cross_sectional_z(slope)
    weights = signal_weights(z, params["entry_z"], params["exit_z"], int(params["k"]), products)
    raw_port = (weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    scale = vol_scale(raw_port, float(params["vol_target"]))
    return weights.mul(scale, axis=0), scale


def walk_forward_score(
    slope: pd.DataFrame,
    params: dict,
    returns: pd.DataFrame,
    rolls: pd.DataFrame,
    products: list[str],
    train_index: pd.DatetimeIndex,
    n_folds: int = 4,
) -> float:
    """Mean contiguous-fold Sharpe on the train block (selection score only)."""
    if len(train_index) < 400:
        return -999.0
    weights, _ = scaled_weights(slope.loc[train_index], params, returns.loc[train_index], products)
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
            rolls.reindex(block).fillna(0.0),
        )
        sharpes.append(annualized_sharpe(result["returns"]))
    return float(np.mean(sharpes)) if sharpes else -999.0


def passive_long_weights(returns: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Passive front-month long book: equal weight across products with data."""
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
    slope: pd.DataFrame,
    selected: dict,
    returns: pd.DataFrame,
    rolls: pd.DataFrame,
    products: list[str],
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
        weights, _ = scaled_weights(slope, variant, returns, products)
        result = backtest_metrics(
            weights.reindex(oos_index).fillna(0.0),
            returns.reindex(oos_index).fillna(0.0),
            rolls.reindex(oos_index).fillna(0.0),
        )
        sharpes.append(annualized_sharpe(result["returns"]))
    return sharpes


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
    universe: list[tuple[str, str]] | None = None,
    workers: int = WORKERS,
    download_only: bool = False,
) -> dict:
    started = time.time()
    universe = universe or UNIVERSE
    calendar = pd.bdate_range(START, END)
    download_provenance = ensure_cached(universe, calendar, workers=workers)
    if download_only:
        print(json.dumps(download_provenance, indent=2))
        return download_provenance

    artifact = artifact_dir(out)
    products = [f"{source}:{code}" for source, code in universe]
    panels = load_product_data(universe, calendar)
    missing = [product for product in products if product not in panels]
    if missing:
        raise RuntimeError(f"no cached data for {missing}")

    terms = {product: term_panel(panels[product], calendar) for product in products}
    held = {
        product: held_returns(panels[product], terms[product], calendar) for product in products
    }
    slope = pd.DataFrame({product: terms[product]["slope"] for product in products}, index=calendar)
    returns = pd.DataFrame(
        {product: held[product]["return"] for product in products}, index=calendar
    )
    rolls = pd.DataFrame({product: held[product]["roll"] for product in products}, index=calendar)
    provenance = []
    for source, code in universe:
        key = f"{source}:{code}"
        active_days = int(terms[key]["active"].sum())
        observed = str(terms[key].index[terms[key]["active"]].min().date()) if active_days else ""
        declared = FIRST_DATE.get((source, code), "")
        provenance.append(
            {
                "source": source,
                "code": code,
                "key": key,
                "declared_first_date": declared,
                "observed_first_date": observed,
                "effective_first_date": max(declared, observed)
                if declared and observed
                else (declared or observed),
                "active_days": active_days,
                "cached_days": int(terms[key]["front"].notna().sum()),
            }
        )

    train_end = pd.Timestamp(TRAIN_END)
    val_end = pd.Timestamp(VAL_END)
    train_index = calendar[calendar <= train_end]
    val_index = calendar[(calendar > train_end) & (calendar <= val_end)]
    test_index = calendar[calendar > val_end]
    oos_index = calendar[calendar > train_end]

    grid_rows = []
    for params in iter_grid():
        score = walk_forward_score(slope, params, returns, rolls, products, train_index)
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

    weights, _ = scaled_weights(slope, selected, returns, products)
    full = backtest_metrics(weights, returns, rolls)
    train_result = backtest_metrics(
        weights.reindex(train_index).fillna(0.0),
        returns.reindex(train_index).fillna(0.0),
        rolls.reindex(train_index).fillna(0.0),
    )
    train_sharpe = annualized_sharpe(train_result["returns"])
    oos = backtest_metrics(
        weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        rolls.reindex(oos_index).fillna(0.0),
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
    bench_full = backtest_metrics(bench_sized, returns, rolls)
    bench_oos = backtest_metrics(
        bench_sized.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        rolls.reindex(oos_index).fillna(0.0),
    )
    bench_metrics = metrics(bench_oos["returns"], bench_oos["equity"], bench_oos["trades"])

    comparison = compare_to_benchmark(oos["returns"], bench_oos["returns"])
    p_value = float(comparison["alpha_p_value"])
    information_ratio = float(comparison["information_ratio"])

    random_target = random_weights(
        weights.reindex(oos_index).fillna(0.0), returns.reindex(oos_index)
    )
    random_result = backtest_metrics(
        random_target,
        returns.reindex(oos_index).fillna(0.0),
        rolls.reindex(oos_index).fillna(0.0),
    )
    random_metrics = metrics(
        random_result["returns"], random_result["equity"], random_result["trades"]
    )

    inverse_slope = -slope
    inverse_weights, _ = scaled_weights(inverse_slope, selected, returns, products)
    inverse_result = backtest_metrics(
        inverse_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        rolls.reindex(oos_index).fillna(0.0),
    )
    inverse_metrics = metrics(
        inverse_result["returns"], inverse_result["equity"], inverse_result["trades"]
    )

    perturbed = [
        value
        for value in perturbation_sharpes(slope, selected, returns, rolls, products, oos_index)
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
            "source": "SHFE/INE public settlement cross-sections (free/key-less/PIT)",
            "universe": [{"source": s, "code": c} for s, c in universe],
            "products": products,
            "start": START,
            "end": END,
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "train_rows": int(len(train_index)),
            "val_rows": int(len(val_index)),
            "test_rows": int(len(test_index)),
            "oos_rows": int(len(oos_index)),
            "calendar": "business days; 404 holidays/predating dates skipped",
            "download": download_provenance,
        },
        "provenance": provenance,
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
        "benchmark_passive_front_month_long_oos": bench_metrics,
        "benchmark_comparison": comparison,
        "ablations": {
            "random_ranking_oos": random_metrics,
            "inverse_slope_oos": inverse_metrics,
        },
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else str(wf_stability),
        "benchmark_pvalue_two_sided": p_value,
        "information_ratio_vs_passive_front_month": information_ratio,
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
            "roll_cross_bps": ROLL_CROSS_BPS,
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
    parser.add_argument("--workers", type=int, default=WORKERS, help="concurrent downloads")
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="populate the settlement cache and exit (resumable)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    arguments = _parse_args()
    main(arguments.out, workers=arguments.workers, download_only=arguments.download_only)
