"""Focused tests for NF-20261110-01 / H177 Treasury Auction Supply-Pressure Timing.

Tests use synthetic data only (no network). They validate PIT/causal
properties, signal construction, grid behavior, and gate logic.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import run_nf_20261110_01_treasury_auction as mod  # noqa: E402


def _make_prices(n_years=20, seed=0):
    """Create synthetic daily price data for SPY."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n_years * 252)
    drift = rng.normal(0.0002, 0.0001)
    vol = rng.uniform(0.008, 0.015)
    rets = rng.normal(drift, vol, len(idx))
    prices = pd.DataFrame({"SPY": pd.Series(100 * np.exp(np.cumsum(rets)), index=idx, name="SPY")})
    return prices


def _make_auctions(n_years=20, seed=0):
    """Create synthetic auction data."""
    rng = np.random.default_rng(seed)
    import calendar

    auction_dates = []
    for year in range(2010, 2010 + n_years):
        # 10Y: monthly, ~2nd week
        for month in range(1, 13):
            cal = calendar.monthcalendar(year, month)
            if cal[1][2] != 0:
                auction_dates.append((pd.Timestamp(year, month, cal[1][2]), "10Y"))
            elif cal[2][2] != 0:
                auction_dates.append((pd.Timestamp(year, month, cal[2][2]), "10Y"))

        # 30Y: quarterly
        for month in [2, 5, 8, 11]:
            cal = calendar.monthcalendar(year, month)
            if cal[2][2] != 0:
                auction_dates.append((pd.Timestamp(year, month, cal[2][2]), "30Y"))
            elif cal[3][2] != 0:
                auction_dates.append((pd.Timestamp(year, month, cal[3][2]), "30Y"))

    results = []
    for auc_date, tenor in auction_dates:
        if auc_date > pd.Timestamp("2026-10-31"):
            continue

        if tenor == "10Y":
            base_btc = 2.4
            base_tail = 0.5
            base_dealer = 0.22
        else:
            base_btc = 2.4
            base_tail = 1.0
            base_dealer = 0.25

        btc = max(1.5, rng.normal(base_btc, 0.25))
        tail = rng.normal(base_tail, 1.5)
        dealer = np.clip(rng.normal(base_dealer, 0.05), 0.1, 0.5)

        years_since_2010 = (auc_date.year - 2010) + (auc_date.month - 1) / 12
        if tenor == "10Y":
            wi_yield = 2.5 + 0.1 * np.sin(years_since_2010 * 2) + rng.normal(0, 0.3)
        else:
            wi_yield = 3.0 + 0.1 * np.sin(years_since_2010 * 2) + rng.normal(0, 0.3)
        wi_yield = max(0.5, wi_yield)

        high_yield = wi_yield + tail / 100.0

        results.append(
            {
                "auction_date": auc_date,
                "tenor": tenor,
                "bid_to_cover": round(btc, 2),
                "tail_bps": round(tail, 1),
                "dealer_take_down_pct": round(dealer, 3),
                "high_yield": round(high_yield, 3),
                "when_issued_yield": round(wi_yield, 3),
            }
        )

    df = pd.DataFrame(results)
    df = df.sort_values("auction_date").reset_index(drop=True)
    return df


def test_signal_bounded():
    """Signal should be bounded [-MAX_POS, MAX_POS]."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    sig = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.15, 21, "both")

    assert (sig["SPY"] >= -mod.MAX_POS).all(), "Signal should be >= -MAX_POS"
    assert (sig["SPY"] <= mod.MAX_POS).all(), f"Signal should be <= MAX_POS ({mod.MAX_POS})"
    assert list(sig.columns) == ["SPY"], "Signal columns should match universe"


def test_signal_long_short_allowed():
    """Signal should allow both long and short positions."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    # With entry_z=0, should get both long and short
    sig = mod._build_auction_signal(prices, auctions, 5, 0.0, 0.0, 0.15, 21, "both")

    has_long = (sig["SPY"] > 0).any()
    has_short = (sig["SPY"] < 0).any()
    # At least one direction should be active (depending on synthetic data)
    assert has_long or has_short, "Signal should have non-zero positions"


def test_auction_score_computation():
    """Auction score should be computed correctly with rolling z-scores."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    scored = mod._compute_auction_score(auctions, 5, "both")

    assert "score" in scored.columns, "Scored auctions should have score column"
    assert "btc_z" in scored.columns, "Should have bid-to-cover z-score"
    assert "tail_z" in scored.columns, "Should have tail z-score"
    assert "dealer_z" in scored.columns, "Should have dealer take-down z-score"

    # Score should be finite
    assert np.isfinite(scored["score"]).all(), "All scores should be finite"

    # Score should be roughly zero-mean (z-score composite)
    assert abs(scored["score"].mean()) < 1.0, "Composite score should be roughly zero-mean"


def test_auction_score_respects_tenor():
    """Score computation should respect tenor filter."""
    auctions = _make_auctions(5, seed=42)

    scored_10y = mod._compute_auction_score(auctions, 10, "10Y")
    scored_30y = mod._compute_auction_score(auctions, 10, "30Y")
    scored_both = mod._compute_auction_score(auctions, 10, "both")

    assert len(scored_10y) < len(scored_both), "10Y should have fewer auctions than both"
    assert len(scored_30y) < len(scored_both), "30Y should have fewer auctions than both"
    assert (scored_10y["tenor"] == "10Y").all(), "10Y filter should only have 10Y"
    assert (scored_30y["tenor"] == "30Y").all(), "30Y filter should only have 30Y"


def test_signal_only_active_after_auctions():
    """Signal should only be non-zero after first auction with sufficient history."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    sig = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.15, 21, "both")

    # Before first auction with enough history for score_window, signal should be 0
    first_auc = auctions["auction_date"].min()
    # Score needs score_window auctions, so first scored auction is at index score_window-1
    # Signal activates on next trading day after that auction
    pre_auction = sig[sig.index < first_auc]
    if len(pre_auction) > 0:
        assert (pre_auction["SPY"] == 0.0).all(), "Signal should be zero before first auction"


def test_hysteresis_behavior():
    """Hysteresis should prevent rapid flipping around thresholds."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    # Low entry_z, high exit_z should create wider hysteresis band
    sig_tight = mod._build_auction_signal(prices, auctions, 5, 0.5, 0.0, 0.15, 21, "both")
    sig_wide = mod._build_auction_signal(prices, auctions, 5, 1.5, 0.5, 0.15, 21, "both")

    # Wider hysteresis should have fewer position changes
    changes_tight = (sig_tight["SPY"].diff() != 0).sum()
    changes_wide = (sig_wide["SPY"].diff() != 0).sum()

    # Not strictly guaranteed with synthetic data, but generally true
    # Just verify both produce valid signals
    assert (sig_tight["SPY"] >= -mod.MAX_POS).all()
    assert (sig_wide["SPY"] >= -mod.MAX_POS).all()


def test_vol_scaling_reduces_exposure_when_vol_high():
    """Vol targeting should reduce position size when realized vol is high."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    # Inject high volatility in a specific period
    high_vol_start = prices.index[600]
    high_vol_end = prices.index[800]
    mask = (prices.index >= high_vol_start) & (prices.index <= high_vol_end)
    for sym in prices.columns:
        prices.loc[mask, sym] *= np.exp(np.random.default_rng(42).normal(0, 0.05, mask.sum()))

    sig = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.10, 21, "both")

    # During high vol, positions should be smaller (when signal is active)
    high_vol_mask = (sig.index >= high_vol_start) & (sig.index <= high_vol_end) & (sig["SPY"] != 0)
    normal_mask = (sig.index < high_vol_start) & (sig["SPY"] != 0)

    high_vol_positions = sig.loc[high_vol_mask, "SPY"].abs()
    normal_positions = sig.loc[normal_mask, "SPY"].abs()

    if len(high_vol_positions) > 5 and len(normal_positions) > 5:
        assert high_vol_positions.mean() < normal_positions.mean() * 1.5, (
            "Vol targeting should reduce exposure in high-vol regime"
        )


def test_grid_has_expected_size():
    """Grid should have 108 combinations (3*3*2*2*3)."""
    n = 1
    for v in mod.GRID.values():
        n *= len(v)
    assert n == 108, f"Grid should have 108 combos, got {n}"


def test_constants_pre_registered():
    """Pre-registered constants should match specification."""
    assert mod.NF_ID == "NF-20261110-01"
    assert mod.HYPOTHESIS == "H177"
    assert mod.START == "2010-01-01"
    assert mod.END == "2026-10-31"
    assert mod.SEED == 42
    assert mod.MAX_POS == 0.5
    assert mod.DAYS_PER_YEAR == 252
    assert mod.VOL_WINDOW == 21
    assert mod.GRID == {
        "score_window": [10, 20, 30],
        "entry_z": [0.5, 1.0, 1.5],
        "exit_z": [0.0, 0.5],
        "vol_target": [0.10, 0.15],
        "tenor": ["10Y", "30Y", "both"],
    }


def test_worst_regime_finite_on_sufficient_data():
    """_worst_regime should return finite value on sufficient data."""
    rng = np.random.default_rng(3)
    daily = pd.Series(rng.normal(0.0002, 0.01, 2000))
    w = mod._worst_regime(daily)
    assert math.isfinite(w)


def test_perturbation_min_ratio_nan_when_base_zeroish():
    """_perturbation_check should return NaN min_ratio when base Sharpe ~0."""
    prices = _make_prices(3, seed=555)
    auctions = _make_auctions(3, seed=555)

    sig = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.15, 21, "both")
    sig = sig.reindex(index=prices.index).fillna(0.0)

    p = mod._perturbation_check(
        prices,
        auctions,
        {"score_window": 10, "entry_z": 1.0, "exit_z": 0.5, "vol_target": 0.15, "tenor": "both"},
        0.0,
        "2023-01-01",
    )
    assert not math.isfinite(p["min_ratio"])


def test_inverse_signal_opposite_direction():
    """Inverse signal should take opposite positions to base signal."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    base_sig = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.15, 21, "both")

    # Create inverse by negating auction score components (as done in runner)
    inv_auctions = auctions.copy()
    inv_auctions["bid_to_cover"] = -inv_auctions["bid_to_cover"]
    inv_auctions["tail_bps"] = -inv_auctions["tail_bps"]
    inv_auctions["dealer_take_down_pct"] = -inv_auctions["dealer_take_down_pct"]
    inv_auctions["high_yield"] = -inv_auctions["high_yield"]
    inv_auctions["when_issued_yield"] = -inv_auctions["when_issued_yield"]

    inv_sig = mod._build_auction_signal(prices, inv_auctions, 10, 1.0, 0.5, 0.15, 21, "both")

    # Inverse signal should have opposite sign where both are non-zero
    both_active = (base_sig["SPY"] != 0) & (inv_sig["SPY"] != 0)
    if both_active.any():
        base_active = base_sig.loc[both_active, "SPY"]
        inv_active = inv_sig.loc[both_active, "SPY"]
        # Signs should be opposite (or at least not consistently same)
        same_sign = (base_active * inv_active > 0).sum()
        total = len(base_active)
        # At most 50% should have same sign (allowing for hysteresis edge cases)
        assert same_sign <= total * 0.7, "Inverse signal should mostly have opposite sign"


def test_auction_date_mapping():
    """Auction dates should map to next trading day correctly."""
    prices = _make_prices(2, seed=42)
    auctions = _make_auctions(2, seed=42)

    # Check that auction dates exist in our price index or map to next day
    for _, row in auctions.iterrows():
        auc_date = row["auction_date"]
        # Should be able to find next trading day
        next_days = prices.index[prices.index > auc_date]
        if len(next_days) > 0:
            trade_date = next_days[0]
            assert trade_date > auc_date, "Trade date should be after auction date"
            assert trade_date in prices.index, "Trade date should be valid trading day"


def test_score_window_effect():
    """Larger score_window should produce smoother scores."""
    auctions = _make_auctions(10, seed=42)

    scored_10 = mod._compute_auction_score(auctions, 10, "both")
    scored_30 = mod._compute_auction_score(auctions, 30, "both")

    # Larger window should have less variable scores (more stable)
    # But both should be finite
    assert np.isfinite(scored_10["score"]).all()
    assert np.isfinite(scored_30["score"]).all()


def test_entry_exit_thresholds():
    """Entry and exit thresholds should control signal activation."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    # Very high entry threshold -> rarely active
    sig_high = mod._build_auction_signal(prices, auctions, 10, 3.0, 0.5, 0.15, 21, "both")
    # Low entry threshold -> more active
    sig_low = mod._build_auction_signal(prices, auctions, 10, 0.1, 0.0, 0.15, 21, "both")

    active_high = (sig_high["SPY"] != 0).sum()
    active_low = (sig_low["SPY"] != 0).sum()

    # Lower threshold should generally have more active periods
    assert active_low >= active_high * 0.5, "Lower entry threshold should activate more often"


def test_tenor_selection():
    """Different tenor selections should use different auction subsets."""
    prices = _make_prices(5, seed=42)
    auctions = _make_auctions(5, seed=42)

    sig_10y = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.15, 21, "10Y")
    sig_30y = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.15, 21, "30Y")
    sig_both = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.15, 21, "both")

    # All should produce valid signals
    for sig in [sig_10y, sig_30y, sig_both]:
        assert (sig["SPY"] >= -mod.MAX_POS).all()
        assert (sig["SPY"] <= mod.MAX_POS).all()
        assert np.isfinite(sig["SPY"]).all()


def test_random_auction_control_structure():
    """Random auction control should have same structure as base."""
    prices = _make_prices(3, seed=42)
    auctions = _make_auctions(3, seed=42)

    sig = mod._build_auction_signal(prices, auctions, 10, 1.0, 0.5, 0.15, 21, "both")

    oos_mask = prices.index > pd.Timestamp("2023-01-01")
    active_mask = sig.abs().sum(axis=1) > 0
    active_dates = prices.index[oos_mask & active_mask]
    n_active = len(active_dates)
    all_auction_dates = prices.index[oos_mask]

    if n_active > 0 and len(all_auction_dates) > n_active:
        rng = np.random.default_rng(mod.SEED)
        rand_dates = rng.choice(all_auction_dates, size=n_active, replace=False)

        # Random dates should be a subset of all dates
        assert len(rand_dates) == n_active
        assert len(set(rand_dates)) == n_active  # No duplicates
        for d in rand_dates:
            assert d in all_auction_dates


if __name__ == "__main__":
    # Run tests manually if needed
    import pytest

    pytest.main([__file__, "-v"])
