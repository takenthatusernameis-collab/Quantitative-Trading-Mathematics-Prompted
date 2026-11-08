"""NF-20261108-17 / H151 (Cycle 65): SPY timing from short-rate level
(13-week T-bill yield) regime via free ETF proxies.

Repo-relative novelty (honest). No executed NF/H in this repo uses a *short-rate
level* (as opposed to a term *spread* or *slope*) as the SPY timing observable.
H141 (NF-20261108-02, REJECT 5/8) tested TLT-vs-SHY Treasury term-spread
momentum (duration-vs-cash relative momentum, a *spread* of two Treasury ETFs).
H92/H96/H145 used equity-vs-duration or equity-vs-bond relative momentum /
correlation. H151 is the first repo execution of a *short-rate level* channel:
the level of the risk-free short rate, proxied by the SHY / BIL / MINT
short-Treasury ETF cumulative return (a traded proxy for the 3-month T-bill
yield), used as a continuous risk-on / risk-off scaling for a vol-targeted long
SPY position.

Mechanism (short-rate level / monetary-tightness transmission). When the
short-term risk-free rate is abnormally elevated relative to its trailing
history, real rates are high, financial conditions are tight, and equity risk
premia are compressed; the pre-registered rule reduces vol-targeted long SPY
exposure continuously as the short-rate z-score rises. When the short rate is
abnormally low (loose conditions), exposure is full. Causal chain: short-rate
level at close t -> z-score regime -> exposure weight applied to return t+1
(engine signals.shift(1)), no look-ahead.

Observable (past-only, PIT, free yfinance): SHY (iShares 1-3Y Treasury Bond
ETF, traded proxy for the 3-month T-bill yield), SPY. The *level* signal is
SHY's trailing cumulative return (price appreciation of a short-duration
Treasury ETF tracks the short end of the curve: falling yields -> SHY price up,
rising yields -> SHY price down). z-score of SHY cumulative return over
shy_window, standardized over z_window.

Note on ^IRX: the direct 13-week T-bill yield index is NOT used. yfinance
returns ^IRX with 7 non-positive values (min -0.105, 2020-03-19/20/23), which
the engine's fail-closed non-positive-price screen rejects. SHY/BIL/MINT are
clean (verified 2026-11-08: 3776 rows each, 0 non-positive, 2010-2025) and are
used instead. Honest adjacency to the rates domain (H141 spread, NF-11 slope)
is disclosed: H151 tests a *level* channel via a traded short-Treasury ETF, not
a spread or slope of two rate instruments.

Null (H0). Trailing short-rate level (SHY cumulative-return z-score) contains
no incremental SPY timing information; OOS gates fail vs buy-hold / random-exposure.

Pre-registration (Cycle 65, decision-ready before validation outcomes).
NF-ID NF-20261108-17. Universe SPY (traded) + SHY/BIL/MINT (signal proxies),
yfinance daily auto-adjust Close (free, PIT). Sample 2010-01-04->2025-01-03
(train 2516 / val 505 / test 755, aligned). Signal: z-score of trailing SHY
cumulative return over shy_window, standardized over z_window (past-only);
continuous stress on positive z = (z.clip(0)/entry_scale).clip(0,1); exposure
(1-stress)*vol_target*vscale; 1-bar delay; Equity CostModel defaults
(1bp commission + 1bp spread); long-only, max exposure vol_target (scaled to
MAX_POS=0.5). Bounded grid: shy_window {21,63,126} x z_window {126,252} x
entry_scale {1.0,2.0} x vol_target {0.10,0.15} (24 combos); train-only 4-fold
WF selection by mean train Sharpe; Test protected. No src/qtr change.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-exposure-matched, inverse regime (de-risk
when short-rate level is abnormally LOW / negative z -- pre-registered
falsifier: if the mechanism is loose-conditions risk-on, the inverse should
not outperform).

Falsifiers: random-exposure comparable or better; inverse outperforms;
benchmark fails; fragile; worst-regime collapse.
"""
