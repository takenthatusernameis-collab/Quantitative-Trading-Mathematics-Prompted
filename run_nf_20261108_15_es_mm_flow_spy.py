"""NF-20261108-15 / H150 (Cycle 64): SPY timing from E-mini S&P 500
futures (ES=F) managed-money / leveraged-fund net positioning flow.

Repo-relative novelty (honest). No executed NF/H in this repo uses CFTC
Traders-in-Financial-Futures (TFF) managed-money net position in ES futures
as the SPY timing observable. All prior families use price/volume/volatility
or cross-asset ratio observables drawn from yfinance. H150 is the first
execution of a regulatory position-flow observable (CFTC TFF, free public
CSV, weekly, point-in-time).

Mechanism (institutional positioning flow): the CFTC TFF report breaks ES
futures open interest into Dealer, Asset Manager, Leveraged Money and Other
Reportables. Leveraged Money (CTA / hedge-fund / systematic) net position
(= MM_Long - MM_Short) is a proxy for aggressive directional positioning flow.
When leveraged money is abnormally net-long ES (z-score high), the marginal
buyer has already deployed; mean-reversion / crowding risk suggests reduced
SPY exposure. When abnormally net-short, the opposite. The signal is
computed from a Friday-dated weekly report known at Friday's close and traded
at next Monday's open (1-bar execution delay via engine signals.shift(1)).

Null (H0). ES leveraged-money net positioning contains no incremental SPY
timing information; OOS gates fail vs buy-hold / random-exposure.

Pre-registration (Cycle 64, decision-ready before validation outcomes).
Hypothesis H150. Universe: SPY (traded) + ES=F (signal, yfinance proxy for
the ES futures price level; the *positioning* signal comes from the CFTC TFF
CSV). Data: CFTC TFF disaggregated-financial CSV (free, public, weekly,
2010-2024) + yfinance ES=F/SPY daily auto-adjust Close. Continuous stress on
positive z = (z.clip(0)/entry_scale).clip(0,1); exposure (1-stress)*vol_target
*vscale; 1-bar delay; long-only. Bounded grid: mm_window {63,126} x z_window
{126,252} x entry_scale {1.0,2.0} x vol_target {0.10,0.15} (16 combos);
train-only 4-fold WF selection by mean train Sharpe; Test protected.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-exposure-matched, inverse regime (de-risk
when ES MM net position is abnormally LOW / negative z - pre-registered
falsifier).

Falsifiers: random-exposure comparable or better; inverse outperforms
(H138/H139 pattern); benchmark fails; fragile; worst-regime collapse.
"""

from __future__ import annotations

import csv
import datetime
import io
import json
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.validation.statistics import sharpe_ratio  # noqa: E402

EXPERIMENT_DESC = (
    "NF-20261108-15/H150: SPY timing from E-mini S&P 500 futures (ES=F) "
    "managed-money / leveraged-fund net positioning flow (CFTC TFF, free "
    "public CSV, weekly, point-in-time). De-risk vol-targeted long SPY when "
    "z-score of trailing ES leveraged-money net position is abnormally "
    "positive (crowding / mean-reversion). 1-bar delay. Train-only WF "
    "selection; Test protected; OOS Val+Test gates; inverse falsifier."
)

SPY = "SPY"
ES = "ES=F"
UNIVERSE = [SPY, ES]
DATA_START = "2010-01-01"
DATA_END = "2025-01-05"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
SEED = 150
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

MM_WINDOWS = [63, 126]
Z_WINDOWS = [126, 252]
ENTRY_SCALES = [1.0, 2.0]
VOL_TARGETS = [0.10, 0.15]

# CFTC Traders-in-Financial-Futures (TFF / disaggregated "Commitments of
# Traders" financial futures) historical compressed zips (free, public,
# weekly). One zip per report year, 2010-2024. A report's date is the
# publication date known at that date's close, so forward-filling the series
# onto the daily calendar is point-in-time safe.
TFF_ZIPS = [
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2024.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2023.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2022.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2021.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2020.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2019.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2018.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2017.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2016.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2015.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2014.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2013.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2012.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2011.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2010.zip",
]

# CFTC market name for the aggregate of all S&P 500 futures (E-mini, micro,
# etc.). The TFF file lists overlapping contracts for the same report date
# (Consolidated, E-mini, Micro E-mini, dividend futures); using only the
# consolidated aggregate avoids double-counting the same open interest.
TFF_MARKET_KEY = "S&P 500 Consolidated"

# Leveraged-money position column conventions across report years. Newer
# files (2013+) use "Lev_Money_Positions_*"; older files (2010-2012) used
# "M_Money_Positions_*" in some distributions. Both are supported.
LEVERAGED_MONEY_COLUMNS = (
    ("Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"),
    ("M_Money_Positions_Long_All", "M_Money_Positions_Short_All"),
)

# Date-column conventions across report years. Newer files use ISO
# "Report_Date_as_YYYY-MM-DD"; older files use "As_of_Date_In_Form_YYMMDD"
# (e.g. "101228" = 2010-12-28).
DATE_COLUMNS = (
    "Report_Date_as_YYYY-MM-DD",
    "As_of_Date_In_Form_YYMMDD",
)


def _fetch_tff_mm() -> pd.DataFrame:
    """Download CFTC Traders-in-Financial-Futures historical zips (free,
    public, weekly) and return a long-format DataFrame of ES leveraged-money
    net position (lev_money_long - lev_money_short) indexed by report date.

    PIT: a report's date is the publication date known at that date's close;
    forward-filling onto the daily calendar never uses a report before its
    report date. Column conventions changed across report years
    ("Lev_Money_Positions_*" vs "M_Money_Positions_*", ISO date vs YYMMDD
    date); both are handled. Only the CFTC "S&P 500 Consolidated" aggregate
    is used, so overlapping contract rows (E-mini, Micro E-mini, dividend
    futures) for the same date are not double-counted.
    """
    import urllib.request

    rows: list[dict] = []
    for url in TFF_ZIPS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            blob = urllib.request.urlopen(req, timeout=120).read()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] TFF zip failed: {url}: {exc!r}")
            continue
        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] TFF zip not a zip: {url}: {exc!r}")
            continue
        for name in zf.namelist():
            if not name.endswith(".txt"):
                continue
            txt = zf.read(name).decode("latin-1")
            reader = csv.DictReader(io.StringIO(txt))
            lev_cols = None
            for long_c, short_c in LEVERAGED_MONEY_COLUMNS:
                if long_c in reader.fieldnames and short_c in reader.fieldnames:
                    lev_cols = (long_c, short_c)
                    break
            if lev_cols is None:
                print(f"[warn] TFF file {name} has no leveraged-money columns")
                continue
            lev_long, lev_short = lev_cols
            for rec in reader:
                market = (rec.get("Market_and_Exchange_Names") or "").strip()
                if TFF_MARKET_KEY not in market:
                    continue
                date = _parse_report_date(rec)
                if date is None:
                    continue
                mm_long = _to_float(rec.get(lev_long))
                mm_short = _to_float(rec.get(lev_short))
                if mm_long is None or mm_short is None:
                    continue
                rows.append(
                    {
                        "date": date,
                        "market": market,
                        "mm_net": mm_long - mm_short,
                    }
                )
    if not rows:
        raise RuntimeError("no ES TFF rows fetched")
    df = (
        pd.DataFrame(rows)
        .sort_values("date")
        .drop_duplicates(subset=["date", "market"], keep="last")
    )
    df = df.groupby("date", as_index=False)["mm_net"].sum()
    df = df.dropna(subset=["mm_net"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    if df["mm_net"].isna().any():
        df = df.dropna(subset=["mm_net"])
    return df


def _parse_report_date(rec) -> pd.Timestamp | None:
    """Return the report date known at that date's close (PIT-safe). Supports
    the ISO "Report_Date_as_YYYY-MM-DD" column (2013+) and the
    "As_of_Date_In_Form_YYMMDD" column (2010-2012, e.g. "101228")."""
    for col in DATE_COLUMNS:
        v = (rec.get(col) or "").strip()
        if not v:
            continue
        try:
            if col == DATE_COLUMNS[1]:
                return pd.Timestamp(datetime.datetime.strptime(v, "%y%m%d").date())
            return pd.Timestamp(v)
        except (ValueError, TypeError):  # noqa: BLE001
            continue
    return None


def _to_float(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s in ("", ".", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _fetch_prices() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download([SPY, ES], start=DATA_START, end=DATA_END, progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"][[SPY, ES]]
    else:
        close = raw[[SPY, ES]]
    df = close.dropna().sort_index()
    df = df[(df > 0).all(axis=1)]
    if df.empty:
        raise RuntimeError("empty price data")
    return df


def _splits(index: pd.DatetimeIndex):
    train = pd.Series(index <= pd.Timestamp(TRAIN_END), index=index)
    val = pd.Series(
        (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END)),
        index=index,
    )
    test = pd.Series(index > pd.Timestamp(VAL_END), index=index)
    return train, val, test


def _mm_net_weekly(tff: pd.DataFrame) -> pd.Series:
    """Resample the weekly report series onto the trading calendar by
    forward-filling the most recent known Friday report value."""
    s = tff.set_index("date")["mm_net"].sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s


def _mm_zscore(mm_net: pd.Series, mm_window: int, z_window: int) -> pd.Series:
    """Rolling mean of ES leveraged-money net position over mm_window (in
    report-week units), z-scored over z_window. Positive z = abnormally
    net-long (crowding)."""
    min_m = max(10, int(mm_window) // 2)
    min_z = max(30, int(z_window) // 2)
    m = mm_net.rolling(int(mm_window), min_periods=min_m).mean()
    s = mm_net.rolling(int(z_window), min_periods=min_z).std()
    return (mm_net - m) / s.replace(0.0, np.nan)


def _vol_scale(prices: pd.DataFrame, vol_target: float, lookback: int = 21) -> pd.Series:
    rv = prices[SPY].pct_change().rolling(lookback, min_periods=10).std() * np.sqrt(252)
    scale = (float(vol_target) / rv.replace(0.0, np.nan)).clip(0.0, 3.0)
    return scale.reindex(prices.index).fillna(0.0)


def make_signals(prices: pd.DataFrame, mm_net: pd.Series, params: dict) -> pd.DataFrame:
    z = _mm_zscore(mm_net, params["mm_window"], params["z_window"])
    # Reindex the weekly report z-score onto the daily trading calendar via
    # forward-fill (most recent Friday report known at each day's close).
    z_daily = z.reindex(prices.index, method="ffill").fillna(0.0)
    stress = (z_daily.clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    raw = (1.0 - stress) * float(params["vol_target"])
    vscale = _vol_scale(prices, params["vol_target"])
    expo = (raw * vscale).fillna(0.0).clip(lower=0.0, upper=MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = expo
    sig.attrs["z"] = z_daily
    return sig


def _cfg() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        max_position_size=MAX_POS,
        max_leverage=1.0,
        asset_class=AssetClass.EQUITY,
        allow_short=False,
    )


def run_one(prices: pd.DataFrame, mm_net: pd.Series, params: dict):
    sig = make_signals(prices, mm_net, params)
    res = run_backtest(prices, sig, _cfg())
    return {"result": res, "signals": sig, "z": sig.attrs["z"]}


def _metrics_from_result(res, mask: pd.Series) -> dict:
    eq = res.equity_curve.loc[res.equity_curve.index.intersection(mask.index[mask])]
    if len(eq) < 30:
        return {
            "n": int(len(eq)),
            "sharpe": float("nan"),
            "profit_factor": float("nan"),
            "max_drawdown": float("nan"),
            "trades": 0,
        }
    ret = eq.pct_change().dropna()
    neg = ret[ret < 0].abs().sum()
    pf = float(ret[ret > 0].sum() / neg) if neg > 1e-12 else float("inf")
    peak = eq.cummax()
    mdd = float(((eq - peak) / peak.replace(0.0, np.nan)).min())
    trades_df = res.trades
    if (
        trades_df is None
        or (hasattr(trades_df, "empty") and trades_df.empty)
        or len(trades_df) == 0
    ):
        ntr = 0
    else:
        td = trades_df
        if "date" in td.columns:
            tmask = pd.to_datetime(td["date"]).isin(eq.index)
            ntr = int(tmask.sum())
        else:
            ntr = int(len(td))
    return {
        "n": int(len(ret)),
        "sharpe": float(sharpe_ratio(ret)),
        "profit_factor": pf,
        "max_drawdown": mdd,
        "trades": ntr,
    }


def wf_train_mean_sharpe(
    prices: pd.DataFrame, mm_net: pd.Series, params: dict, train_mask: pd.Series
) -> float:
    idx = prices.index[train_mask]
    if len(idx) < 400:
        return float("nan")
    splits = np.array_split(np.arange(len(idx)), WF_FOLDS_SELECTION)
    sharpes = []
    for i in range(1, len(splits)):
        fold_idx = idx[splits[i]]
        fmask = pd.Series(prices.index.isin(fold_idx), index=prices.index)
        m = _metrics_from_result(run_one(prices, mm_net, params)["result"], fmask)
        if np.isfinite(m["sharpe"]):
            sharpes.append(m["sharpe"])
    return float(np.mean(sharpes)) if sharpes else float("nan")


def perturbation_ratio(
    prices: pd.DataFrame, mm_net: pd.Series, best: dict, oos_mask: pd.Series
) -> float:
    base = _metrics_from_result(run_one(prices, mm_net, best)["result"], oos_mask)["sharpe"]
    if not np.isfinite(base) or abs(base) < 1e-12:
        return float("nan")
    ratios = []
    for k, delta in [
        ("mm_window", 21),
        ("z_window", 63),
        ("entry_scale", 0.25),
        ("vol_target", 0.02),
    ]:
        for sign in (-1, 1):
            p = dict(best)
            alt = p[k] + sign * delta
            if k in ("mm_window", "z_window"):
                alt = int(max(10, round(alt)))
            p[k] = type(best[k])(alt) if not isinstance(best[k], float) else float(alt)
            try:
                s = _metrics_from_result(run_one(prices, mm_net, p)["result"], oos_mask)["sharpe"]
            except Exception:
                continue
            if np.isfinite(s):
                ratios.append(s / base)
    return float(np.min(ratios)) if ratios else float("nan")


def worst_regime_sharpe(
    prices: pd.DataFrame, mm_net: pd.Series, best: dict, oos_mask: pd.Series
) -> float:
    res = run_one(prices, mm_net, best)["result"]
    eq = res.equity_curve.loc[res.equity_curve.index.intersection(prices.index[oos_mask])]
    ret = eq.pct_change().dropna()
    if len(ret) < 252:
        return float("nan")
    vals = [float(sharpe_ratio(ret.iloc[i - 252 : i])) for i in range(252, len(ret) + 1)]
    vals = [v for v in vals if np.isfinite(v)]
    return float(np.min(vals)) if vals else float("nan")


def benchmark_buy_hold(prices: pd.DataFrame, mask: pd.Series) -> dict:
    p = prices.loc[mask, SPY]
    ret = p.pct_change().dropna()
    peak = p.cummax()
    mdd = float(((p - peak) / peak).min())
    neg = ret[ret < 0].abs().sum()
    pf = float(ret[ret > 0].sum() / neg) if neg > 1e-12 else float("inf")
    return {
        "sharpe": float(sharpe_ratio(ret)),
        "profit_factor": pf,
        "max_drawdown": mdd,
        "trades": 1,
    }


def random_exposure_matched(
    prices: pd.DataFrame, mask: pd.Series, mean_expo: float, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    p = prices.loc[mask, SPY]
    ret = p.pct_change().dropna()
    expo = pd.Series(rng.uniform(0, 1, len(ret)), index=ret.index)
    expo = expo * (mean_expo / expo.mean()) if expo.mean() > 1e-12 else expo
    expo = expo.clip(0.0, MAX_POS)
    strat = (ret * expo.shift(1).fillna(0.0)).dropna()
    peak = (1 + strat).cumprod().cummax()
    eq = (1 + strat).cumprod()
    mdd = float(((eq - peak) / peak).min())
    neg = strat[strat < 0].abs().sum()
    pf = float(strat[strat > 0].sum() / neg) if neg > 1e-12 else float("inf")
    ntr = int((expo.diff().abs().fillna(0) > 1e-6).sum())
    return {
        "sharpe": float(sharpe_ratio(strat)),
        "profit_factor": pf,
        "max_drawdown": mdd,
        "trades": ntr,
    }


def inverse_regime(prices: pd.DataFrame, mm_net: pd.Series, params: dict) -> dict:
    z = _mm_zscore(mm_net, params["mm_window"], params["z_window"])
    z_daily = z.reindex(prices.index, method="ffill").fillna(0.0)
    # inverse: de-risk when ES MM net position is abnormally LOW / negative z
    stress = ((-z_daily).clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    raw = (1.0 - stress) * float(params["vol_target"])
    vscale = _vol_scale(prices, params["vol_target"])
    expo = (raw * vscale).fillna(0.0).clip(lower=0.0, upper=MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = expo
    res = run_backtest(prices, sig, _cfg())
    oos = pd.Series((prices.index > pd.Timestamp(TRAIN_END)), index=prices.index)
    return _metrics_from_result(
        res, pd.Series((prices.index > pd.Timestamp(TRAIN_END)), index=prices.index)
    )


def main():
    t0 = time.time()
    tff = _fetch_tff_mm()
    prices = _fetch_prices()
    train_m, val_m, test_m = _splits(prices.index)
    oos_m = val_m | test_m

    # Align the weekly MM-net series to the trading calendar (forward-fill).
    mm_net = _mm_net_weekly(tff)
    mm_net = mm_net.reindex(prices.index, method="ffill")
    if mm_net.isna().all():
        raise RuntimeError("MM net position empty after reindex")

    grid = []
    for mm_window in MM_WINDOWS:
        for z_window in Z_WINDOWS:
            for entry_scale in ENTRY_SCALES:
                for vol_target in VOL_TARGETS:
                    p = dict(
                        mm_window=mm_window,
                        z_window=z_window,
                        entry_scale=entry_scale,
                        vol_target=vol_target,
                    )
                    wf = wf_train_mean_sharpe(prices, mm_net, p, train_m)
                    grid.append({**p, "wf_train_mean_sharpe": wf})
    grid_df = pd.DataFrame(grid).sort_values("wf_train_mean_sharpe", ascending=False)
    best = {
        k: (int(v) if k in ("mm_window", "z_window") else float(v))
        for k, v in grid_df.iloc[0][["mm_window", "z_window", "entry_scale", "vol_target"]].items()
    }

    oos_res = run_one(prices, mm_net, best)["result"]
    oos_met = _metrics_from_result(oos_res, oos_m)
    bh = benchmark_buy_hold(prices, oos_m)
    eq = oos_res.equity_curve.loc[oos_res.equity_curve.index.intersection(prices.index[oos_m])]
    strat_ret = eq.pct_change().dropna()
    bh_ret = prices.loc[oos_m, SPY].pct_change().reindex(strat_ret.index).dropna()
    common = strat_ret.index.intersection(bh_ret.index)
    diff = (strat_ret.loc[common] - bh_ret.loc[common]).values
    rng = np.random.default_rng(SEED)
    boots = [rng.choice(diff, size=len(diff), replace=True).mean() * 252 for _ in range(2000)]
    ir = float(diff.mean() / (diff.std() + 1e-12) * np.sqrt(252))
    p_bench = float(np.mean(np.array(boots) <= 0.0))
    wf_stab = (
        float(oos_met["sharpe"] / grid_df.iloc[0]["wf_train_mean_sharpe"])
        if np.isfinite(grid_df.iloc[0]["wf_train_mean_sharpe"])
        and abs(grid_df.iloc[0]["wf_train_mean_sharpe"]) > 1e-12
        else float("nan")
    )
    worst = worst_regime_sharpe(prices, mm_net, best, oos_m)
    pert = perturbation_ratio(prices, mm_net, best, oos_m)

    gates = {
        "sharpe_ge_1": oos_met["sharpe"] >= 1.0,
        "trades_ge_200": oos_met["trades"] >= 200,
        "pf_ge_1_3": oos_met["profit_factor"] >= 1.3,
        "maxdd_le_15pct": (abs(oos_met["max_drawdown"]) <= 0.15)
        if np.isfinite(oos_met["max_drawdown"])
        else False,
        "wf_stability_ge_0_7": (wf_stab >= 0.7) if np.isfinite(wf_stab) else False,
        "worst_regime_ge_0_3": (worst >= 0.3) if np.isfinite(worst) else False,
        "benchmark_p_le_0_05_ir_ge_0": (p_bench <= 0.05 and ir >= 0.0),
        "perturbation_ge_0_5": (pert >= 0.5) if np.isfinite(pert) else False,
    }
    passed = sum(gates.values())
    verdict = "PASS" if passed == len(gates) else "REJECT"

    mean_expo = float(make_signals(prices, mm_net, best)[SPY].loc[oos_m].mean())
    summary = {
        "nf_id_exec": "NF-20261108-15",
        "hypothesis": "H150",
        "verdict": verdict,
        "gates_passed": f"{passed}/{len(gates)}",
        "gates": gates,
        "selected_params": best,
        "selection_wf_train_mean_sharpe": float(grid_df.iloc[0]["wf_train_mean_sharpe"]),
        "oos_val_test": oos_met,
        "wf_stability_ratio": wf_stab,
        "worst_regime_rolling252_sharpe": worst,
        "benchmark_buy_hold_spy_oos": bh,
        "benchmark_p": p_bench,
        "information_ratio_vs_bh": ir,
        "perturbation_min_ratio": pert,
        "ablations": {
            "buy_hold_spy": bh,
            "random_exposure_matched": random_exposure_matched(prices, oos_m, mean_expo, SEED),
            "inverse_regime": inverse_regime(prices, mm_net, best),
        },
        "tff_rows": int(len(tff)),
        "tff_date_range": [str(tff["date"].min().date()), str(tff["date"].max().date())],
        "timing_seconds": round(time.time() - t0, 2),
        "data": {
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
            "rows": int(len(prices)),
        },
        "description": EXPERIMENT_DESC,
    }

    outdir = ROOT / ".experiments" / "nf_runs" / "nf_20261108_15_es_mm_flow_spy"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    grid_df.to_csv(outdir / "grid.csv", index=False)
    meta = {
        "universe": UNIVERSE,
        "train_end": TRAIN_END,
        "val_end": VAL_END,
        "rows": int(len(prices)),
        "train": int(train_m.sum()),
        "val": int(val_m.sum()),
        "test": int(test_m.sum()),
    }
    (outdir / "data_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        json.dumps(
            {"verdict": verdict, "gates": f"{passed}/{len(gates)}", "oos": oos_met, "best": best},
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
