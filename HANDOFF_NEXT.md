# HANDOFF_NEXT (Cycle 83)

## Completed this session (Cycle 83)
- **H169 / NF-20261109-14 — Overnight futures (ES/NQ) lead-lag to cash session (SPY/QQQ) — REAL EXECUTION: REJECT 4/8.**
  - Artifact: `.experiments/nf_runs/nf_20261109_14_overnight_futures_leadlag/summary.json` (+ `grid.csv`, `data_meta.json`, 0.63s)
  - Runner: `run_nf_20261109_14_overnight_futures_leadlag.py`; Tests: `tests/test_nf_20261109_14_overnight_futures_leadlag.py` (**15 passed**)
  - Data (free/public yfinance, PIT): ES=F/NQ=F (signal), SPY/QQQ (traded), daily auto-adjust Open/Close, 4231 rows 2010-01-04→2026-10-30 (train 2515 / val 756 / test 962; OOS Val+Test n=1712).
  - Signal: z-scored overnight futures return (open[t]/close[t-1]-1) over `lookback`; long cash if z > `z_entry`, short if z < `-z_entry`, flat otherwise; vol-targeted intraday position at cash open held to cash close; 1-bar delay via engine `signals.shift(1)`; long/short, Equity CostModel defaults; MAX_POS 0.5.
  - Selected (train-only 4-fold WF mean Sharpe 0.511): `pair=ES_SPY, lookback=21, z_entry=1.0, vol_target=0.20`.
  - OOS Val+Test (333 trades, n=1712): Sharpe **0.490** fail, PF **1.211** fail, max DD **-1.10%** pass, trades **333** pass, WF stability **0.960** pass (train 0.511→OOS 0.490), worst-regime rolling-252 **-1.532** fail, benchmark p **0.859** / IR **-0.398** fail, perturbation **0.903** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.449/1.086/-7.20%/1712; random-futures-sign **−0.343**/0.874/-3.52%/333 (weaker, no edge); **inverse signal** (short on positive overnight futures return) **−0.490**/0.825/-2.17%/333 — inverse weaker, direction consistent but no edge.
  - Honest adjacency: H18 overnight/intraday (REJECT 4/9, same-asset overnight sign), H85 cross-asset lead-lag (REJECT 2/8, sector ETF→constituent). Novelty scored repo-relative on the *derivative futures overnight return → underlying cash daytime return* mechanism.
- **Cycle 83 discovery (directive §4):** Reconciled lineage to H168. Proposed/scored repo-new/decisive candidates across ≥3 broad mechanism categories with honest scoring and concrete deferred reassessment (no silent drops): **NF-20261109-14 Overnight futures lead-lag (4.45, selected/executed as H169)**; NF-20261109-15 Tax-loss harvesting (4.35, deferred); NF-20261109-16 Dividend capture (4.20, deferred).
- **Draft collisions reconciled:** NF-20261109-14 verified unused before execution.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python -m ruff check run_nf_20261109_14_overnight_futures_leadlag.py tests/test_nf_20261109_14_overnight_futures_leadlag.py` — **All checks passed**.
- `python -m ruff format --check` (same files) — **clean** (after `ruff format`).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_14_overnight_futures_leadlag.py` — **15 passed**.
- `python3 run_nf_20261109_14_overnight_futures_leadlag.py` — completed; artifact written. Verdict **REJECT 4/8** (REAL, not fabricated). `{"verdict":"REJECT","gates":"4/8","oos":{"n":1712,"sharpe":0.490...,"pf":1.211...,"maxdd":-0.0110...,"trades":333},"best":{"pair":"ES_SPY","lookback":21,"z_entry":1.0,"vol_target":0.2}}`.
- **Not rerun:** full pinned `src/qtr` suite (no `src/qtr` change); global ruff/format over `src tests run_*.py`.

## Approaches / evidence (do not blindly repeat)
- H169 **direction consistent** (inverse weaker at −0.490 vs base 0.490) but **no edge** (both fail gates). Do not repeat the pre-registered "long on positive overnight futures return" mapping without a materially different, pre-registered mechanism/mapping and evidence.
- Overnight futures lead-lag rejected as specified; mechanism not validated on free data.
- Correlation-class rejects (asset/pair differences disclosed): H127 GLD-TLT (4/8), H96/H134/H137 correlation. RV-stress rejects: H151 TLT (5/8), H156 UUP (5/8), H164 GLD (3/8, direction falsified). Dispersion rejects: H118/H160/H162. Vol-complex: H158/H159. Credit spreads: H94/H108/H146/H163. Calendar/seasonal: H91/H140/H142/H90/H168. FX carry: H161. VRP: H17/H100/H167. Cross-asset lead-lag: H85. Index rebalance flows: H168. Overnight futures lead-lag: H169.

## Precise next task (Cycle 84, directive §4)
See `NEXT_TASK.md`: reconcile lineage to H169 (H85–H169 rejected/recorded), next unused H-ID **H170**. Propose >=3 repo-new candidates across >=3 broad mechanism categories with honest scoring; carried-forward pool includes NF-20261109-15 tax-loss harvesting (4.35), NF-20261109-16 dividend capture (4.20), NF-20261109-12 holiday drift (4.15), NF-20261109-13 low-vol factor timing (3.45) — reassess with concrete evidence before recycling; search materially different categories first. Pre-register **H170**, implement runner + focused tests, ruff + focused pytest, execute REAL, record verdict. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).