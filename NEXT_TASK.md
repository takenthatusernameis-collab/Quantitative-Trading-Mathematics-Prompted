# NEXT_TASK — Cycle 63: discovery, pre-register, implement, execute next H-ID after H148

## State (post Cycle 62 / H148)
- **H148 / NF-20261107-52 — SPY timing from EEM-vs-SPY realized-volatility divergence (cross-asset volatility transmission / global risk; RV-difference z-score): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261107_52_eem_spy_rvdiv/summary.json` (+ `grid.csv`, `data_meta.json`, 5.61s, **corrected REAL**)
  - Runner: `run_nf_20261107_52_eem_spy_rvdiv.py`; Tests: `tests/test_nf_20261107_52_eem_spy_rvdiv.py` (6 passed)
  - **Integrity note:** an incomplete non-standard runner/artifact was committed earlier in Cycle 62 (commit `d5b8d74` context) without the standard gated/ablation protocol; repaired to the pre-registered standard protocol and re-executed. Committed artifact is the corrected REAL run.
  - Data (free/public yfinance, PIT): SPY + EEM daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: z-score of trailing `(rv_EEM − rv_SPY)` (log-return rolling std) over `z_window`; continuous de-risking of vol-targeted long SPY when z abnormally positive (EM stress), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.995): `rv_window=63, z_window=126, entry_scale=1.0, vol_target=0.15`.
  - OOS Val+Test (2757 engine trades, n=1259): Sharpe **0.946** fail, PF **1.215** fail, max DD **-2.57%** pass, trades **2757** pass, WF stability **0.951** pass, worst-regime rolling-252 **-0.820** fail, benchmark p **0.939** / IR **-0.714** fail, perturbation **0.943** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.688**/1.168/-3.18%/1258 (weaker, no benchmark edge); **inverse regime** (de-risk when EEM RV abnormally low vs SPY / negative z) **0.540**/1.120/-2.08%/2747 (weaker; **direction supported**, unlike H138/H139 inverse outperformance, but no benchmark edge).
  - Honest adjacency: repo-new executed EEM/SPY RV-*difference* observable/pair. Explicitly separated from H138 (HYG−LQD/SPY RV ratio, REJECT 2/8) and H139 (IWM/SPY RV ratio, REJECT 2/8) — different asset pair/channel and difference construction; both H138/H139 had inverse mappings outperforming (direction falsified), H148 inverse is weaker (direction supported) but still no edge. Adjacent to H144 (EEM-SPY relative-momentum, REJECT 3/8; different observable: RV divergence vs price momentum). No validated edge.
- `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. No commit/push.
- **H85–H148 all rejected/recorded.** Next unused H-ID after H148: **H149** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H148, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 62 discovery/outcome, `HANDOFF_NEXT.md` (Cycle 62).

## Cycle 62 discovery (directive §4, >=3 repo-new mechanism candidates across >=3 broad categories)
Lineage reconciled to H147 (H85–H147 rejected/recorded). Candidates scored honestly (25 novelty / 25 plausibility / 20 data+PIT / 15 falsifiability / 10 execution / 5 support). Independence justified from rejected construction classes: correlation H96/H127/H134/H137; RV-divergence H138/H139/H148 (H148 adds EEM/SPY RV-difference with repo-new pair; inverse tested); OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144 (H148 different observable); GLD-SPY relmom H145; cross-sectional IVOL dispersion H146; RSP/SPY MA-participation breadth H115/H147; FX-strength z-score adjacency H95/H103/H106.

| Candidate (NF-ID) | Broad category | N | E | D | F | X | S | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NF-20261107-52 EEM-vs-SPY realized-vol divergence SPY timing (RV-difference z-score) — **H148 (selected/executed)** | Cross-asset volatility transmission / global risk transmission | 3 | 3 | 5 | 4 | 4 | 2 | **3.50** |
| NF-20261106-20 XLY/XLP consumer-discretionary-vs-staples ratio momentum — **NOT selected (NF root executed as H110, REJECT 4/8)** | Cross-sector macro regime / consumer-demand transmission | (3) | (3) | (5) | (4) | (4) | (3) | (3.55) |
| NF-20261106-01 GDX-vs-GLD miner gold-beta RV divergence SPY timing | Commodity volatility transmission / sector risk transmission | 3 | 3 | 5 | 4 | 4 | 2 | **3.50** |

Scoring notes (honest): NF-20261107-52 novelty 3 — repo-new EEM/SPY RV-difference pair/observable with material adjacency to RV-divergence class H138/H139 (inverse outperformed there) and to H144 relmom; explicit inverse-falsifier design. NF-20261106-20 scored 3.55 but its NF root corresponds to executed H110 (`nf_20261106_20_xly_xlp_consumer`, REJECT 4/8) — **not repo-new; excluded from selection** (honest correction recorded). NF-20261106-01 deferred (adjacency to gold/miner H88/H99/H101/H145 and RV-div class).

## Deferred / held candidates (reassess with concrete evidence, no silent drops)
- **Held (materially different design required vs rejected construction classes):** NF-20261107-49 TLT-SPY realized corr (correlation class H96/H127/H134/H137); NF-20261108-04 triple witching OPX+futures (subclass of H140); NF-20261107-14/48 OVX−VIX (IV-spread class H125/H126). NF-20261107-52 **executed as H148 (REJECT)**.
- **Deferred (Cycle 62 scored):** NF-20261106-01 GDX-vs-GLD miner RV divergence (3.50; needs concrete separation from H88/H99/H101/H145 and RV-div class).
- **Deferred from Cycle 60:** RV trend/momentum equity timing (3.40, adjacency H122/H29/H30 — requires clearly separated pre-registered design); cross-sectional idiosyncratic-skew spread timing (3.00).
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy). NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8). NF-07/08/10/11/13/15/17/20/21 **deferred** (**NF-20 root executed H110**). NF-11r/NF-06-18 same root as NF-11 (ETF TLT-SHY proxy executed H141). NF-06-11 CBOE PC ratio **infeasible**. NF-20261106-03/23/24/28/30/32/33/35 **deferred**. NF-20261107-05 CPI drift **deferred** (data blocker). NF-20261108-05 overnight/intraday return-flow **deferred**. NF-20261108-07 TIP-IEF breakeven-proxy **deferred**. NF-20261108-08 DBC-SPY commodity-complex **deferred**. NF-20261108-10 FXE EUR momentum **deferred** (FX-family adjacency H95/H103/H106).
- **Rejected construction classes (do not blindly repeat):** correlation H96/H127/H134/H137; RV-divergence H138/H139/H148; OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144; GLD-SPY relmom H145; cross-sectional IVOL dispersion H146; breadth H115/H147; FX-strength H95/H103/H106. **NF-20/H110 executed — not repo-new.**

## Precise next task (one task) — Cycle 63 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4:
1. Reconcile lineage to H148 (H85–H148 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held pool above with concrete evidence (no silent drops). **Verify NF roots against executed H-IDs/artifacts** (do not re-propose executed roots like NF-20/H110). Justify independence from rejected construction classes above.
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID (**H149**) in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 63 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading. **Pandas 3.x safety:** do not use `if <DataFrame>:` / `if trade_dates:` truthiness on DataFrames.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
