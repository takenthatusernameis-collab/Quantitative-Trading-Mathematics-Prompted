"""NF-20261122-03 / H198 (Cycle 265 pre-registration and execution).

Broad mechanism category: index-membership discrete-event price pressure
(stock-level demand/supply shock at S&P 500 reconstitution). Repo-new root
family relative to executed H1-H197: no executed H-ID trades the discrete,
date-stamped event of S&P 500 index inclusion/deletion. The closest prior
families are the continuous equity cross-sections H187-H197 (accruals,
issuance, valuation, innovation, beta, coskewness, price delay, turnover,
capital structure) and the event-adjacent calendar studies (turn-of-month,
FOMC drift, index rebalance). A membership-event book trades a discrete
reconstitution event rather than a continuous characteristic sort; per
directive sec. 6 that is a distinct return-generating mechanism (index-fund
demand/supply pressure), not a parameter/universe/timeframe variant.

Mechanism / causal chain.  Index funds and ETFs tracking the S&P 500 must buy
names added at the effective date and sell names removed, creating temporary
price pressure. Added names subsequently drift up (continued index-fund buying
plus positive attention) and removed names drift down (forced selling plus
negative attention); the effect concentrates around the effective date and
decays over the following weeks (Shleifer 1986; Harris & Gurel 1986; Chen,
Noronha & Singal 2005; Wurgler & Zhuravskaya 2002). Prediction (directional):
**long announced additions / short announced deletions (tradeable removals)
around the effective date, held 1-3 months.** Null (H0): the index-membership
event carries no post-effective-date drift after costs -- a
long-additions/short-removals event book adds nothing over a passive
equal-weight book of the same universe.

Data and PIT timing.  Free PIT event calendar: the Wikipedia "Historical
components of the S&P 500" changes table (effective date, added/removed
ticker, stated reason). Prices: yfinance daily auto-adjusted Close. Measured
price-leg coverage (Cycle 265, population-level, retry-aware): added 284/370 =
76.8% with data (282/370 = 76.2% covering the event); tradeable-by-construction
removed (market_cap / spin_off / reorganization) 104/169 = 61.5% with data and
covering the event. Binding coverage = min(added, tradeable-removed) = 61.5%
>= 60% threshold -> price leg FEASIBLE (supersedes the Cycle 256 20-name
"blocked" claim, which was dominated by acquisition/bankruptcy delistings and
un-retried transient empties). Each event enters the book on its effective
date t (or t+1 trading day, a grid dimension); the shared engine applies
``shift(1)``, so the position earns returns t -> t+1. No announcement-date
lookahead: only the effective date and the stated reason (both in the
historical table) are used. Prices are calendar-aligned ffilled closes before
``pct_change`` (the H191 convention). Removed names are restricted to
tradeable-by-construction reasons (market_cap / spin_off / reorganization);
acquisition/bankruptcy deletions are delisted at the event by construction and
are not shortable candidates.

Pre-registration (Cycle 265, written before any forward-return outcome was
computed).  Sample 2005-01-01 -> 2026-11-21; Train -> 2021-12-31; Val
2022-01-01 -> 2023-12-31; Test protected 2024-01-01 -> 2026-11-21. Universe:
all added tickers and all tradeable-by-construction removed tickers with a
valid effective date in [2005, 2026] and a yfinance price series covering the
+/-252-trading-day event window. Event basket: long = added name(s), short =
tradeable removed name(s); each open event basket is dollar-neutral and
gross-normalized across simultaneously open baskets (sum |w| = 1, rebalanced
daily to the open set). Grid (bounded, 12): holding_days {21, 42, 63} x
entry_delay {0, 1} x vol_target {0.10, 0.15}; train-only 4-fold walk-forward
Sharpe selection. Costs: 5 bps one-way per leg traded; no short borrow cost
modelled (disclosed optimistic). Coverage is a survivorship-biased subset:
excluded added names (mostly later delisted) bias the long leg upward;
excluded removed names (mostly later bankrupt) bias the short leg downward --
disclosed, and the long-only ablation isolates the long leg.

Gates (OOS Val+Test, fail-closed, standard 8, unchanged from H187/H190-H197):
Sharpe >= 1.0; trades >= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7;
worst-regime rolling-252 Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with
IR >= 0 vs the passive equal-weight long book of the same universe; OAT +/-20%
perturbation min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random event signs (same
open legs, seed 42); inverse event (short additions / long removals);
long-only additions (short leg removed); event-count / coverage diagnostics.

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors and primitives from run_nf_20261120_01_equity_accruals.py
(H187), which exposes run_nf_20261119_02_commodity_hedging_pressure.py (H186)
and run_nf_20261114_01_commodity_termstructure_carry.py (H184). The changes
table is parsed with scripts/probe_sp500_membership_priceleg.py (the Cycle 256
free-data probe). Only the event-list construction and the event-basket
weights are new code. Free/public real data only (Wikipedia changes table +
yfinance daily auto-adjusted Close); ``src/qtr`` unchanged. Artifact under
.experiments/nf_runs/nf_20261122_03_sp500_membership_event_drift_<timestamp>/
summary.json + grid.csv + data_meta.json.
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

# Import shared primitives from H187 (equity accruals), which exposes H184.
_H187_PATH = ROOT / "run_nf_20261120_01_equity_accruals.py"
_h187_spec = importlib.util.spec_from_file_location("h187_accruals", _H187_PATH)
assert _h187_spec is not None and _h187_spec.loader is not None
h187 = importlib.util.module_from_spec(_h187_spec)  # type: ignore[arg-type]
sys.modules[_h187_spec.name] = h187
_h187_spec.loader.exec_module(h187)
h184 = h187.h184

# Import the S&P 500 changes-table parser from the Cycle 256 free-data probe.
_PROBE_PATH = ROOT / "scripts" / "probe_sp500_membership_priceleg.py"
_probe_spec = importlib.util.spec_from_file_location("sp500_priceleg_probe", _PROBE_PATH)
assert _probe_spec is not None and _probe_spec.loader is not None
probe = importlib.util.module_from_spec(_probe_spec)  # type: ignore[arg-type]
sys.modules[_probe_spec.name] = probe
_probe_spec.loader.exec_module(probe)

EXPERIMENT = "nf_20261122_03_sp500_membership_event_drift"
NF_ID = "NF-20261122-03"
HYPOTHESIS = "H198"

START = "2005-01-01"
END = "2026-11-21"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

COST_ONE_WAY_BPS = 5.0
SEED = 42
VOL_LOOKBACK = 60
DAYS_PER_YEAR = 252
MIN_EVENTS = 30
MIN_PRICE_OBSERVATIONS = 126
EVENT_WINDOW_DAYS = 252
MIN_YEAR = 2005
MAX_YEAR = 2026
TRADEABLE_REMOVED_BUCKETS = ("market_cap", "spin_off", "reorganization")

GATES = dict(h184.GATES)

GRID = {
    "holding_days": [21, 42, 63],
    "entry_delay": [0, 1],
    "vol_target": [0.10, 0.15],
}

CACHE_DIR = Path(".cache") / "sp500"


# ---------------------------------------------------------------------------
# Event calendar: Wikipedia changes table -> list of membership events
# ---------------------------------------------------------------------------


def cache_dir_for(cache_dir: Path | str | None = None) -> Path:
    return Path(cache_dir) if cache_dir is not None else CACHE_DIR


def _clean_ticker(value: object) -> str:
    """Normalise a changes-table ticker cell (NaN/None/whitespace/stray pipes)."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if "|" in text:
        text = text.split("|")[0].strip()
    return text


def load_changes_frame(
    fetch_fn=None,
    cache_dir: Path | str | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load the Wikipedia changes table (cached CSV; parsed once per refresh).

    The cached CSV is the reproducible artifact: the event calendar is fetched
    from the free Wikipedia table only when the cache is missing or ``refresh``
    is set, and the parsed frame (effective_date, added/removed ticker, reason,
    reason_bucket) is what the runner reads afterwards.
    """
    path = cache_dir_for(cache_dir) / "membership_changes.csv"
    if path.exists() and not refresh:
        frame = pd.read_csv(path, parse_dates=["effective_date"])
        if "reason_bucket" not in frame.columns:
            frame["reason_bucket"] = frame["reason"].map(probe.classify_reason)
        return frame
    frame = probe.fetch_changes_table(fetch_fn=fetch_fn)
    frame["reason_bucket"] = frame["reason"].map(probe.classify_reason)
    cache_dir_for(cache_dir).mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def build_event_list(
    frame: pd.DataFrame,
    min_year: int = MIN_YEAR,
    max_year: int = MAX_YEAR,
) -> list[dict]:
    """One dict per changes-table row with a usable added and/or tradeable removed leg.

    ``removed_ticker`` is kept only when its stated reason is tradeable by
    construction (market_cap / spin_off / reorganization); acquisition and
    bankruptcy deletions are delisted at the event and cannot be shorted.
    """
    frame = frame[frame["effective_date"].dt.year.between(min_year, max_year)].copy()
    events: list[dict] = []
    for _, row in frame.iterrows():
        added = _clean_ticker(row.get("added_ticker"))
        removed = _clean_ticker(row.get("removed_ticker"))
        bucket = row.get("reason_bucket")
        short_ok = bool(removed) and bucket in TRADEABLE_REMOVED_BUCKETS
        if not added and not short_ok:
            continue
        events.append(
            {
                "event_date": row["effective_date"].date(),
                "added_ticker": added or None,
                "removed_ticker": removed if short_ok else None,
                "removed_reason_bucket": bucket if short_ok else None,
            }
        )
    events.sort(key=lambda event: event["event_date"])
    return events


def event_tickers(events: list[dict]) -> list[str]:
    """Sorted union of every added / tradeable-removed ticker in the event list."""
    tickers: set[str] = set()
    for event in events:
        if event["added_ticker"]:
            tickers.add(event["added_ticker"])
        if event["removed_ticker"]:
            tickers.add(event["removed_ticker"])
    return sorted(tickers)


# ---------------------------------------------------------------------------
# Price data: retry-aware yfinance closes for the event universe
# ---------------------------------------------------------------------------


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
        # yfinance returns flat columns for some versions and a MultiIndex
        # (field, ticker) for others; normalise to a single Close series.
        if "Close" in frame.columns:
            close = frame["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
        else:
            close = frame.iloc[:, 0]
        return close.astype(float), None, attempt, 0
    return None, (last_error or "no attempt executed")[:120], max_attempts, max_attempts


def load_event_closes(
    tickers: list[str],
    start: str = START,
    end: str = END,
    cache_dir: Path | str | None = None,
    refresh: bool = False,
    max_attempts: int = 2,
    throttle_s: float = 0.25,
    verbose: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Download (or load cached) daily closes for the event universe.

    Returns ``(closes, coverage)`` where ``closes`` is a date x ticker panel of
    raw (unadjusted) yfinance closes and ``coverage`` records, per ticker,
    whether a series was returned and its span. Cached to
    ``<cache>/event_closes.parquet`` + ``<cache>/event_coverage.json``.
    """
    cache_dir = cache_dir_for(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / "event_closes.parquet"
    coverage_path = cache_dir / "event_coverage.json"
    if path.exists() and coverage_path.exists() and not refresh:
        closes = pd.read_parquet(path)
        coverage = json.loads(coverage_path.read_text())
        missing = [ticker for ticker in tickers if ticker not in closes.columns]
        if not missing:
            return closes, coverage

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
        if verbose and index % 50 == 0:
            usable = sum(1 for row in coverage.values() if row["has_data"])
            print(f"  {index}/{len(tickers)} tickers, {usable} with data", flush=True)
        # Per-ticker throttle: free quote APIs rate-limit tight request loops
        # (a burst returns empty frames for live tickers; the Cycle 256 probe
        # documented the same transient-empty class).
        time.sleep(throttle_s * 0.6)

    if not series:
        raise RuntimeError(
            "no event ticker returned a price series; check network access / quote-API rate limits"
        )
    closes = pd.DataFrame(series).sort_index()
    closes.to_parquet(path)
    coverage_path.write_text(json.dumps(coverage, indent=2) + "\n")
    return closes, coverage


def returns_from_closes(closes: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Calendar-align ffilled closes then pct_change (the H191 convention)."""
    aligned = closes.reindex(calendar).ffill()
    returns = aligned.pct_change(fill_method=None)
    return returns.where(np.isfinite(returns))


def event_usable(
    closes: pd.DataFrame,
    ticker: str,
    event_date,
    window_days: int = EVENT_WINDOW_DAYS,
    min_observations: int = MIN_PRICE_OBSERVATIONS,
) -> bool:
    """True when the ticker has enough finite closes at/before the event date."""
    if ticker not in closes.columns:
        return False
    series = closes[ticker]
    hi = pd.Timestamp(event_date)
    lo = hi - pd.Timedelta(days=int(window_days * 1.6))
    window = series.loc[lo:hi].dropna()
    return bool(len(window) >= min_observations)


# ---------------------------------------------------------------------------
# Event-basket weights (the only new portfolio construction)
# ---------------------------------------------------------------------------


def build_event_weights(
    events: list[dict],
    closes: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    holding_days: int,
    entry_delay: int = 0,
) -> pd.DataFrame:
    """Daily target weights for the index-membership event book.

    Each event with a usable price series opens ``entry_delay`` trading days
    after its effective date and is held for ``holding_days`` trading days.
    At each day the set of open events is re-collected; each open event's
    basket (long added names, short tradeable removed names) receives total
    absolute weight ``1 / n_open``, split equally between the long and short
    sides. Weights are gross-normalized to one across all open baskets
    (``sum |w| = 1``), and the engine applies ``shift(1)`` before any return
    is earned.
    """
    products = list(closes.columns)
    weights = pd.DataFrame(0.0, index=calendar, columns=products, dtype=float)
    positions = {timestamp: index for index, timestamp in enumerate(calendar)}

    baskets: list[tuple[int, int, list[str], list[str]]] = []
    for event in events:
        event_date = pd.Timestamp(event["event_date"])
        if event_date not in positions:
            next_index = int(calendar.searchsorted(event_date))
            if next_index >= len(calendar):
                continue
            event_date = calendar[next_index]
        entry_index = positions[event_date]
        entry_pos = entry_index + int(entry_delay)
        exit_pos = entry_pos + int(holding_days)
        if entry_pos >= len(calendar):
            continue
        longs = []
        if event["added_ticker"] and event_usable(
            closes, event["added_ticker"], event["event_date"]
        ):
            longs.append(event["added_ticker"])
        shorts = []
        if event["removed_ticker"] and event_usable(
            closes, event["removed_ticker"], event["event_date"]
        ):
            shorts.append(event["removed_ticker"])
        if not longs and not shorts:
            continue
        baskets.append((entry_pos, min(exit_pos, len(calendar)), longs, shorts))

    for day in range(len(calendar)):
        open_baskets = [basket for basket in baskets if basket[0] <= day < basket[1]]
        n_open = len(open_baskets)
        if n_open == 0:
            continue
        basket_total = 1.0 / n_open
        for _, _, longs, shorts in open_baskets:
            sides: list[tuple[float, list[str]]] = []
            if longs:
                sides.append((1.0, longs))
            if shorts:
                sides.append((-1.0, shorts))
            for sign, names in sides:
                per_name = (basket_total / len(sides)) / len(names)
                for name in names:
                    weights.iat[day, weights.columns.get_loc(name)] += sign * per_name
    return weights


def long_only_events(events: list[dict]) -> list[dict]:
    """Events with the short leg removed (long-additions-only ablation)."""
    return [{**event, "removed_ticker": None} for event in events]


def scaled_event_weights(
    weights: pd.DataFrame, returns: pd.DataFrame, vol_target: float
) -> pd.DataFrame:
    """Delever-only vol scaling of the event book (same convention as H184)."""
    raw = (weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    scale = h184.vol_scale(raw, vol_target)
    return weights.mul(scale, axis=0)


def zero_rolls(index: pd.DatetimeIndex, products: list[str]) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=index, columns=products, dtype=float)


# ---------------------------------------------------------------------------
# Grid search / walk-forward selection
# ---------------------------------------------------------------------------


def iter_grid():
    for holding_days in GRID["holding_days"]:
        for entry_delay in GRID["entry_delay"]:
            for vol_target in GRID["vol_target"]:
                yield {
                    "holding_days": int(holding_days),
                    "entry_delay": int(entry_delay),
                    "vol_target": float(vol_target),
                }


def event_walk_forward_score(
    events: list[dict],
    closes: pd.DataFrame,
    returns: pd.DataFrame,
    products: list[str],
    train_index: pd.DatetimeIndex,
    params: dict,
    n_folds: int = 4,
) -> float:
    """Mean contiguous-fold Sharpe on the train block (selection score only)."""
    if len(train_index) < 400:
        return -999.0
    weights = build_event_weights(
        events,
        closes,
        train_index,
        int(params["holding_days"]),
        int(params["entry_delay"]),
    )
    weights = scaled_event_weights(
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
    events: list[dict],
    closes: pd.DataFrame,
    returns: pd.DataFrame,
    products: list[str],
    selected: dict,
    oos_index: pd.DatetimeIndex,
) -> list[float]:
    """OAT +/-20% perturbation of holding_days, entry_delay and vol_target on OOS."""
    variants = []
    for factor in (0.8, 1.2):
        for param in ("holding_days", "vol_target"):
            variant = dict(selected)
            variant[param] = round(float(selected[param]) * factor, 6)
            variants.append(variant)
    for delta in (-1, 1):
        variant = dict(selected)
        variant["entry_delay"] = max(0, int(selected["entry_delay"]) + delta)
        variants.append(variant)

    out: list[float] = []
    for variant in variants:
        weights = build_event_weights(
            events,
            closes,
            oos_index,
            int(variant["holding_days"]),
            int(variant["entry_delay"]),
        )
        weights = scaled_event_weights(
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

    frame = load_changes_frame(refresh=refresh_data)
    events = build_event_list(frame)
    if len(events) < MIN_EVENTS:
        raise RuntimeError(f"only {len(events)} events parsed; need >= {MIN_EVENTS}")
    products = event_tickers(events)
    closes, coverage = load_event_closes(products, refresh=refresh_data, verbose=not download_only)

    if download_only:
        provenance = {
            "events": int(len(events)),
            "unique_tickers": int(len(products)),
            "tickers_with_data": int(sum(1 for row in coverage.values() if row["has_data"])),
            "coverage_path": str(cache_dir_for() / "event_coverage.json"),
        }
        print(json.dumps(provenance, indent=2))
        return provenance

    returns = returns_from_closes(closes, calendar)

    train_end = pd.Timestamp(TRAIN_END)
    val_end = pd.Timestamp(VAL_END)
    train_index = calendar[calendar <= train_end]
    val_index = calendar[(calendar > train_end) & (calendar <= val_end)]
    test_index = calendar[calendar > val_end]
    oos_index = calendar[calendar > train_end]

    artifact = artifact_dir(out)
    grid_rows = []
    for params in iter_grid():
        score = event_walk_forward_score(events, closes, returns, products, train_index, params)
        grid_rows.append({**params, "wf_train_sharpe": score})
    grid = pd.DataFrame(grid_rows).sort_values("wf_train_sharpe", ascending=False)
    grid.to_csv(artifact / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows: train selection produced no finite score")
    best = valid.iloc[0].to_dict()
    selected = {
        "holding_days": int(best["holding_days"]),
        "entry_delay": int(best["entry_delay"]),
        "vol_target": float(best["vol_target"]),
    }

    weights = build_event_weights(
        events, closes, calendar, selected["holding_days"], selected["entry_delay"]
    )
    weights = scaled_event_weights(weights, returns, selected["vol_target"])

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

    inverse_weights = (-weights).reindex(oos_index).fillna(0.0)
    inverse_result = h184.backtest_metrics(
        inverse_weights,
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    inverse_metrics = h184.metrics(
        inverse_result["returns"], inverse_result["equity"], inverse_result["trades"]
    )

    long_weights = build_event_weights(
        long_only_events(events),
        closes,
        calendar,
        selected["holding_days"],
        selected["entry_delay"],
    )
    long_weights = scaled_event_weights(long_weights, returns, selected["vol_target"])
    long_oos = h184.backtest_metrics(
        long_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        zero_rolls(oos_index, products),
    )
    long_metrics = h184.metrics(long_oos["returns"], long_oos["equity"], long_oos["trades"])

    perturbed = [
        value
        for value in perturbation_sharpes(events, closes, returns, products, selected, oos_index)
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

    events_by_year: dict[str, int] = {}
    for event in events:
        key = str(event["event_date"].year)
        events_by_year[key] = events_by_year.get(key, 0) + 1
    n_added_legs = sum(1 for event in events if event["added_ticker"])
    n_short_legs = sum(1 for event in events if event["removed_ticker"])
    usable_added = sum(
        1
        for event in events
        if event["added_ticker"]
        and event_usable(closes, event["added_ticker"], event["event_date"])
    )
    usable_short = sum(
        1
        for event in events
        if event["removed_ticker"]
        and event_usable(closes, event["removed_ticker"], event["event_date"])
    )

    data_meta = {
        "event_source": "Wikipedia Historical components of the S&P 500 (free/PIT effective dates)",
        "event_url": probe.CHANGES_URL,
        "price_source": "yfinance auto-adjusted Close (free/public)",
        "universe": "all added + tradeable-by-construction removed event tickers",
        "tradeable_removed_buckets": sorted(TRADEABLE_REMOVED_BUCKETS),
        "n_events": int(len(events)),
        "events_by_year": events_by_year,
        "n_added_legs": int(n_added_legs),
        "n_short_legs": int(n_short_legs),
        "usable_added_legs": int(usable_added),
        "usable_short_legs": int(usable_short),
        "unique_tickers": int(len(products)),
        "tickers_with_data": int(sum(1 for row in coverage.values() if row["has_data"])),
        "population_coverage_added_frac": 282 / 370,
        "population_coverage_tradeable_removed_frac": 104 / 169,
        "coverage_note": (
            "survivorship-biased subset: excluded added names (mostly later "
            "delisted) bias the long leg upward; excluded removed names (mostly "
            "later bankrupt) bias the short leg downward"
        ),
        "min_price_observations": MIN_PRICE_OBSERVATIONS,
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
            "random_event_signs_oos": random_metrics,
            "inverse_event_oos": inverse_metrics,
            "long_only_additions_oos": long_metrics,
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
            "pit_rule": "Wikipedia effective date; engine shift(1); no announcement-date lookahead",
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
        help="populate the changes/price cache and exit (resumable)",
    )
    parser.add_argument(
        "--refresh-data",
        action="store_true",
        help="re-fetch the changes table and price panel even if cached",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only, refresh_data=args.refresh_data)
