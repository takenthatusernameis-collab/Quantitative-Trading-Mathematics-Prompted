"""NF-20261114-01 / H184 (Cycle 214): commodity term-structure carry.

Broad mechanism category: carry / commodity term structure (roll yield on
physically delivered futures).  Repo-new root family relative to executed
H1-H183: no executed H-ID trades the per-contract roll-yield slope; H23 tested
*directional* crypto TSMOM on perpetual futures (rejected) and H183 tested
delta-neutral funding carry (rejected) -- different instrument, signal, and
return source.  Parameter, timeframe, universe and market variations are
explicitly not new families; this is roll-yield capture on physically delivered
commodity futures, not perpetual funding accrual.

Mechanism.  Physically delivered futures embed inventory carry: a curve sloping
down (front above deferred, backwardation) pays a long position positive roll
yield as contracts age toward delivery; hedgers pay speculators to warehouse.
Null (H0): the front/second settlement slope known at day t's settle has no
predictive power for next-period roll-adjusted returns after CNY costs --
timing adds nothing over a passive front-month long book.

Observable / PIT timing.  SHFE/INE/CZCE/CFFEX publish official, key-less,
daily per-contract settlement cross-sections (static files; probe
`scripts/probe_commodity_termstructure_availability.py`, 4/4 sources usable,
exit 0, own run 2026-11-18).  Each file is the settlement record for trade
date t and is knowable at t's settle; the signal uses day-t settlements only
and positions are formed no earlier than t+1 (explicit `shift(1)`).  Coverage:
SHFE 2010-01-04 ->, INE from 2018-03-26, CZCE from 2015-12-01, CFFEX 2016->
2026; CNY-denominated, T+1, daily price limits; bounded first scope
2016-01-04 -> 2026-11-17.

Data reuse.  URL builders and parsers are imported from
`scripts/probe_commodity_termstructure_availability.py` (no forked copy).

Pre-registration (Cycle 214, before any forward-return inspection).
Universe: SHFE RB/CU/AL/ZN/AU/AG, INE SC (from 2018-03), optional CZCE
TA/MA/SR (from 2015-12), optional CFFEX IC/TF/T (from listing); each product
eligible from its first available date; contracts whose delivery month equals
the current month excluded.  Signal: annualized slope
ln(F1/F2)*12/months(F1,F2) from the two nearest contracts with settlement >
0 and open interest >= 100; cross-sectional rank long top-k / short bottom-k
equal weight; hysteresis on the cross-sectional spread z-score; train-only
4-fold walk-forward Sharpe selection.  Grid (bounded, 24):
entry_z {0.5,1.0,1.5} x exit_z {0.0,0.5} x k {1,3,5} x vol_target {0.10,0.15}.
Costs (CNY): 2 bps commission + 3 bps slippage per one-way side (5 bps
round-trip per leg), 1 bps roll crossing when the front contract changes;
T+1 and daily price limits are constraints.  Gates (OOS Val+Test, fail-closed,
standard 8): Sharpe>=1.0, trades>=50, PF>=1.3, maxDD<=15%, WF stability>=0.7,
worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05 with IR>=0 vs the
passive front-month long book, perturbation min ratio>=0.5.  Ablations:
passive front-month long book, random ranking (same active days, seed 42),
inverse-slope, OAT +/-20% perturbation.  Resumable on-disk cache under
`.cache/commodity_settlements/` (skip existing), one request per trade date per
venue, 404 holidays tolerated.  `src/qtr` unchanged; no gate weakening.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from probe_commodity_termstructure_availability import (
    fetch as probe_fetch,
)
from probe_commodity_termstructure_availability import (  # noqa: E402
    parse_cffex_csv,
    parse_exchange_json,
    parse_pipe_text,
    source_url,
)

from qtr.validation.statistics import benchmark_significance_gate

EXPERIMENT = "nf_20261114_01_commodity_termstructure_carry"
NF_ID = "NF-20261114-01"
HYPOTHESIS = "H184"

START = "2016-01-04"
END = "2026-11-17"
TRAIN_END = "2023-06-30"
VAL_END = "2024-12-31"

UNIVERSE = {
    "SHFE": ["RB", "CU", "AL", "ZN", "AU", "AG"],
    "INE": ["SC"],
    "CZCE": ["TA", "MA", "SR"],
    "CFFEX": ["IC", "TF", "T"],
}
ALL_PRODUCTS = sorted(product for products in UNIVERSE.values() for product in products)

COMMISSION_BPS = 2.0
SLIPPAGE_BPS = 3.0
ROLL_CROSS_BPS = 1.0
SIDE_BPS = COMMISSION_BPS + SLIPPAGE_BPS  # 5 bps per one-way side per leg
OPEN_INTEREST_FLOOR = 100.0
MAX_LEVERAGE = 10.0
DAYS_PER_YEAR = 252
SEED = 42
VOL_WINDOW = 21
SPREAD_Z_WINDOW = 63
SPREAD_Z_MIN_PERIODS = 21

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


def _cache_path(source: str, day) -> Path:
    return CACHE_DIR / source / f"{day:%Y%m%d}.dat"


def _fetch_cached(source: str, day, timeout: float = 30.0) -> tuple[bytes | None, str]:
    """Return (payload, status); status in {OK, MISSING, UNREACHABLE, UNPARSABLE}.

    Reads the on-disk cache first (resumable: skip existing files); otherwise
    downloads via the shared probe transport (one bounded retry).  404
    (holiday / pre-listing) is MISSING, not failure.
    """
    path = _cache_path(source, day)
    if path.exists():
        return path.read_bytes(), "OK"
    try:
        payload = probe_fetch(source, day, timeout=timeout)
    except Exception:
        return None, "UNREACHABLE"
    if payload is None:
        return None, "MISSING"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload, "OK"


def _parse_cross_section(source: str, raw: bytes, day) -> pd.DataFrame:
    parser = PARSER_BY_SOURCE[source]
    frame = parser(raw, reference=day) if source == "CZCE" else parser(raw)
    frame["date"] = pd.Timestamp(day)
    trade_month = day.strftime("%Y%m")
    frame = frame[frame["delivery"] != trade_month]  # exclude delivery window
    frame = frame[frame["product"].isin(UNIVERSE[source])]
    return frame.reset_index(drop=True)


def _one_date(source: str, day) -> tuple[list[dict], str]:
    payload, status = _fetch_cached(source, day)
    if payload is None:
        return [], status
    try:
        frame = _parse_cross_section(source, payload, day)
    except Exception:
        return [], "UNPARSABLE"
    return frame.to_dict("records"), status


def _download_universe() -> tuple[pd.DataFrame, dict[str, object]]:
    dates = pd.bdate_range(START, END)
    jobs = [(source, day) for source in UNIVERSE for day in dates]
    rows: list[dict] = []
    status_counts: dict[str, dict[str, int]] = {
        source: {"OK": 0, "MISSING": 0, "UNREACHABLE": 0, "UNPARSABLE": 0} for source in UNIVERSE
    }
    first_dates: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_one_date, source, day): (source, day) for source, day in jobs}
        for future in as_completed(futures):
            source, day = futures[future]
            record_rows, status = future.result()
            status_counts[source][status] += 1
            if status == "OK" and source not in first_dates:
                first_dates[source] = day.isoformat()
            rows.extend(record_rows)
    frame = pd.DataFrame(
        rows,
        columns=["date", "product", "delivery", "settlement", "open_interest"],
    )
    if len(frame):
        frame["date"] = pd.to_datetime(frame["date"])
        frame["settlement"] = pd.to_numeric(frame["settlement"], errors="coerce")
        frame["open_interest"] = pd.to_numeric(frame["open_interest"], errors="coerce")
        frame = frame.dropna(subset=["settlement"])
        frame = frame.sort_values(["date", "product", "delivery"]).reset_index(drop=True)
    provenance: dict[str, object] = {}
    for source in UNIVERSE:
        pattern = source_url(source, pd.Timestamp(START)).replace(
            pd.Timestamp(START).strftime("%Y%m%d"), "{YYYYMMDD}"
        )
        provenance[source] = {
            "url_pattern": pattern,
            "status_counts": status_counts[source],
            "first_usable_date": first_dates.get(source, ""),
        }
    return frame, provenance


def _delivery_to_month(delivery: str) -> int:
    """Convert delivery string (YYMM or YYYYMM) to total months since year 0."""
    s = str(delivery).strip()
    if len(s) == 6:
        year, month = int(s[:4]), int(s[4:])
    elif len(s) == 4:
        year, month = 2000 + int(s[:2]), int(s[2:])
    else:
        raise ValueError(f"unrecognized delivery format: {delivery!r}")
    return year * 12 + month


def _term_structure(frame: pd.DataFrame) -> pd.DataFrame:
    """Front/second settlement slope per product per trade date.

    Returns columns [date, product, front, second, front_settle,
    second_settle, front_oi, second_oi, slope] with slope annualized (decimal
    per year); only contracts with settlement > 0 and open interest >= floor.
    """
    records: list[dict] = []
    for (date, product), group in frame.groupby(["date", "product"], sort=False):
        group = group.sort_values("delivery")
        valid = group[(group["settlement"] > 0) & (group["open_interest"] >= OPEN_INTEREST_FLOOR)]
        if len(valid) < 2:
            continue
        front_row, second_row = valid.iloc[0], valid.iloc[1]
        front = str(front_row["delivery"])
        second = str(second_row["delivery"])
        s1 = float(front_row["settlement"])
        s2 = float(second_row["settlement"])
        m1 = _delivery_to_month(front)
        m2 = _delivery_to_month(second)
        months = m2 - m1
        if months <= 0 or s2 <= 0:
            continue
        slope = math.log(s1 / s2) * 12.0 / months
        records.append(
            {
                "date": date,
                "product": product,
                "front": front,
                "second": second,
                "front_settle": s1,
                "second_settle": s2,
                "front_oi": float(front_row["open_interest"]),
                "second_oi": float(second_row["open_interest"]),
                "slope": float(slope),
            }
        )
    columns = [
        "date",
        "product",
        "front",
        "second",
        "front_settle",
        "second_settle",
        "front_oi",
        "second_oi",
        "slope",
    ]
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(records).sort_values(["date", "product"]).reset_index(drop=True)


def _signal_frame(
    term: pd.DataFrame, dates: pd.DatetimeIndex, products: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Pivot slope, front settlement and front delivery into date x product frames."""
    slope = term.pivot_table(index="date", columns="product", values="slope", aggfunc="first")
    front_settle = term.pivot_table(
        index="date", columns="product", values="front_settle", aggfunc="first"
    )
    front_delivery = term.pivot_table(
        index="date", columns="product", values="front", aggfunc="first"
    )
    return (
        slope.reindex(index=dates, columns=products),
        front_settle.reindex(index=dates, columns=products),
        front_delivery.reindex(index=dates, columns=products),
    )


def _cross_sectional_signal(
    slope: pd.DataFrame,
    k: int,
    entry_z: float,
    exit_z: float,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Rank signal with hysteresis on the cross-sectional spread z-score.

    Long the top-k by slope, short the bottom-k, equal weight; the whole book
    is gated by hysteresis on spread_z (fixed trailing 63-day mean/std, not
    tuned).  Returns (signal, spread, spread_z).
    """
    n_valid = slope.notna().sum(axis=1)
    desc_rank = slope.rank(axis=1, ascending=False, method="min")
    long_mask = desc_rank <= k
    threshold = (n_valid - k + 1).values[:, None]
    short_mask = pd.DataFrame(
        (desc_rank.values >= threshold) & ((n_valid >= 2 * k).values[:, None]),
        index=slope.index,
        columns=slope.columns,
    )
    signal = pd.DataFrame(0.0, index=slope.index, columns=slope.columns, dtype=float)
    signal[long_mask] = 1.0 / k
    signal[short_mask] = -1.0 / k
    signal = signal.where(n_valid.ge(2 * k), 0.0)

    long_slope = slope.where(long_mask).mean(axis=1)
    short_slope = slope.where(short_mask).mean(axis=1)
    spread = (long_slope - short_slope).where(n_valid >= 2 * k)
    ma = spread.rolling(SPREAD_Z_WINDOW, min_periods=SPREAD_Z_MIN_PERIODS).mean()
    ms = spread.rolling(SPREAD_Z_WINDOW, min_periods=SPREAD_Z_MIN_PERIODS).std(ddof=0)
    spread_z = (spread - ma) / ms

    active = pd.Series(False, index=slope.index, dtype=bool)
    state = False
    loc = {date: i for i, date in enumerate(slope.index)}
    for date in slope.index:
        value = spread_z.iloc[loc[date]]
        if pd.isna(value):
            active.iloc[loc[date]] = state
            continue
        if not state and value >= entry_z:
            state = True
        elif state and value <= exit_z:
            state = False
        active.iloc[loc[date]] = state
    gated = signal.mul(active, axis=0)
    return gated, spread, spread_z


def _vol_scale(signal: pd.DataFrame, returns: pd.DataFrame, vol_target: float) -> pd.Series:
    """Trailing realized vol of the gated signal book; scale = target / vol."""
    basket = (signal * returns).sum(axis=1, min_count=1).fillna(0.0)
    vol_ann = basket.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=0) * math.sqrt(
        DAYS_PER_YEAR
    )
    scale = vol_target / vol_ann.replace(0.0, np.nan)
    scale = scale.replace([np.inf, -np.inf], np.nan).clip(upper=MAX_LEVERAGE)
    return scale


def _front_returns(
    front_settle: pd.DataFrame, front_delivery: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Daily front-contract settlement returns and front-change flags."""
    returns = front_settle.pct_change()
    prev = front_delivery.shift(1)
    changed = front_delivery.ne(prev) & prev.notna()
    return returns, changed


def _execute(
    signal: pd.DataFrame,
    scale: pd.Series,
    returns: pd.DataFrame,
    changed: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.DataFrame]:
    """Shift signal by one bar (trade t+1 on day-t info), scale, cost.

    executed[t] holds the position formed at close t-1 and earns returns[t].
    """
    executed = signal.mul(scale, axis=0).shift(1).fillna(0.0)
    gross = executed.abs().sum(axis=1)
    over = gross > 1.0
    if over.any():
        executed.loc[over] = executed.loc[over].div(gross[over], axis=0)
    turnover = executed.diff().abs().sum(axis=1)
    turnover.iloc[0] = executed.iloc[0].abs().sum()
    trade_cost = turnover * (SIDE_BPS / 1e4)
    prev_position = executed.shift(1).abs()
    roll_flag = changed.fillna(False) & (prev_position > 0)
    roll_cost = roll_flag.mul(prev_position, axis=0).sum(axis=1) * (ROLL_CROSS_BPS / 1e4)
    gross_ret = (executed * returns).sum(axis=1, min_count=1)
    strat = (gross_ret - trade_cost - roll_cost).fillna(0.0)
    equity = (1.0 + strat).cumprod()
    trades = int((executed.diff().abs().fillna(executed.abs()) > 1e-12).sum().sum())
    return strat, equity, trade_cost + roll_cost, executed


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
    gains = float(values[values > 0].sum())
    losses = -float(values[values < 0].sum())
    if losses <= 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


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


def _backtest(
    signal: pd.DataFrame,
    scale: pd.Series,
    returns: pd.DataFrame,
    changed: pd.DataFrame,
    index: pd.DatetimeIndex,
) -> dict:
    """Run the executed book over ``index``; returns metrics plus ledgers."""
    signal = signal.reindex(index)
    scale = scale.reindex(index)
    returns = returns.reindex(index)
    changed = changed.reindex(index)
    strat, equity, cost, executed = _execute(signal, scale, returns, changed)
    strat = strat.reindex(index).fillna(0.0)
    equity = equity.reindex(index)
    out = _metrics(strat, equity, trades=0)
    out["trades"] = int((executed.diff().abs().fillna(executed.abs()) > 1e-12).sum().sum())
    out["equity"] = equity
    out["returns"] = strat
    out["executed"] = executed
    out["cost_bps_sum"] = float(cost.sum() * 1e4)
    return out


def _wf_score(
    signal: pd.DataFrame,
    scale: pd.Series,
    returns: pd.DataFrame,
    changed: pd.DataFrame,
    train: pd.DatetimeIndex,
    n_folds: int = 4,
) -> float:
    """Mean train-only fold Sharpe; weights are a pure function of params/data."""
    if len(train) < 400:
        return -999.0
    fold = len(train) // n_folds
    sharpes = []
    for i in range(n_folds):
        stop = len(train) if i == n_folds - 1 else (i + 1) * fold
        block = train[i * fold : stop]
        if len(block) < 120:
            continue
        bt = _backtest(signal, scale, returns, changed, block)
        sharpes.append(bt["sharpe"])
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
    slope: pd.DataFrame,
    returns: pd.DataFrame,
    changed: pd.DataFrame,
    index: pd.DatetimeIndex,
    selected: dict,
) -> list[float]:
    """One-at-a-time +/-20% perturbation of entry_z / exit_z / vol_target on OOS."""
    base = {
        "entry_z": selected["entry_z"],
        "exit_z": selected["exit_z"],
        "k": selected["k"],
        "vol_target": selected["vol_target"],
    }
    candidates = {
        "entry_z": sorted(
            {
                round(base["entry_z"] * 0.8, 6),
                base["entry_z"],
                round(base["entry_z"] * 1.2, 6),
            }
        ),
        "exit_z": sorted(
            {
                round(base["exit_z"] * 0.8, 6),
                base["exit_z"],
                round(base["exit_z"] * 1.2, 6),
            }
        ),
        "vol_target": sorted(
            {
                round(base["vol_target"] * 0.8, 6),
                base["vol_target"],
                round(base["vol_target"] * 1.2, 6),
            }
        ),
    }
    sharpes = []
    for param, values in candidates.items():
        for value in values:
            if value == base[param]:
                continue
            params = dict(base)
            params[param] = float(value)
            if params["exit_z"] > params["entry_z"]:
                params["exit_z"] = params["entry_z"]
            signal, _, _ = _cross_sectional_signal(
                slope, int(params["k"]), params["entry_z"], params["exit_z"]
            )
            scale = _vol_scale(signal, returns, params["vol_target"])
            bt = _backtest(signal, scale, returns, changed, index)
            sharpes.append(bt["sharpe"])
    return [value for value in sharpes if np.isfinite(value)]


def _iter_grid():
    for entry_z in GRID["entry_z"]:
        for exit_z in GRID["exit_z"]:
            if exit_z > entry_z:
                continue
            for k in GRID["k"]:
                for vol_target in GRID["vol_target"]:
                    yield {
                        "entry_z": float(entry_z),
                        "exit_z": float(exit_z),
                        "k": int(k),
                        "vol_target": float(vol_target),
                    }


def _benchmark_weights(front_settle: pd.DataFrame) -> pd.DataFrame:
    """Passive front-month long book: equal weight across valid front contracts."""
    valid = front_settle.notna()
    weights = valid.div(valid.sum(axis=1), axis=0).fillna(0.0)
    return weights.fillna(0.0)


def main(out: str | None = None) -> dict:
    started = time.time()
    artifact = (
        Path(out).resolve()
        if out
        else (
            Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{time.strftime('%Y%m%d_%H%M%S')}"
        ).resolve()
    )
    artifact.mkdir(parents=True, exist_ok=True)

    frame, provenance = _download_universe()
    dates = pd.bdate_range(START, END)
    products = ALL_PRODUCTS

    term = _term_structure(frame)
    slope, front_settle, front_delivery = _signal_frame(term, dates, products)
    returns, changed = _front_returns(front_settle, front_delivery)

    train = dates[dates <= pd.Timestamp(TRAIN_END)]
    val = dates[(dates > pd.Timestamp(TRAIN_END)) & (dates <= pd.Timestamp(VAL_END))]
    test = dates[dates > pd.Timestamp(VAL_END)]
    oos = dates[dates > pd.Timestamp(TRAIN_END)]

    rows = []
    signals: dict[str, pd.DataFrame] = {}
    scales: dict[str, pd.Series] = {}
    for params in _iter_grid():
        key = json.dumps(params, sort_keys=True)
        signal, _, _ = _cross_sectional_signal(
            slope, int(params["k"]), params["entry_z"], params["exit_z"]
        )
        scale = _vol_scale(signal, returns, params["vol_target"])
        signals[key] = signal
        scales[key] = scale
        wf = _wf_score(signal, scale, returns, changed, train)
        train_bt = _backtest(signal, scale, returns, changed, train)
        rows.append({**params, "wf_train_sharpe": wf, "train_sharpe": train_bt["sharpe"]})
    grid = pd.DataFrame(rows).sort_values(["wf_train_sharpe", "train_sharpe"], ascending=False)
    grid.to_csv(artifact / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows")
    best = valid.iloc[0].to_dict()
    selected = {
        "entry_z": float(best["entry_z"]),
        "exit_z": float(best["exit_z"]),
        "k": int(best["k"]),
        "vol_target": float(best["vol_target"]),
    }
    key = json.dumps(selected, sort_keys=True)
    signal = signals[key]
    scale = scales[key]

    oos_bt = _backtest(signal, scale, returns, changed, oos)
    oos_executed = oos_bt["executed"].reindex(oos)
    oos_metrics = {k_: v for k_, v in oos_bt.items() if k_ not in ("equity", "returns", "executed")}

    train_bt = _backtest(signal, scale, returns, changed, train)
    train_sharpe = train_bt["sharpe"]
    wf_stability = (
        float(oos_metrics["sharpe"] / train_sharpe)
        if np.isfinite(train_sharpe) and train_sharpe != 0
        else (float("inf") if oos_metrics["sharpe"] > 0 else 0.0)
    )

    # Passive front-month long benchmark (same cost model, no vol target, no gate).
    bench_w = _benchmark_weights(front_settle)
    bench_scale = pd.Series(1.0, index=dates)
    bench_bt = _backtest(bench_w, bench_scale, returns, changed, oos)
    bench_metrics = {
        k_: v for k_, v in bench_bt.items() if k_ not in ("equity", "returns", "executed")
    }

    # Random ranking control: same active days as the selected book, random
    # long/short assignment among valid products, seed 42.
    k = selected["k"]
    valid_daily = slope.notna() & (slope.notna().sum(axis=1) >= 2 * k)
    rng = np.random.default_rng(SEED)
    active_dates = oos[oos_executed.abs().sum(axis=1) > 0]
    random_signal = pd.DataFrame(0.0, index=oos, columns=products, dtype=float)
    for date in active_dates:
        valid_products = [p for p in products if valid_daily.loc[date, p]]
        if len(valid_products) < 2 * k:
            continue
        choice = rng.choice(valid_products, size=2 * k, replace=False)
        random_signal.loc[date, choice[:k]] = 1.0 / k
        random_signal.loc[date, choice[k:]] = -1.0 / k
    random_bt = _backtest(
        random_signal.reindex(dates),
        scale.reindex(dates),
        returns,
        changed,
        oos,
    )
    random_metrics = {
        k_: v for k_, v in random_bt.items() if k_ not in ("equity", "returns", "executed")
    }

    # Inverse-slope ablation: same parameters, rankings flipped.
    inverse_signal, _, _ = _cross_sectional_signal(
        -slope, int(selected["k"]), selected["entry_z"], selected["exit_z"]
    )
    inverse_scale = _vol_scale(inverse_signal, returns, selected["vol_target"])
    inverse_bt = _backtest(inverse_signal, inverse_scale, returns, changed, oos)
    inverse_metrics = {
        k_: v for k_, v in inverse_bt.items() if k_ not in ("equity", "returns", "executed")
    }

    perturbed = _perturbation_oos_sharpes(
        slope.reindex(oos),
        returns.reindex(oos),
        changed.reindex(oos),
        oos,
        selected,
    )
    base_sharpe = oos_metrics["sharpe"]
    min_ratio = (
        float(min(perturbed) / base_sharpe)
        if perturbed and np.isfinite(base_sharpe) and base_sharpe != 0
        else 0.0
    )

    oos_ret = oos_bt["returns"].reindex(oos).fillna(0.0)
    bench_ret = bench_bt["returns"].reindex(oos).fillna(0.0)
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
            "source": "SHFE/INE/CZCE/CFFEX public settlement cross-sections, free/key-less/PIT",
            "universe": UNIVERSE,
            "products": products,
            "start": START,
            "end": END,
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "train_rows": int(len(train)),
            "val_rows": int(len(val)),
            "test_rows": int(len(test)),
            "oos_rows": int(len(oos)),
            "provenance": provenance,
        },
        "grid_size": int(len(grid)),
        "selected": selected,
        "wf_train_sharpe": float(best["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sharpe),
        "oos_val_test": oos_metrics,
        "benchmark_front_month_long_oos": bench_metrics,
        "ablations": {
            "random_ranking_oos": random_metrics,
            "inverse_slope_oos": inverse_metrics,
        },
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else wf_stability,
        "benchmark_pvalue_one_sided": float(p_value),
        "information_ratio_vs_front_month_long": float(ir),
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
            "cost_bps_per_side": SIDE_BPS,
            "roll_cross_bps": ROLL_CROSS_BPS,
            "open_interest_floor": OPEN_INTEREST_FLOOR,
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
