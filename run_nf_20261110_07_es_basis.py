"""NF-20261110-07 / H180 (Cycle 94): S&P 500 E-mini Futures-to-Spot Basis Regime Timing.

Repo-new root family: futures-basis / index-arbitrage transmission. Distinct from all
exhausted families: TSMOM (H1/H7-12/21-23/25), cross-sectional momentum (H2/H16),
regime-gated vol momentum (H3/H5/H6), VRP (H17), VIX-complex implied families
(H86/H89/H100/H104/H105/H158/H159/H165/H167), realized-moment stress (H122/H128/H135),
macro/rates/curve (H171/H173/H175/H177), calendar (H91/H140/H142/H168), relmom
(H144/H145/H152/H157), short-constraint/limits-to-arbitrage (H179), and options
sentiment/positioning (H178). Mechanism: the ES-to-SPY cash-futures basis is a direct
index-arbitrage linkage (cost-of-carry + funding + borrow + roll), not a momentum,
volatility, macro, calendar, or sentiment channel.

Mechanism. The E-mini S&P 500 futures (ES=F) trade vs the SPY ETF basket. When the
basis is rich (ES elevated vs SPY), futures are overpriced relative to the cash index:
arbitrageurs buy SPY / sell ES (cash-and-carry), which is a funded, near-riskless
spread that should compress. When the basis is cheap (ES depressed vs SPY), the
reverse arbitrage (long ES / short SPY) is constrained by short-sale friction and
borrow cost, so the mispricing can persist. The basis therefore embeds both a
cost-of-carry signal (level) and a mean-reversion signal (deviation from fair value).
A trailing z-score of the normalized basis gates vol-targeted long SPY exposure:
reduce/short when basis is rich (futures overpriced -> SPY relatively cheap -> mean
reversion favors SPY), increase long when basis is cheap (futures underpriced ->
arbitrage compression favors SPY). Causal chain: basis extremes -> cash/futures
arbitrage flow / cost-of-carry imbalance -> basis compression -> SPY relative strength.

Causal chain (PIT). ES=F and SPY daily closes are both known at the daily close; the
basis at close t is computed from close-t prices and enters the position for the
t->t+1 return via engine `signals.shift(1)` (position at close t earns return t->t+1).
Strictly causal: no future-day basis is used to set a same-day position.

Observable (past-only, PIT, free/public). ES=F (yfinance auto-adjusted daily Close),
SPY (yfinance daily Close). Basis = ES_close - SPY_close (points); normalized basis
z = (basis - rolling_mean) / rolling_std over a past-only window. Both series have
full free history 2010-01-04 -> 2026-11-09 (verified: 4177/4240 rows, no nulls).
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

EXPERIMENT = "nf_20261110_07_es_basis"
NF_ID = "NF-20261110-07"
HYPOTHESIS = "H180"
START = "2010-01-01"
END = "2026-11-09"
MAX_POS = 0.5
SEED = 42
DAYS_PER_YEAR = 252
VOL_WINDOW = 21
ES_TICKER = "ES=F"
SPY_TICKER = "SPY"

GRID = {
    "basis_window": [63, 126, 252],
    "entry_z": [0.5, 1.0, 1.5],
    "exit_z": [0.0, 0.5],
    "vol_target": [0.10, 0.15],
}

# Gates (OOS Val+Test, fail-closed).
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
def _download_yfinance_daily(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is required")
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
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


def _basis_zscore(basis: pd.Series, window: int) -> pd.Series:
    """Rolling z-score of the ES-to-SPY basis using past-only windows (no lookahead)."""
    s = basis.astype(float)
    minp = max(2, window // 2)
    m = s.rolling(window, min_periods=minp).mean()
    sd = s.rolling(window, min_periods=minp).std(ddof=0)
    return (s - m) / sd.replace(0.0, np.nan)


def _compute_weights(
    prices: pd.DataFrame,
    basis_z: pd.Series,
    basis_window: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
) -> pd.DataFrame:
    """Hysteresis state machine on the trailing basis z-score.

    Rich basis (z >= entry_z) -> futures overpriced -> reduce/short long SPY.
    Cheap basis (z <= -entry_z) -> futures underpriced -> increase long SPY.
    """
    tickers = prices.columns.tolist()
    weights = pd.DataFrame(0.0, index=prices.index, columns=tickers)

    z = basis_z.reindex(prices.index).astype(float)
    position = 0.0
    w_series = pd.Series(0.0, index=prices.index)
    for i in range(len(prices)):
        z_val = z.iloc[i] if i < len(z) else np.nan
        if np.isnan(z_val):
            w_series.iloc[i] = position
            continue
        if position >= 0.0:
            if z_val >= entry_z:
                position = -1.0
            elif z_val <= -entry_z:
                position = 1.0
            elif exit_z > 0.0 and position > 0.0 and z_val >= exit_z:
                position = 0.0
            elif exit_z > 0.0 and position < 0.0 and z_val <= -exit_z:
                position = 0.0
        else:
            if z_val <= -entry_z:
                position = 1.0
            elif z_val >= entry_z:
                position = -1.0
            elif exit_z > 0.0 and position < 0.0 and z_val <= -exit_z:
                position = 0.0
            elif exit_z > 0.0 and position > 0.0 and z_val >= exit_z:
                position = 0.0
        w_series.iloc[i] = position

    returns = prices[SPY_TICKER].pct_change()
    vol = returns.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(DAYS_PER_YEAR)
    vol_scale = (vol_target / vol.replace(0, np.nan)).clip(0.0, 3.0).fillna(0.0)
    w_vol = (w_series * vol_scale).clip(-MAX_POS, MAX_POS)
    weights[SPY_TICKER] = w_vol
    for c in weights.columns:
        if c != SPY_TICKER:
            weights[c] = 0.0
    return weights


def _run_bt(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    allow_short: bool = True,
) -> tuple[pd.Series, pd.Series, int]:
    cfg = BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        allow_short=allow_short,
    )
    res = run_backtest(close, weights, cfg)
    strat_ret = res.returns.reindex(close.index).fillna(0.0).astype(float)
    eq = res.equity_curve.reindex(close.index).astype(float)
    pos = res.positions.reindex(close.index).fillna(0.0)
    trades = int((pos.diff().abs() > 1e-12).sum().sum())
    return strat_ret, eq, trades


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


def _wf_score(
    train_close: pd.DataFrame,
    train_basis_z: pd.Series,
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
        z = train_basis_z.iloc[start:end]
        w = _compute_weights(c, z, **params)
        r, _, _ = _run_bt(c, w)
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
        float(rng.choice(centered, size=len(centered), replace=True).mean())
        for _ in range(n_boot)
    ]
    boots_arr = np.array(boots)
    p = (1.0 + float(np.sum(boots_arr >= obs))) / (n_boot + 1.0)
    return float(p)


def _time_split(index: pd.DatetimeIndex) -> tuple[str, str]:
    n = len(index)
    i1 = index[n // 2]
    i2 = index[(3 * n) // 4]
    return str(i1.date()), str(i2.date())


def _perturbation_oos_sharpes(
    prices: pd.DataFrame,
    basis_z: pd.Series,
    selected: dict,
    val_start: str,
    test_end: str,
) -> list[float]:
    base = selected.copy()
    sharpes = []
    bw_opts = sorted(
        set(
            [
                max(3, int(round(base["basis_window"] * 0.8))),
                base["basis_window"],
                min(60, int(round(base["basis_window"] * 1.2))),
            ]
        )
    )
    ez_opts = sorted(
        set([round(base["entry_z"] * 0.8, 4), base["entry_z"], round(base["entry_z"] * 1.2, 4)])
    )
    xz_opts = sorted(
        set([round(base["exit_z"] * 0.8, 4), base["exit_z"], round(base["exit_z"] * 1.2, 4)])
    )
    vt_opts = sorted(
        set(
            [
                round(base["vol_target"] * 0.8, 4),
                base["vol_target"],
                round(base["vol_target"] * 1.2, 4),
            ]
        )
    )
    for bw in bw_opts:
        for vt in vt_opts:
            for ez in ez_opts:
                for xz in xz_opts:
                    p = dict(base)
                    p["basis_window"] = int(bw)
                    p["vol_target"] = float(min(max(vt, 0.02), 0.5))
                    p["entry_z"] = float(ez)
                    p["exit_z"] = float(xz)
                    w = _compute_weights(prices, basis_z, **p)
                    mask = (prices.index >= pd.Timestamp(val_start)) & (
                        prices.index <= pd.Timestamp(test_end)
                    )
                    r, _, _ = _run_bt(prices.loc[mask], w.loc[mask])
                    sharpes.append(_annualized_sharpe(r))
    return [s for s in sharpes if np.isfinite(s)]
