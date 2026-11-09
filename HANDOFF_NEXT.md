# HANDOFF_NEXT (Cycle 79)

## Completed this session (Cycle 78)
- **H164 / NF-20261108-26 — GLD realized-volatility stress regime SPY timing (commodity safe-haven / monetary-stress volatility transmission): REJECT (3/8, REAL).**
  - Artifact: `.experiments/nf_runs/nf_20261108_26_gld_rv_stress_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 18.63s)
  - Runner: `run_nf_20261108_26_gld_rv_stress_spy.py`; Tests: `tests/test_nf_20261108_26_gld_rv_stress_spy.py` (**7 passed**)
  - Data (free/public yfinance, PIT): SPY (traded) + GLD (signal), daily auto-adjust Close, 4233 rows 2010-01-04→2026-10-30 (train 2515 / val 756 / test 962; OOS Val+Test n=1716).
  - Signal: trailing GLD realized volatility (annualized rolling std of returns) z-scored; continuous de-risk vol-targeted long SPY when GLD RV z abnormally positive (stress = `(z.clip(0)/entry_scale).clip(0,1)`), full exposure when benign; 1-bar delay via engine `signals.shift(1)`, long-only, Equity CostModel defaults.
  - Selected (train-only 4-fold WF mean Sharpe 0.913): `rv_window=63, z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3784 trades, n=1716): Sharpe **0.569** fail, PF **1.114** fail, max DD **-3.04%** pass, trades **3784** pass, WF stability **0.624** fail (train 0.913→OOS 0.569), worst-regime rolling-252 **-1.123** fail, benchmark p **0.977** / IR **-0.788** fail, perturbation **0.948** pass → **3/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.792/1.164/-33.72%/1; random-exposure-matched **0.472**/1.112/-7.73%/1715 (weaker, no edge); **inverse regime** (pre-registered falsifier: de-risk when GLD RV LOW / negative z) **1.108**/1.230/-2.10%/3927 — **inverse materially outperforms base and falsifies the pre-registered de-risk-on-high-GLD-RV direction**. H164 is not a validated edge as specified.
  - Honest adjacency: repo-new executed *GLD own realized-vol stress* SPY-timing observable. Distinct from H151 TLT RV stress (REJECT 5/8, Treasury) and H156 UUP RV stress (REJECT 5/8, USD) — same construction class but different asset/mechanism; distinct from H149 GDX-GLD RV divergence (REJECT 4/8, relative/divergence observable) and H88 (GLD/commodity convergence context). Construction-class adjacency (RV z-score de-risking, vol-target, 1-bar delay) disclosed.
  - **Artifact-path integrity:** `.experiments/nf_runs/nf_20261108_18_gld_rv_stress_spy/` is occupied by **H151 (NF-20261108-18, TLT RV stress, REJECT 5/8)** and was **not overwritten**. H164 artifacts are in `nf_20261108_26_gld_rv_stress_spy/`.
- **Cycle 78 discovery (directive §4):** Reconciled lineage to H163. Proposed/scored repo-new/decisive candidates across broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops): **NF-20261108-26 GLD RV stress (3.75, selected/executed as H164)**; NF-20261109-03 breakeven-inflation downgraded 3.50 **deferred/data-limited** (direct ^T5YIE/^T10YIE unavailable on yfinance probe 2026-11-09 in this environment; TIP/IEF proxy conflated); NF-20261106-33 EWH/SPY (3.35, deferred/confounded); NF-20261108-16 Halloween seasonal (3.35, deferred/calendar adjacency H91/H140/H142).
- **NF root/integrity reconciliation (partial, evidence recorded):** NF-20261108-26 verified unused before execution. NF-08-26/H164 runner/test updated to Cycle 78 protocol; NF-09-06 GLD-RV untracked duplicate draft files removed. **Tracked collision remains (do not treat as results):** `run_nf_20261109_06_idio_skew_regime.py`/`tests/test_nf_20261109_06_idio_skew_regime.py` (commit 60e71c6) claim NF-20261109-06/H164 but focused tests were **3 failed, 7 passed** and **no REAL execution/artifact** in Cycle 78. `run_nf_20261109_07_dealer_crowding_spy.py` (commit 4b0c93b) is a stub with no NF root/mechanism/tests/artifact. Cycle 79 must verify/rename/remove/reconcile these before any execution.
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H164, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 78, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m py_compile run_nf_20261108_26_gld_rv_stress_spy.py tests/test_nf_20261108_26_gld_rv_stress_spy.py` — clean.
- `python -m ruff check run_nf_20261108_26_gld_rv_stress_spy.py tests/test_nf_20261108_26_gld_rv_stress_spy.py` — **All checks passed**.
- `python -m ruff format --check` (same files) — **clean**.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_26_gld_rv_stress_spy.py` — **7 passed**.
- `python3 run_nf_20261108_26_gld_rv_stress_spy.py` — completed; artifact written. Verdict **REJECT 3/8** (REAL, not fabricated). `{"verdict":"REJECT","gates":"3/8","oos":{"n":1716,"sharpe":0.569...,"pf":1.114...,"maxdd":-0.0304...,"trades":3784},"best":{"rv_window":63,"z_window":126,"entry_scale":2,"vol_target":0.15}}`.
- `python3 -m py_compile run_nf_20261109_06_idio_skew_regime.py tests/test_nf_20261109_06_idio_skew_regime.py` — clean (imports at runtime).
- `python -m ruff check` on idio_skew files — **All checks passed** (but idio_skew tests failed; not executed).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_06_idio_skew_regime.py` — **3 failed, 7 passed** (evidence: past-only skew assertion, hysteresis mapping, broadcast shape). **Not an executed result; tracked draft collision.**
- **Not rerun:** full pinned `src/qtr` suite (no `src/qtr` change); global ruff/format over `src tests run_*.py`.

## Approaches / evidence (do not blindly repeat)
- H164 **direction falsified** by inverse ablation (inverse 1.108/1.230 >> base 0.569/1.114). Do not repeat the pre-registered “de-risk on high GLD RV” mapping without a materially different, pre-registered mechanism/mapping and evidence.
- RV-stress construction rejects (asset/observable differences disclosed): H151 TLT RV (5/8), H156 UUP RV (5/8), **H164 GLD RV (3/8, direction falsified)**. RV-divergence: H149 (4/8). Further RV-stress tests require clear separation and justified mapping.
- Dispersion rejects: H118/H160/H162. FX: H95/H103/H106/H161. Credit: H94/H108/H146/H163. Implied-vol/VRP: H158/H159/H160 etc.
- NF-09-03 direct breakeven indices (^T5YIE/^T10YIE) unavailable on yfinance probe 2026-11-09; TIP/IEF proxy conflated.
- **Tracked draft hazard:** nf_09_06 idio_skew claims NF-20261109-06/H164 with failing tests/no artifact; nf_09_07 dealer_crowding is a stub. Reconcile IDs/roots before execution.

## Precise next task (Cycle 79, directive §4)
1. Reconcile lineage to H164 (H85–H164 rejected/recorded). Next unused H-ID: **H165** (H24/H68–H73/H76–H79 unassigned, not recycled).
2. **Reconcile tracked draft collisions first:** fix/rename/remove with evidence `run_nf_20261109_06_idio_skew_regime.py`+test (claims H164, 3F/7P, no artifact) and `run_nf_20261109_07_dealer_crowding_spy.py` (stub). Assign new NF/H IDs only if made decision-ready and NF roots verified unused.
3. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred pool with concrete evidence (no silent drops). Reassess: NF-20261109-03 (breakeven, data-limited), NF-20261106-33 (EWH/SPY, 3.35), NF-20261108-16 (Halloween, 3.35), NF-20261108-20 (IEF RV stress, adj H151), NF-20261108-21/22/23 (UNG-USO/EFA-EEM/USO lead-lag). Justify independence from rejected classes (RV-stress H151/H156/H164 direction-falsified; credit H94/H108/H146/H163; dispersion H118/H160/H162; FX H95/H103/H106/H161).
4. Verify NF roots against executed H-IDs/artifacts/runners before selection. NF-20261108-26/H164 executed; nf_20261108_18_gld_rv_stress_spy dir = H151 TLT (do not overwrite).
5. Pre-register highest-expected-information feasible candidate as **H165** in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 79 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
6. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. **Pandas 3.x safety:** do not use `if <DataFrame>:` truthiness.
7. Run `ruff check/format`, focused `pytest`, execute REAL; record verdict + artifact path. **Do not fabricate results.** No gate weakening; no published/certified artifact modification.
8. If `src/qtr` is touched, rerun: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
