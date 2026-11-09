# HANDOFF_NEXT (Cycle 82)

## Completed this session (Cycle 79)
- **H165 / NF-20261109-08 — realized SPY--VIX correlation regime SPY timing (cross-asset volatility-equity stress transmission): REJECT (4/8, REAL).**
  - Artifact: `.experiments/nf_runs/nf_20261109_08_spy_vix_corr_regime/summary.json` (+ `grid.csv`, `data_meta.json`, 26.35s)
  - Runner: `run_nf_20261109_08_spy_vix_corr_regime.py`; Tests: `tests/test_nf_20261109_08_spy_vix_corr_regime.py` (**7 passed**)
  - Data (free/public yfinance, PIT): SPY (traded) + ^VIX (signal), daily auto-adjust Close, 4233 rows 2010-01-04→2026-10-30 (train 2515 / val 756 / test 962; OOS Val+Test n=1716).
  - Signal: rolling realized correlation of SPY and ^VIX returns over `corr_window`, z-scored over `z_window` (past-only); continuous de-risk on abnormally negative correlation (stress) = `((-z).clip(0)/entry_scale).clip(0,1)`; full exposure when benign; 1-bar delay via engine `signals.shift(1)`, long-only, Equity CostModel defaults; MAX_POS 0.5.
  - Selected (train-only 4-fold WF mean Sharpe 0.754): `corr_window=63, z_window=252, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3968 trades, n=1716): Sharpe **0.652** fail, PF **1.124** fail, max DD **-3.00%** pass, trades **3968** pass, WF stability **0.865** pass (train 0.754→OOS 0.652), worst-regime rolling-252 **-0.994** fail, benchmark p **0.974** / IR **-0.787** fail, perturbation **0.930** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.792/1.164/-33.72%/1; random-exposure-matched **0.615**/1.143/-7.70%/1715 (weaker, no edge); **inverse regime** (pre-registered falsifier: de-risk when SPY--VIX correlation abnormally POSITIVE / benign) **0.950**/1.200/-3.08%/3743 — **inverse materially outperforms base and falsifies the pre-registered de-risk-on-negative-correlation direction**. H165 is not a validated edge as specified.
  - Honest adjacency: H127 GLD--TLT correlation (REJECT 4/8, different pair), H96/H134/H137 correlation class (REJECT), H158/H159 VIX-complex (different observable). Novelty scored repo-relative on the SPY--VIX correlation-regime observable.
- **Cycle 79 discovery (directive §4):** Reconciled lineage to H164. Proposed/scored repo-new/decisive candidates across broad mechanism categories with honest scoring and concrete deferred reassessment (no silent drops): **NF-20261109-08 SPY--VIX correlation (3.55, selected/executed as H165)**; NF-09-03 breakeven-inflation downgraded 3.50 **deferred/data-limited** (direct ^T5YIE/^T10YIE unavailable; TIP/IEF proxy conflated); NF-06-33 EWH/SPY (3.35, deferred/confounded); NF-08-16 Halloween seasonal (3.90 held, calendar adjacency H91/H140/H142 — prior cycles declined selection 6x).
- **Draft collisions reconciled:** removed `run_nf_20261109_06_idio_skew_regime.py` + test (3F/7P, no artifact, claimed NF-09-06/H164) and `run_nf_20261109_07_dealer_crowding_spy.py` (32-byte stub, no root/mechanism/tests/artifact). NF-20261109-08 verified unused before execution.
- **Cycle 82 / H168 — S&P 500 index rebalance flow timing SPY — REAL EXECUTION: REJECT 4/8.** Runner `run_nf_20261109_11_spy_index_rebalance.py` + tests `tests/test_nf_20261109_11_spy_index_rebalance.py` (9 passed). `ruff check/format` clean. Artifact `.experiments/nf_runs/nf_20261109_11_spy_index_rebalance/summary.json` (+`grid.csv`, `data_meta.json`, 6.44s). OOS Val+Test (n=1717): Sharpe **0.803** fail, trades **700** pass, PF **1.151** fail, max DD **-3.44%** pass, WF stability **0.752** pass, worst-regime **-1.210** fail, benchmark p **0.982** / IR **-0.759** fail, perturbation **0.982** pass. Random-window control **0.839** matches base 0.803 → structural-flow mechanism not validated. Documented `HYPOTHESIS_SPEC.md` §H168, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 82, `NEXT_TASK.md` (Cycle 83 / H169).

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python -m ruff check run_nf_20261109_08_spy_vix_corr_regime.py tests/test_nf_20261109_08_spy_vix_corr_regime.py` — **All checks passed**.
- `python -m ruff format --check` (same files) — **clean** (after `ruff format`).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_08_spy_vix_corr_regime.py` — **7 passed**.
- `python3 run_nf_20261109_08_spy_vix_corr_regime.py` — completed; artifact written. Verdict **REJECT 4/8** (REAL, not fabricated). `{"verdict":"REJECT","gates":"4/8","oos":{"n":1716,"sharpe":0.652...,"pf":1.124...,"maxdd":-0.0300...,"trades":3968},"best":{"corr_window":63,"z_window":252,"entry_scale":2,"vol_target":0.15}}`.
- **Not rerun:** full pinned `src/qtr` suite (no `src/qtr` change); global ruff/format over `src tests run_*.py`.

## Approaches / evidence (do not blindly repeat)
- H165 **direction falsified** by inverse ablation (inverse 0.950/1.200 >> base 0.652/1.124). Do not repeat the pre-registered "de-risk on strongly negative SPY--VIX correlation" mapping without a materially different, pre-registered mechanism/mapping and evidence.
- Correlation-class rejects (asset/pair differences disclosed): H127 GLD-TLT (4/8), H96/H134/H137 correlation. RV-stress rejects: H151 TLT (5/8), H156 UUP (5/8), H164 GLD (3/8, direction falsified). Dispersion rejects: H118/H160/H162. Vol-complex: H158/H159.
- NF-09-03 direct breakeven indices (^T5YIE/^T10YIE) unavailable on yfinance probe; TIP/IEF proxy conflated.
- Tracked drafts NF-09-06 idio_skew and NF-09-07 dealer_crowding removed (non-decision-ready collisions); do not reuse NF-09-06/-07.

## Precise next task (Cycle 80, directive §4)
See `NEXT_TASK.md`: reconcile lineage to H165 (H85–H165 rejected/recorded), next unused H-ID **H165→H166**. Propose >=3 repo-new candidates across >=3 broad mechanism categories with honest scoring; carried-forward pool is low-expected-information (breakeven data-limited, EWH confounded, Halloween held) — search materially different categories before selecting. Pre-register **H166**, implement runner + focused tests, ruff + focused pytest, execute REAL, record verdict. `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite).
