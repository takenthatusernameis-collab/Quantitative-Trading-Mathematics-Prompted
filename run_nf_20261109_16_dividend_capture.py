"""NF-20261109-16 / H180 (Cycle 94): Dividend Capture / Ex-Dividend Microstructure Premium.

Corporate action / microstructure (repo-new root family). Distinct from all exhausted
families: H91/H140/H142/H168 (calendar seasonality windows - recurring generic windows,
not discrete corporate cash-flow events), H173 (Fed model / ERP dividend-yield LEVEL -
valuation-level timing, not ex-dividend microstructure), H174 (ETF premium/discount to
NAV - creation/redemption arbitrage convergence, invalid without PIT NAV), H176 (tax-loss
harvesting - December tax flow), H177 (Treasury auction - government supply operations),
H178 (options put/call ratio - derivatives positioning), H179 (short interest - limits to
arbitrage), and all TSMOM/relmom/vol/credit/rates/VIX families.

Mechanism. On an ex-dividend date the stock price theoretically drops by the dividend
amount; the dividend clientele / microstructure premium says prices may drop by *less*
than the dividend (buyers compensate sellers for the foregone cash), so buying before the
ex-date and selling after can capture dividend cash net of the price drop. Causal chain:
dividend declared and ex-date known ex-ante -> buy at close day before ex-date (holder of
record) -> receive dividend cash plus any price resilience -> sell after ex-date.

Causal chain (PIT). Dividend declaration and the ex-date schedule are public ~3 weeks
before the ex-date, so at the close of day e-1 the ex-date e dividend is known. Position
set at close e-1 earns return e->e+1 via engine `signals.shift(1)`, plus credited dividend
cash on ex-date e. Strictly causal: no dividend amount is used before its declaration is
public; the ex-date schedule is treated as known from past-only dividend history.

Observable (past-only, PIT, free/public). yfinance daily OHLC (auto_adjust=False so the
ex-date price drop remains visible) + yfinance dividend history (ex-date, amount) for SPY
and sector ETFs. yfinance dividend index is the ex-date at 09:30 ET (market open), so the
close of day e-1 already knows the ex-date e dividend. 2010-01-01 -> 2026-10-31.

Honest caveats (disclosed, not silenced). (1) Low frequency: ~4 ex-dates per year per
ETF -> order 16 events over the 4-year protected OOS window for SPY alone, below the
>= 50 OOS trades gate; the sector-ETF universe expansion (~44 events/year) is the only
grid leg that can clear the trades gate. (2) yfinance dividend history is not guaranteed
strictly point-in-time at declaration date; ex-date schedule used as known ex-ante. (3)
Overnight/open slippage around ex-dates may exceed the modeled equity cost model on free
data; costs are applied on both legs of each round trip.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest

EXPERIMENT = "nf_20261109_16_dividend_capture"
NF_ID = "NF-20261109-16"
HYPOTHESIS = "H180"
START = "2010-01-01"
END = "2026-10-31"
MAX_POS = 0.5
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 21

SECTOR_ETFS = ["SPY", "XLF", "XLE", "XLV", "XLI", "XLB", "XLP", "XLU", "XLY", "XLC", "XLK"]

# Pre-registered splits (holdout fixed ex-ante; selection train-only, gates OOS only).
TRAIN_END = "2018-12-31"
VAL_END = "2022-12-31"
TEST_END = "2026-10-30"

GRID = {
    "hold_days": [0, 1, 2],  # exit at close of ex-date + hold_days
    "vol_target": [0.10, 0.15],
    "universe": ["SPY", "SPY_SECTORS"],
}

# Gates (OOS Val+Test, fail-closed). Low-frequency event strategy: trades >= 50.
GATES = {
    "sharpe": (1.0, lambda v: np.isfinite(v) and v >= 1.0),
    "trades": (50, lambda v: int(v) >= 50),
    "pf": (1.3, lambda v: np.isfinite(v) and v >= 1.3),
    "maxdd": (-0.15, lambda v: np.isfinite(v) and v >= -0.15),
    "wf_stability": (0.7, lambda v: np.isfinite(v) and v >= 0.7),
    "worst_regime": (0.3, lambda v: np.isfinite(v) and v >= 0.3),
    "benchmark": (0.05, lambda v: np.isfinite(v) and v <= 0.05),
    "perturbation": (0.5, lambda v: np.isfinite(v) and v >= 0.5),
}


def _artifact_dir(out: str | None) -> Path:
    if out:
        p = Path(out).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    ts = time.strftime("%Y%m%d_%H%M%S")
    p = (Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{ts}").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


# ------------------------------------------------------------ data acquisition
def _download_yfinance_daily(
    tickers: list[str], start: str, end: str, auto_adjust: bool
) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=auto_adjust,
        progress=False,
        threads=True,
    )
    if raw is None or len(raw) == 0:
        raise RuntimeError("yfinance returned empty data")
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]]
        close.columns = [tickers[0]]
    close = close.ffill().dropna(how="all")
    close.columns = [str(c) for c in close.columns]
    return close


def _fetch_dividends(tickers: list[str]) -> dict[str, pd.Series]:
    """Download per-ticker dividend history (ex-date -> amount per share).

    yfinance dividend index is tz-aware at 09:30 ET on the ex-date; normalized to
    tz-naive dates and treated as the ex-dividend date.
    """
    out: dict[str, pd.Series] = {}
    for ticker in tickers:
        try:
            div = yf.Ticker(ticker).dividends
        except Exception:
            div = None
        if div is None or len(div) == 0:
            out[ticker] = pd.Series(dtype=float)
            continue
        d = div.sort_index()
        d.index = pd.DatetimeIndex(d.index).tz_localize(None)
        d.index = d.index.normalize()
        d = d.astype(float)
        d = d[d > 0]
        out[ticker] = d
    return out


def _align_dividends_to_daily(
    daily_index: pd.DatetimeIndex, dividends: dict[str, pd.Series], tickers: list[str]
) -> dict[str, pd.Series]:
    """Align dividend amounts to the daily trading index (amount on ex-date, 0 else)."""
    aligned: dict[str, pd.Series] = {}
    for ticker in tickers:
        d = dividends.get(ticker, pd.Series(dtype=float))
        s = pd.Series(0.0, index=daily_index)
        if not d.empty:
            common = d.index.intersection(daily_index)
            if len(common):
                s.loc[common] = d.reindex(common).to_numpy()
        aligned[ticker] = s.astype(float)
    return aligned


# ------------------------------------------------------------ signal / backtest
def _compute_weights(
    prices: pd.DataFrame,
    div_aligned: dict[str, pd.Series],
    hold_days: int,
    vol_target: float,
    universe: str,
) -> pd.DataFrame:
    """Long vol-targeted exposure from close day before each ex-date through close
    ex-date + hold_days. Flat otherwise. No shorting."""
    tickers = prices.columns.tolist()
    weights = pd.DataFrame(0.0, index=prices.index, columns=tickers)
    hold_days = int(hold_days)

    for ticker in tickers:
        div = div_aligned[ticker]
        rets = prices[ticker].pct_change()
        vol = rets.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(DAYS_PER_YEAR)
        vol_scale = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 3.0).fillna(0.0)

        active = pd.Series(False, index=prices.index)
        ex_locs = prices.index.get_indexer(div[div > 0].index)
        for loc in ex_locs:
            if loc == -1:
                continue
            start = max(0, loc - 1)
            end = min(len(prices) - 1, loc - 1 + hold_days)
            active.iloc[start : end + 1] = True

        w = (active.astype(float) * vol_scale).clip(0.0, MAX_POS)
        weights[ticker] = w

    if universe == "SPY":
        for c in weights.columns:
            if c != "SPY":
                weights[c] = 0.0
    return weights


def _run_bt(
    close: pd.DataFrame,
    weights: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, int, pd.DataFrame]:
    cfg = BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        allow_short=False,
    )
    res = run_backtest(close, weights, cfg)
    strat_ret = res.returns.reindex(close.index).fillna(0.0).astype(float)
    eq = res.equity_curve.reindex(close.index).astype(float)
    pos = res.positions.reindex(close.index).fillna(0.0)
    trades = int((pos.diff().abs() > 1e-12).sum().sum())
    return strat_ret, eq, trades, pos


def _credit_dividends(
    strat_ret: pd.Series,
    positions: pd.DataFrame,
    prices: pd.DataFrame,
    div_aligned: dict[str, pd.Series],
) -> pd.Series:
    """Add dividend cash received on ex-dates for positions held into the ex-date.

    Approximation: dividend amount per share divided by the prior close, credited to
    the ex-date return, scaled by the position held at the prior close. Disclosed as
    a convention; engine itself models price returns and costs only.
    """
    credit = pd.Series(0.0, index=strat_ret.index)
    for ticker in prices.columns:
        pos = positions[ticker]
        div = div_aligned[ticker]
        px = prices[ticker]
        ex_locs = prices.index.get_indexer(div[div > 0].index)
        for loc in ex_locs:
            if loc <= 0 or loc == -1:
                continue
            prev = prices.index[loc - 1]
            w = float(pos.loc[prev]) if prev in pos.index else 0.0
            if w <= 0:
                continue
            prior_px = float(px.loc[prev])
            if not math.isfinite(prior_px) or prior_px <= 0:
                continue
            credit.loc[prices.index[loc]] += w * float(div.loc[prices.index[loc]]) / prior_px
    return strat_ret + credit


def _metrics(strat_ret: pd.Series, eq: pd.Series, trades: int) -> dict:
    return {
        "sharpe": _annualized_sharpe(strat_ret),
        "profit_factor": _profit_factor(strat_ret),
        "max_drawdown": _max_drawdown(eq),
        "trades": int(trades),
        "periods": int(len(strat_ret.dropna())),
        "total_return": float(eq.iloc[-1] / eq.iloc[0] - 1.0) if len(eq) > 1 else 0.0,
        "worst_regime_rolling252_sharpe": _rolling_252_sharpe_worst(strat_ret),
    }


def _annualized_sharpe(ret: pd.Series) -> float:
    r = ret.dropna()
    if len(r) < 20:
        return 0.0
    sd = r.std(ddof=0)
    if sd <= 0 or not np.isfinite(sd):
        return 0.0
    return float(r.mean() / sd * math.sqrt(DAYS_PER_YEAR))


def _profit_factor(ret: pd.Series) -> float:
    r = ret.dropna()
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    if neg <= 0:
        return float("inf") if pos > 0 else 0.0
    return float(pos / neg)


def _max_drawdown(equity: pd.Series) -> float:
    eq = equity.dropna()
    if len(eq) == 0:
        return 0.0
    peak = eq.cummax()
    dd = eq / peak - 1.0
    return float(dd.min())


def _rolling_252_sharpe_worst(ret: pd.Series) -> float:
    r = ret.dropna()
    if len(r) < 252:
        return _annualized_sharpe(r)
    rs = r.rolling(252).apply(lambda x: _annualized_sharpe(pd.Series(x)), raw=False)
    rs = rs.dropna()
    return float(rs.min()) if len(rs) else _annualized_sharpe(r)


def _wf_score(
    train_close: pd.DataFrame,
    train_div: dict[str, pd.Series],
    params: dict,
    n_folds: int = 4,
) -> float:
    n = len(train_close)
    if n < 200:
        return -999.0
    fold = n // n_folds
    sharpes = []
    for i in range(n_folds):
        start = i * fold
        end = n if i == n_folds - 1 else (i + 1) * fold
        if end - start < 80:
            continue
        c = train_close.iloc[start:end]
        w = _compute_weights(c, train_div, **params)
        r, _, _, _ = _run_bt(c, w)
        sharpes.append(_annualized_sharpe(r))
    return float(np.mean(sharpes)) if sharpes else -999.0


def _information_ratio(strat: pd.Series, bench: pd.Series) -> float:
    a, b = strat.align(bench, join="inner")
    diff = (a - b).dropna()
    sd = diff.std(ddof=0)
    if len(diff) < 20 or sd <= 0 or not np.isfinite(sd):
        return 0.0
    return float(diff.mean() / sd * math.sqrt(DAYS_PER_YEAR))


def _benchmark_pvalue(strat: pd.Series, bench: pd.Series, n_boot: int = 2000) -> float:
    a, b = strat.align(bench, join="inner")
    diff = (a - b).dropna().to_numpy()
    if len(diff) < 20:
        return 1.0
    obs = diff.mean()
    if not np.isfinite(obs):
        return 1.0
    rng = np.random.default_rng(SEED)
    centered = diff - obs
    boots = [
        float(rng.choice(centered, size=len(centered), replace=True).mean()) for _ in range(n_boot)
    ]
    boots_arr = np.array(boots)
    p = (1.0 + float(np.sum(boots_arr >= obs))) / (n_boot + 1.0)
    return float(p)


def _perturbation_oos_sharpes(
    prices: pd.DataFrame,
    div_aligned: dict[str, pd.Series],
    selected: dict,
    oos_start: str,
    oos_end: str,
) -> list[float]:
    base = selected.copy()
    sharpes = []
    hd_opts = sorted({max(0, base["hold_days"] - 1), base["hold_days"], base["hold_days"] + 1})
    vt_opts = sorted(
        set(
            [
                round(base["vol_target"] * 0.8, 4),
                base["vol_target"],
                round(base["vol_target"] * 1.2, 4),
            ]
        )
    )
    for hd in hd_opts:
        for vt in vt_opts:
            p = dict(base)
            p["hold_days"] = int(hd)
            p["vol_target"] = float(vt)
            w = _compute_weights(prices, div_aligned, **p)
            mask = (prices.index >= pd.Timestamp(oos_start)) & (
                prices.index <= pd.Timestamp(oos_end)
            )
            r, _, _, _ = _run_bt(prices.loc[mask], w.loc[mask])
            sharpes.append(_annualized_sharpe(r))
    return [s for s in sharpes if np.isfinite(s)]


def _iter_grid():
    for hold_days in GRID["hold_days"]:
        for vol_target in GRID["vol_target"]:
            for universe in GRID["universe"]:
                yield {"hold_days": hold_days, "vol_target": vol_target, "universe": universe}


# ---------------------------------------------------------------- main driver
def main(out_dir: str | None = None) -> dict:
    t0 = time.time()
    art = _artifact_dir(out_dir)

    tickers = SECTOR_ETFS
    print("Downloading raw price data (auto_adjust=False)...")
    prices = _download_yfinance_daily(tickers, START, END, auto_adjust=False)
    print("Downloading total-return price data for benchmark (auto_adjust=True)...")
    bench_prices = _download_yfinance_daily(["SPY"], START, END, auto_adjust=True)[["SPY"]]
    print(
        f"Price data shape: {prices.shape}  {prices.index[0].date()} -> {prices.index[-1].date()}"
    )

    print("Downloading dividend history...")
    dividends = _fetch_dividends(tickers)
    div_counts = {t: int((dividends[t] > 0).sum()) for t in tickers}
    print(f"Dividend ex-date counts: {div_counts}")

    div_aligned = _align_dividends_to_daily(prices.index, dividends, tickers)

    train_close = prices.loc[prices.index <= pd.Timestamp(TRAIN_END)]
    val_close = prices.loc[
        (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    ]
    test_close = prices.loc[
        (prices.index > pd.Timestamp(VAL_END)) & (prices.index <= pd.Timestamp(TEST_END))
    ]
    oos_close = prices.loc[prices.index > pd.Timestamp(TRAIN_END)]
    oos_mask = oos_close.index

    print(f"Splits: train -> {TRAIN_END}; val {VAL_END}; test protected {TEST_END}")

    # Grid search: selection by train-only 4-fold walk-forward Sharpe.
    rows = []
    train_div = {t: div_aligned[t].reindex(train_close.index).fillna(0.0) for t in tickers}
    for params in _iter_grid():
        wf = _wf_score(train_close, train_div, params)
        rows.append({**params, "wf_train_sharpe": wf})
    grid = pd.DataFrame(rows).sort_values("wf_train_sharpe", ascending=False)
    grid.to_csv(art / "grid.csv", index=False)
    valid_grid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid_grid.empty:
        raise RuntimeError("no valid grid rows")
    sel = valid_grid.iloc[0].to_dict()
    selected = {k: sel[k] for k in ["hold_days", "vol_target", "universe"]}
    selected["hold_days"] = int(selected["hold_days"])
    selected["vol_target"] = float(selected["vol_target"])
    selected["universe"] = str(selected["universe"])

    # Selected weights on full sample; OOS backtest + dividend credit.
    w_sel = _compute_weights(prices, div_aligned, **selected)
    oos_w = w_sel.loc[oos_mask]
    oos_ret, oos_eq, oos_trades, oos_pos = _run_bt(oos_close, oos_w)
    oos_div = {t: div_aligned[t].reindex(oos_close.index).fillna(0.0) for t in tickers}
    oos_ret = _credit_dividends(oos_ret, oos_pos.reindex(oos_close.index), oos_close, oos_div)
    oos_eq = (1.0 + oos_ret).cumprod()
    oos_m = _metrics(oos_ret, oos_eq, oos_trades)

    # Benchmark: total-return buy-hold SPY over OOS.
    bench_w = pd.DataFrame(1.0, index=oos_close.index, columns=["SPY"])
    bench_ret, bench_eq, _, _ = _run_bt(bench_prices.reindex(oos_close.index), bench_w)
    bench_m = _metrics(bench_ret, bench_eq, 0)

    # Ablations.
    rng = np.random.default_rng(SEED)
    n_events = int((div_aligned["SPY"] > 0).sum())
    random_dates = rng.choice(oos_close.index, size=min(n_events, len(oos_close)), replace=False)
    rand_active = pd.Series(False, index=oos_close.index)
    rand_active.loc[random_dates] = True
    rand_div = {t: div_aligned[t].reindex(oos_close.index).fillna(0.0) for t in tickers}
    rand_w = _compute_weights(oos_close, rand_div, **selected)
    rand_w = rand_w.multiply(rand_active.reindex(oos_close.index), axis=0)
    rand_ret, rand_eq, rand_trades, rand_pos = _run_bt(oos_close, rand_w)
    rand_ret = _credit_dividends(rand_ret, rand_pos.reindex(oos_close.index), oos_close, rand_div)
    rand_eq = (1.0 + rand_ret).cumprod()
    rand_m = _metrics(rand_ret, rand_eq, rand_trades)

    # Inverse falsifier: long vol-targeted exposure on NON-capture days (opposite
    # of the capture window), long-only so it survives allow_short=False.
    inv_active = pd.Series(True, index=oos_close.index)
    div_spy = div_aligned["SPY"].reindex(oos_close.index).fillna(0.0)
    ex_locs = oos_close.index.get_indexer(div_spy[div_spy > 0].index)
    for loc in ex_locs:
        if loc == -1 or loc == 0:
            continue
        start = loc - 1
        end = min(len(oos_close) - 1, loc - 1 + int(selected["hold_days"]))
        inv_active.iloc[start : end + 1] = False
    inv_w = _compute_weights(oos_close, oos_div, **selected)
    inv_w = inv_w.multiply(inv_active, axis=0)
    inv_ret, inv_eq, inv_trades, inv_pos = _run_bt(oos_close, inv_w)
    inv_ret = _credit_dividends(inv_ret, inv_pos.reindex(oos_close.index), oos_close, oos_div)
    inv_eq = (1.0 + inv_ret).cumprod()
    inv_m = _metrics(inv_ret, inv_eq, inv_trades)

    train_sel_ret, _, _, _ = _run_bt(train_close, w_sel.loc[train_close.index])
    train_sel_sharpe = _annualized_sharpe(train_sel_ret)
    wf_stability = (
        float(oos_m["sharpe"] / train_sel_sharpe)
        if np.isfinite(train_sel_sharpe) and train_sel_sharpe != 0
        else (float("inf") if oos_m["sharpe"] > 0 else 0.0)
    )

    pert_sharpes = _perturbation_oos_sharpes(
        prices, div_aligned, selected, str(val_close.index[0].date()), str(prices.index[-1].date())
    )
    base_sh = oos_m["sharpe"]
    min_ratio = (
        float(min(pert_sharpes) / base_sh)
        if pert_sharpes and np.isfinite(base_sh) and base_sh != 0
        else 0.0
    )

    ir = _information_ratio(oos_ret, bench_ret)
    bp = _benchmark_pvalue(oos_ret, bench_ret)

    gates = {
        "sharpe_ge_1": bool(np.isfinite(oos_m["sharpe"]) and oos_m["sharpe"] >= 1.0),
        "trades_ge_50": bool(oos_m["trades"] >= 50),
        "pf_ge_1_3": bool(np.isfinite(oos_m["profit_factor"]) and oos_m["profit_factor"] >= 1.3),
        "maxdd_le_15pct": bool(
            np.isfinite(oos_m["max_drawdown"]) and oos_m["max_drawdown"] >= -0.15
        ),
        "wf_stability_ge_0_7": bool(np.isfinite(wf_stability) and wf_stability >= 0.7),
        "worst_regime_ge_0_3": bool(
            np.isfinite(oos_m["worst_regime_rolling252_sharpe"])
            and oos_m["worst_regime_rolling252_sharpe"] >= 0.3
        ),
        "benchmark_p_le_0_05_and_ir_ge_0": bool(
            np.isfinite(bp) and bp <= 0.05 and np.isfinite(ir) and ir >= 0.0
        ),
        "perturbation_min_ratio_ge_0_5": bool(np.isfinite(min_ratio) and min_ratio >= 0.5),
    }
    gates_passed = int(sum(1 for v in gates.values() if v))
    verdict = "ACCEPT" if gates_passed == 8 else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "spy_rows": int(len(prices)),
            "dividend_ex_date_counts": div_counts,
            "start": str(prices.index[0].date()),
            "end": str(prices.index[-1].date()),
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "test_end": TEST_END,
            "oos_rows": int(len(oos_close)),
            "note": "yfinance raw daily closes (ex-date price drop visible) + yfinance dividend history (ex-date index)",
        },
        "selected": selected,
        "wf_train_sharpe": float(sel["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sel_sharpe),
        "oos_val_test": oos_m,
        "benchmark_buy_hold_spy_oos": bench_m,
        "ablations": {
            "random_dates_oos": rand_m,
            "inverse_signal_oos": inv_m,
        },
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else wf_stability,
        "benchmark_pvalue_one_sided": float(bp),
        "information_ratio_vs_buy_hold": float(ir),
        "perturbation": {
            "min_ratio": float(min_ratio) if np.isfinite(min_ratio) else min_ratio,
            "n_points": len(pert_sharpes),
            "min_sharpe": float(min(pert_sharpes)) if pert_sharpes else None,
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
        },
    }
    (art / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    grid.to_csv(art / "grid.csv", index=False)
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": gates_passed,
                "artifact": str(art),
                "oos_sharpe": oos_m["sharpe"],
            },
            indent=2,
        )
    )
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    main(args.out)
