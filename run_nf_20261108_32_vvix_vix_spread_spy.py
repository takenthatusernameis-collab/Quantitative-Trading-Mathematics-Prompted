"""NF-20261108-32 / H159 (Cycle 73): SPY timing from VVIX-vs-VIX implied-volatility
regime (volatility-of-volatility / VVIX-VIX spread transmission).

Repo-relative novelty (honest). No executed NF/H in this repo uses the *VVIX minus
VIX* spread (volatility-of-implied-volatility level minus VIX level) as a continuous
SPY equity-timing observable. H158 (NF-20261108-30) used VIX minus SPY *realized*
vol (implied-realized variance risk premium on the *same* index); H158's VIX term-
structure neighbors (H86/H123/H131/H104/H89/H125/H126) use VIX *level* or VIX *term
structure* (VIX vs VIX3M/VIX9D) or cross-asset implied-vol *spreads* (OVX-VIX H125,
GVZ-VIX H126). VVIX is the CBOE volatility-of-implied-volatility index: a
*second-order* implied-vol measure, not a VIX level, not a VIX term-structure slope,
and not an implied-minus-realized spread. The VVIX-VIX *spread* as a continuous
de-risking input is repo-new. Honest adjacency to the z-score / continuous de-risking
/ vol-target statistical form (H138/H139/H151/H156/H158) is acknowledged; novelty is
scored repo-relative on the VVIX-VIX observable/category, not as a wholly new
statistical method.

Mechanism (volatility-of-volatility / tail-hedging-demand transmission). VVIX
measures the 30-day implied volatility *of* VIX futures options = the price of
tail/convexity hedging. VIX is the 30-day implied volatility of SPY. The spread
VVIX - VIX proxies the *excess* cost of tail protection over baseline implied vol:
abnormally high VVIX relative to VIX = hedgers paying a large premium for crash
protection = equity risk premia elevated / fear regime -> reduce vol-targeted long
SPY exposure continuously. Normal or negative spread = full exposure. Causal chain:
VVIX close t and VIX close t -> trailing spread and z-score at close t -> exposure
weight applied to return t+1 (engine signals.shift(1)), no look-ahead.

Observable (past-only, PIT, free yfinance): SPY, ^VIX, ^VVIX daily auto-adjust Close.
`spread_t = VVIX_t - VIX_t`; `z_t = (spread_t - rolling_mean(spread,z_window))
/ rolling_std(spread,z_window)`.

Null (H0). Trailing VVIX-VIX implied-volatility-of-volatility spread (z-score)
contains no incremental SPY timing information; OOS gates fail vs
buy-hold / random-exposure.

Pre-registration (Cycle 73, decision-ready before validation outcomes).
NF-ID NF-20261108-32. Hypothesis H159. Universe SPY (traded) + ^VIX, ^VVIX
(signal), yfinance daily auto-adjust Close (free, PIT). Sample
2010-01-04->2025-01-03 (train 2516 / val 505 / test 755, aligned; ^VVIX has 9
NaN rows in the raw panel that are dropped by the alignment+dropna screen, so the
final panel is slightly shorter and train/val/test counts are computed from the
aligned frame). Signal: z-score of trailing (VVIX - VIX) spread over z_window
(past-only); continuous stress on positive z = (z.clip(0)/entry_scale).clip(0,1);
exposure (1-stress)*vol_target*vscale; 1-bar delay via engine signals.shift(1);
Equity CostModel defaults (1bp commission + 1bp spread); long-only, max exposure
scaled to MAX_POS=0.5. Bounded grid: z_window {126,252} x entry_scale {1.0,2.0} x
vol_target {0.10,0.15} (8 combos); train-only 4-fold WF selection by mean train
Sharpe; Test protected. No src/qtr change.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-exposure-matched, inverse regime (de-risk
when VVIX-VIX spread abnormally LOW / negative z -- pre-registered falsifier
of the tail-hedging-demand -> de-risk mapping).

Falsifiers: random-exposure comparable or better; inverse outperforms;
benchmark fails; fragile; worst-regime collapse.
"""