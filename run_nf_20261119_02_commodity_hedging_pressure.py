"""NF-20261119-02 / H186 (Cycle 219 pre-registration and execution).

Broad mechanism category: hedging pressure / risk-transfer premium measured by
the *trader category* that holds the book.  Repo-new root family relative to
executed H1-H185: no executed H-ID uses the CFTC Legacy futures-only
commercial-vs-non-commercial breakdown as a cross-sectional commodity return
predictor.

Separation from prior families.
  * H150 (rejected) uses the CFTC *TFF leveraged-money* net position as a
    *time-series de-risking overlay on SPY*: different report, different
    trader category, different market, timing not cross-section.
  * H185 (rejected) uses total *open interest* growth and the front
    contract's OI share from Chinese exchange cross-sections: a crowding
    quantity with no trader-category information.
  * H184 (rejected) uses the relative *price* of two contracts (settlement
    slope = inventory carry).
H186's observable is (comm_short - comm_long) / open_interest: *who* is on
which side, not how large the book is and not what it costs to roll.

Mechanism / causal chain.  Producers, processors and merchants are natural
short hedgers; they must pay speculators a risk premium to absorb that
exposure (Keynes normal backwardation; Hicks; Bessembinder 1992; de Roon,
Nijman & Veld 2000).  When commercials are unusually net short relative to
open interest, the compensation offered to the long side is high and the
cross-section should earn a positive forward return; unusually net long
commercials should earn less.  Pre-registered direction: long the top-k ETFs
whose underlying future has the highest commercial net-short share, short the
bottom-k.  Null (H0): the commercial hedging-pressure cross-section has no
predictive power for next-period ETF returns after costs -- a positioning
overlay adds nothing over a passive equal-weight long commodity-ETF book.

PIT timing.  Legacy COT reports are as-of Tuesday and released by CFTC on
Friday ~15:30 ET.  Each report is assigned publication date report_date + 3
calendar days (the earliest Friday release; holiday delays only make the true
release later, so this is conservative), and a daily date t may only use the
latest report whose publication date is <= t.  The shared engine then applies
``shift(1)``, so a report as-of Tuesday t is first tradeable at the session
after the Friday release.  No same-week outcome enters the signal.

Pre-registration (Cycle 219, written before any forward-return outcome was
computed).  Sample 2012-01-03 -> 2026-11-17 (common ETF availability); train
-> 2021-12-31; Val 2022-01-01 -> 2023-12-31; Test protected 2024-01-01 ->
2026-11-17.  Universe (ETF <-> CFTC contract market code): GLD/088691,
SLV/084691, USO/067651, UNG/023651, CORN/002602, WEAT/001602, SOYB/005602,
CPER/085692, PPLT/076651.  Features: ``hp`` = (comm_short - comm_long) /
open_interest, and ``hp_change_4w`` = hp_t - hp_{t-4 reports}.  Cross-sectional
z on the weekly report grid, hysteresis entry_z/exit_z, top-k long / bottom-k
short, gross-normalized to one, forward-filled to the daily ETF calendar so
turnover happens at most weekly.  Grid (bounded, 16): feature {hp, hp_change_4w}
x entry_z {0.5, 1.0} x exit_z {0.0} x k {2, 3} x vol_target {0.10, 0.15};
train-only 4-fold walk-forward Sharpe selection.  Costs: 5 bps one-way per leg
traded (ETF commission + spread); no separate roll charge (the ETF embeds
roll); vol targeting delevers only.

Gates (OOS Val+Test, fail-closed, standard 8, unchanged): Sharpe >= 1.0; trades
>= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7; worst-regime rolling-252
Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with IR >= 0 vs the passive
equal-weight long ETF book; OAT +/-20% perturbation min ratio >= 0.5.

Ablations/falsifiers: passive equal-weight long book; random ranking (same
active leg count, seed 42); inverse signal; train-block Spearman of ``hp`` vs
``hp_change_4w`` as an input-collinearity diagnostic.

Implementation constraints: reuse the backtest engine, metrics, gate helpers,
benchmark constructors and cross-sectional/hysteresis primitives from
run_nf_20261114_01_commodity_termstructure_carry.py (no forked copy); only the
CFTC loader and the hedging-pressure alignment are new code.  Free/public real
data only; ``src/qtr`` unchanged.  Artifact under
.experiments/nf_runs/<experiment>_<timestamp>/summary.json + grid.csv.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

try:
    from qtr.validation.statistics import benchmark_significance_gate, compare_to_benchmark
except ImportError:  # allow `python run_nf_*.py` with no editable install
    sys.path.insert(0, str(ROOT / "src"))
    from qtr.validation.statistics import benchmark_significance_gate, compare_to_benchmark

_H184_PATH = ROOT / "run_nf_20261114_01_commodity_termstructure_carry.py"
_h184_spec = importlib.util.spec_from_file_location("h184_termstructure", _H184_PATH)
assert _h184_spec is not None and _h184_spec.loader is not None
h184 = importlib.util.module_from_spec(_h184_spec)  # type: ignore[arg-type]
sys.modules[_h184_spec.name] = h184
_h184_spec.loader.exec_module(h184)

EXPERIMENT = "nf_20261119_02_commodity_hedging_pressure"
NF_ID = "NF-20261119-02"
HYPOTHESIS = "H186"

START = "2012-01-03"
END = "2026-11-17"
TRAIN_END = "2021-12-31"
VAL_END = "2023-12-31"

# ETF <-> CFTC Legacy "futures only" contract market code.
UNIVERSE = [
    ("GLD", "088691"),
    ("SLV", "084691"),
    ("USO", "067651"),
    ("UNG", "023651"),
    ("CORN", "002602"),
    ("WEAT", "001602"),
    ("SOYB", "005602"),
    ("CPER", "085692"),
    ("PPLT", "076651"),
]
PRODUCTS = [etf for etf, _ in UNIVERSE]

COST_ONE_WAY_BPS = 5.0
PUBLISH_LAG_DAYS = 3  # Tuesday report -> Friday release (earliest; holiday = later)
MIN_ACTIVE_NAMES = 5
CHANGE_WINDOW_REPORTS = 4
SEED = 42

GATES = dict(h184.GATES)

FEATURES = ["hp", "hp_change_4w"]
GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0],
    "exit_z": [0.0],
    "k": [2, 3],
    "vol_target": [0.10, 0.15],
}

SOCRATA_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
SOCRATA_SELECT = ",".join(
    [
        "cftc_contract_market_code",
        "report_date_as_yyyy_mm_dd",
        "open_interest_all",
        "comm_positions_long_all",
        "comm_positions_short_all",
    ]
)
CACHE_DIR = Path(".cache") / "cftc_legacy"


# ---------------------------------------------------------------------------
# Data acquisition (free/public, key-less)
# ---------------------------------------------------------------------------


def cftc_query_url(codes: list[str], start: str = START, end: str = END) -> str:
    """SoQL query for the Legacy futures-only report rows of the given markets."""
    quoted = ",".join(f"'{code}'" for code in codes)
    where = (
        f"cftc_contract_market_code in({quoted})"
        f" and report_date_as_yyyy_mm_dd between '{start}T00:00:00.000' and '{end}T23:59:59.999'"
    )
    params = {
        "$select": SOCRATA_SELECT,
        "$where": where,
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": "50000",
    }
    return f"{SOCRATA_URL}?{urllib.parse.urlencode(params)}"


def fetch_cftc_rows(url: str, timeout: int = 120) -> list[dict]:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def parse_cftc_rows(rows: list[dict]) -> pd.DataFrame:
    """Long frame: code, report_date, comm_long, comm_short, open_interest."""
    if not rows:
        return pd.DataFrame(
            columns=["code", "report_date", "comm_long", "comm_short", "open_interest"]
        )
    frame = pd.DataFrame(rows)
    out = pd.DataFrame(
        {
            "code": frame["cftc_contract_market_code"].astype(str),
            "report_date": pd.to_datetime(
                frame["report_date_as_yyyy_mm_dd"].astype(str).str.slice(0, 10)
            ),
            "comm_long": pd.to_numeric(frame["comm_positions_long_all"], errors="coerce"),
            "comm_short": pd.to_numeric(frame["comm_positions_short_all"], errors="coerce"),
            "open_interest": pd.to_numeric(frame["open_interest_all"], errors="coerce"),
        }
    )
    out = out.dropna(subset=["comm_long", "comm_short", "open_interest", "report_date"])
    return out.sort_values(["code", "report_date"]).reset_index(drop=True)


def ensure_cftc_cache(codes: list[str], cache_dir: Path = CACHE_DIR) -> pd.DataFrame:
    path = cache_dir / "legacy_commodities.csv"
    if path.exists():
        cached = pd.read_csv(path, parse_dates=["report_date"])
        if set(codes).issubset(set(cached["code"].unique())):
            return cached
    cache_dir.mkdir(parents=True, exist_ok=True)
    parsed = parse_cftc_rows(fetch_cftc_rows(cftc_query_url(codes)))
    if parsed.empty:
        raise RuntimeError("CFTC Legacy query returned no rows")
    parsed.to_csv(path, index=False)
    return parsed


def ensure_etf_cache(products: list[str], cache_dir: Path = CACHE_DIR) -> pd.DataFrame:
    path = cache_dir / "etf_closes.csv"
    if path.exists():
        cached = pd.read_csv(path, index_col=0, parse_dates=True)
        if set(products).issubset(set(cached.columns)):
            return cached
    import yfinance as yf

    cache_dir.mkdir(parents=True, exist_ok=True)
    raw = yf.download(list(products), start=START, end=END, auto_adjust=True, progress=False)[
        "Close"
    ]
    raw = raw.reindex(columns=list(products))
    raw.to_csv(path)
    return raw


# ---------------------------------------------------------------------------
# Hedging-pressure construction (the only new signal code)
# ---------------------------------------------------------------------------


def hedging_pressure_row(frame: pd.DataFrame) -> pd.Series:
    """(comm_short - comm_long) / open_interest for one market's report history."""
    oi = frame["open_interest"].where(frame["open_interest"] > 0)
    hp = (frame["comm_short"] - frame["comm_long"]) / oi
    hp.index = pd.DatetimeIndex(frame["report_date"])
    return hp.where(np.isfinite(hp))


def weekly_hedging_pressure(rows: pd.DataFrame, universe: list[tuple[str, str]]) -> pd.DataFrame:
    """Report-date x ETF frame of commercial net-short share of open interest."""
    series = {}
    for etf, code in universe:
        block = rows[rows["code"] == code]
        if block.empty:
            continue
        series[etf] = hedging_pressure_row(block)
    if not series:
        return pd.DataFrame()
    frame = pd.DataFrame(series).sort_index()
    return frame.where(frame.notna().sum(axis=1) >= MIN_ACTIVE_NAMES)


def publication_dates(report_index: pd.DatetimeIndex, lag_days: int = PUBLISH_LAG_DAYS):
    """CFTC release date: earliest Friday publication for a Tuesday as-of date."""
    return pd.DatetimeIndex(report_index) + pd.Timedelta(days=lag_days)


def feature_panel(hp_weekly: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """All declared H186 features on the weekly report grid."""
    change = hp_weekly - hp_weekly.shift(CHANGE_WINDOW_REPORTS)
    return {"hp": hp_weekly, "hp_change_4w": change.where(np.isfinite(change))}


def align_to_daily(
    weekly: pd.DataFrame, report_index: pd.DatetimeIndex, daily_index: pd.DatetimeIndex
) -> pd.DataFrame:
    """PIT alignment: daily t sees only the latest report published on or before t."""
    published = pd.DatetimeIndex(publication_dates(report_index))
    order = np.argsort(published.values, kind="stable")
    published = published[order]
    frame = weekly.iloc[order]
    positions = np.searchsorted(published.values, daily_index.values, side="right") - 1
    aligned = pd.DataFrame(np.nan, index=daily_index, columns=frame.columns, dtype=float)
    rows = frame.to_numpy(dtype=float)
    valid = positions >= 0
    aligned.iloc[np.where(valid)[0]] = rows[positions[valid]]
    return aligned


def target_weights(
    feature_daily: pd.DataFrame,
    params: dict,
    returns: pd.DataFrame,
    products: list[str],
) -> pd.DataFrame:
    """Cross-sectional z + hysteresis on daily-aligned features, vol-target scaled."""
    z = h184.cross_sectional_z(feature_daily)
    weights = h184.signal_weights(
        z, params["entry_z"], params["exit_z"], int(params["k"]), products
    )
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
    """Input-only diagnostic: cross-sectional Spearman of hp vs hp_change_4w."""
    left, right = features["hp"], features["hp_change_4w"]
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
    products = list(PRODUCTS)

    rows = ensure_cftc_cache([code for _, code in UNIVERSE])
    closes = ensure_etf_cache(products)
    if download_only:
        provenance = {
            "cftc_rows": int(len(rows)),
            "cftc_first": str(rows["report_date"].min().date()) if len(rows) else "",
            "cftc_last": str(rows["report_date"].max().date()) if len(rows) else "",
            "etf_rows": int(len(closes)),
            "etf_first": str(closes.index.min().date()) if len(closes) else "",
            "etf_last": str(closes.index.max().date()) if len(closes) else "",
        }
        print(json.dumps(provenance, indent=2))
        return provenance

    returns = closes.reindex(calendar).ffill().pct_change(fill_method=None)
    returns = returns.where(np.isfinite(returns))

    hp_weekly = weekly_hedging_pressure(rows, UNIVERSE)
    if hp_weekly.empty:
        raise RuntimeError("no hedging-pressure cross-sections built")
    features_weekly = feature_panel(hp_weekly)
    report_index = hp_weekly.index
    features_daily = {
        name: align_to_daily(frame.reindex(columns=products), report_index, calendar)
        for name, frame in features_weekly.items()
    }

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

    data_meta = {
        "cftc_source": SOCRATA_URL,
        "cftc_dataset": "Legacy - Futures Only",
        "cftc_reports": int(len(report_index)),
        "cftc_first_report": str(report_index.min().date()),
        "cftc_last_report": str(report_index.max().date()),
        "publish_lag_days": PUBLISH_LAG_DAYS,
        "etf_source": "yfinance auto-adjusted Close (free/public)",
        "universe": [{"etf": etf, "cftc_code": code} for etf, code in UNIVERSE],
        "active_names_last_report": int(hp_weekly.iloc[-1].notna().sum()),
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
        "train_input_collinearity_hp_vs_change": train_collinearity(features_daily, train_index),
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
            "roll_cross_bps": 0.0,
            "benchmark_pvalue_statistic": "two-sided (published gate statistic)",
            "pit_rule": "report_date + 3 calendar days publication, engine shift(1)",
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
        help="populate the CFTC/ETF cache and exit (resumable)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(out=args.out, download_only=args.download_only)
