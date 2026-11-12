# Experiment Lineage Report

**Generated:** 2026-11-12 20:57:29 UTC
**Source:** `.experiments/experiments.jsonl`
**Total Experiments:** 173

## Summary by Category

| Category | Count | Passed | Failed | Errors |
|---|---:|---:|---:|---:|
| Baseline / MA Crossover | 9 | 6 | 0 | 3 |
| Time-Series Momentum | 60 | 41 | 0 | 16 |
| Cross-Sectional Momentum | 2 | 2 | 0 | 0 |
| Regime-Gated | 5 | 5 | 0 | 0 |
| Volatility / VRP | 9 | 5 | 2 | 2 |
| Volume Predictive | 6 | 3 | 0 | 3 |
| Hypothesis H10-H29 | 23 | 16 | 0 | 7 |
| New Family (NF) - Recent | 51 | 27 | 14 | 10 |
| New Family (NF) - Factor/Other | 5 | 4 | 0 | 1 |
| Other / Uncategorized | 3 | 2 | 0 | 1 |

## Detailed Experiment Records

### Baseline / MA Crossover

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 17-00-29-177005 | ma_crossover_baseline_v1 | 2026-10-10 17:00:29 UTC | 41a04698 | failed | — | data_source=unknown | — | Unable to find a usable engine; tried using: 'pyar... |
| 17-00-51-665376 | ma_crossover_baseline_v1 | 2026-10-10 17:00:51 UTC | 41a04698 | failed | — | data_source=unknown | 4 artifacts | 'numpy.ndarray' object has no attribute 'expanding... |
| 17-02-03-093094 | ma_crossover_baseline_v1 | 2026-10-10 17:02:03 UTC | 41a04698 | failed | — | data_source=unknown | 4 artifacts | name 'sharpe_ratio' is not defined |
| 17-02-22-080026 | ma_crossover_baseline_v1 | 2026-10-10 17:02:22 UTC | 41a04698 | completed | sharpe_step1=-1.2471<br>sharpe_step0=-1.2468<br>profit_factor_step1=0.7806<br>max_drawdown_step1=-0.9999<br>walkforward_stability_step1=1.8392<br>total_return_step1=-0.9999<br>annualized_return_step1=-0.5904 | data_source=unknown | 8 artifacts | — |
| 17-03-39-610858 | ma_crossover_baseline_v1 | 2026-10-10 17:03:39 UTC | 41a04698 | completed | sharpe_step1=-1.0405<br>sharpe_step0=-1.0403<br>profit_factor_step1=0.8138<br>max_drawdown_step1=-0.9995<br>walkforward_stability_step1=1.4344<br>total_return_step1=-0.9995<br>annualized_return_step1=-0.5311 | data_source=unknown | 8 artifacts | — |
| 17-04-21-400695 | ma_crossover_baseline_v1 | 2026-10-10 17:04:21 UTC | 41a04698 | completed | sharpe_step1=-2.5928<br>sharpe_step0=-2.5922<br>profit_factor_step1=0.5643<br>max_drawdown_step1=-0.9950<br>walkforward_stability_step1=1.1620<br>total_return_step1=-0.9950<br>annualized_return_step1=-0.4119 | data_source=unknown | 8 artifacts | — |
| 17-05-58-697503 | buy_and_hold_baseline_v1 | 2026-10-10 17:05:58 UTC | 41a04698 | completed | sharpe_step1=0.6597<br>sharpe_step0=0.6596<br>profit_factor_step1=1.1347<br>max_drawdown_step1=-0.3410<br>walkforward_stability_step1=1.0277<br>total_return_step1=1.7457<br>annualized_return_step1=0.1065 | data_source=unknown | 6 artifacts | — |
| 17-07-48-008615 | ma_crossover_param_sweep_v1 | 2026-10-10 17:07:48 UTC | 41a04698 | completed | — | data_source=unknown | 7 artifacts | — |
| 08-26-02-537359 | buy_and_hold_baseline_v1 | 2026-10-14 08:26:02 UTC | 37224854 | completed | sharpe_step1=0.6847<br>sharpe_step0=0.6846<br>profit_factor_step1=1.1401<br>max_drawdown_step1=-0.3410<br>walkforward_stability_step1=0.9335<br>total_return_step1=1.8628<br>annualized_return_step1=0.1111 | data_source=unknown | 6 artifacts | — |

### Time-Series Momentum

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 20-56-30-507309 | ts_momentum_20etf_v1 | 2026-10-10 20:56:30 UTC | 2bb82523 | completed | — | data_source=unknown | 11 artifacts | — |
| 20-57-26-136503 | ts_momentum_20etf_v1 | 2026-10-10 20:57:26 UTC | 2bb82523 | completed | — | data_source=unknown | 11 artifacts | — |
| 21-08-54-188263 | ts_momentum_20etf_v1 | 2026-10-10 21:08:54 UTC | 2bb82523 | completed | — | data_source=unknown | 11 artifacts | — |
| 21-58-07-833835 | futures_tsmom_v1 | 2026-10-10 21:58:07 UTC | e6a36808 | failed | — | data_source=unknown | 4 artifacts | compare_to_benchmark() got an unexpected keyword a... |
| 21-58-28-353634 | futures_tsmom_v1 | 2026-10-10 21:58:28 UTC | e6a36808 | completed | — | data_source=unknown | 8 artifacts | — |
| 21-59-16-546117 | futures_tsmom_v1 | 2026-10-10 21:59:16 UTC | e6a36808 | completed | — | data_source=unknown | 8 artifacts | — |
| 22-59-01-182037 | futures_tsmom_v1 | 2026-10-10 22:59:01 UTC | cd8cd603 | completed | — | data_source=unknown | 8 artifacts | — |
| 00-25-56-751422 | ddcv_futures_tsmom_v1 | 2026-10-11 00:25:56 UTC | ffb2647b | failed | — | data_source=unknown | 4 artifacts | name 'sharpe' is not defined |
| 00-26-08-362690 | ddcv_futures_tsmom_v1 | 2026-10-11 00:26:08 UTC | ffb2647b | failed | — | data_source=unknown | 4 artifacts | name 'max_drawdown' is not defined |
| 00-26-18-281925 | ddcv_futures_tsmom_v1 | 2026-10-11 00:26:18 UTC | ffb2647b | failed | — | data_source=unknown | 4 artifacts | "'dd_trigger'" |
| 00-26-35-750834 | ddcv_futures_tsmom_v1 | 2026-10-11 00:26:35 UTC | ffb2647b | completed | — | data_source=unknown | 9 artifacts | — |
| 00-34-05-381535 | ddcv_futures_tsmom_v1 | 2026-10-11 00:34:05 UTC | a6b40706 | completed | — | data_source=unknown | 9 artifacts | — |
| 02-44-40-301520 | h6_vix_ddcv_futures_tsmom_v1 | 2026-10-11 02:44:40 UTC | f7ab792b | completed | — | data_source=unknown | 12 artifacts | — |
| 02-46-37-311994 | h6_vix_ddcv_futures_tsmom_v1 | 2026-10-11 02:46:37 UTC | eee6cd45 | completed | — | data_source=unknown | 12 artifacts | — |
| 07-18-25-546691 | h6_vix_ddcv_futures_tsmom_v1 | 2026-10-11 07:18:25 UTC | 8193bdcf | failed | — | data_source=unknown | — | Unable to find a usable engine; tried using: 'pyar... |
| 07-18-39-160945 | h6_vix_ddcv_futures_tsmom_v1 | 2026-10-11 07:18:39 UTC | 8193bdcf | completed | — | data_source=unknown | 12 artifacts | — |
| 08-02-22-999214 | h6_vix_ddcv_futures_tsmom_v1 | 2026-10-11 08:02:22 UTC | 0df82803 | completed | — | data_source=unknown | 12 artifacts | — |
| 15-21-31-333870 | h8_roll_adjusted_futures_ts... | 2026-10-11 15:21:31 UTC | 8ad8f231 | completed | — | data_source=unknown | 25 artifacts | — |
| 15-53-04-679746 | h9_intraday_tsmom_ctexits_v1 | 2026-10-11 15:53:04 UTC | 0174ca64 | failed | — | data_source=unknown | — | fill_method must be None; got fill_method=1. |
| 15-53-31-819888 | h9_intraday_tsmom_ctexits_v1 | 2026-10-11 15:53:31 UTC | 0174ca64 | failed | — | data_source=unknown | 7 artifacts | The truth value of a Series is ambiguous. Use a.em... |
| 15-54-17-212022 | h9_intraday_tsmom_ctexits_v1 | 2026-10-11 15:54:17 UTC | 0174ca64 | completed | — | data_source=unknown | 8 artifacts | — |
| 16-44-06-168529 | h9_intraday_tsmom_ctexits_v2 | 2026-10-11 16:44:06 UTC | ab2141a6 | completed | — | data_source=unknown | 10 artifacts | — |
| 16-46-06-466282 | h9_intraday_tsmom_ctexits_v2 | 2026-10-11 16:46:06 UTC | ab2141a6 | completed | — | data_source=unknown | 13 artifacts | — |
| 16-52-38-694559 | h9_intraday_tsmom_ctexits_v2 | 2026-10-11 16:52:38 UTC | 0fdf2488 | completed | — | data_source=unknown | 13 artifacts | — |
| 17-23-43-809533 | h10_intraday_tsmom_pfopt | 2026-10-11 17:23:43 UTC | 3d4e7096 | failed | — | data_source=unknown | — | NDFrame.fillna() got an unexpected keyword argumen... |
| 17-24-14-385352 | h10_intraday_tsmom_pfopt | 2026-10-11 17:24:14 UTC | 3d4e7096 | completed | — | data_source=unknown | 21 artifacts | — |
| 17-41-18-169363 | h10_intraday_tsmom_pfopt | 2026-10-11 17:41:18 UTC | d9b6b082 | completed | — | data_source=unknown | 21 artifacts | — |
| 22-13-37-475937 | H18_Overnight_Intraday_Deco... | 2026-10-13 22:13:37 UTC | 11f5d01d | failed | — | data_source=unknown | 15 artifacts | — |
| 22-14-26-107907 | H18_Overnight_Intraday_Deco... | 2026-10-13 22:14:26 UTC | 11f5d01d | failed | — | data_source=unknown | 16 artifacts | — |
| 22-14-50-729923 | H18_Overnight_Intraday_Deco... | 2026-10-13 22:14:50 UTC | 11f5d01d | failed | — | data_source=unknown | 16 artifacts | — |
| 23-22-46-285872 | h21_futures_tsmom_multicont... | 2026-10-13 23:22:46 UTC | 61290014 | failed | — | data_source=unknown | — | unhashable type: 'list' |
| 23-23-08-695117 | h21_futures_tsmom_multicont... | 2026-10-13 23:23:08 UTC | 61290014 | failed | — | data_source=unknown | — | The truth value of a Series is ambiguous. Use a.em... |
| 23-24-11-769546 | h21_futures_tsmom_multicont... | 2026-10-13 23:24:11 UTC | 61290014 | failed | — | data_source=unknown | — | 'BASKET' |
| 23-27-07-191470 | h21_futures_tsmom_multicont... | 2026-10-13 23:27:07 UTC | 61290014 | failed | — | data_source=unknown | 1 artifacts | cannot access local variable 'daily_agg' where it ... |
| 23-27-52-101656 | h21_futures_tsmom_multicont... | 2026-10-13 23:27:52 UTC | 61290014 | completed | — | data_source=unknown | 21 artifacts | — |
| 07-11-16-067434 | h22_futures_tsmom_voltarget | 2026-10-14 07:11:16 UTC | fa4c1d0f | failed | — | data_source=unknown | 1 artifacts | name 'atr' is not defined |
| 07-11-53-652432 | h22_futures_tsmom_voltarget | 2026-10-14 07:11:53 UTC | fa4c1d0f | failed | — | data_source=unknown | 1 artifacts | name 'sharpe_ratio' is not defined |
| 07-12-35-292010 | h22_futures_tsmom_voltarget | 2026-10-14 07:12:35 UTC | fa4c1d0f | completed | — | data_source=unknown | 22 artifacts | — |
| 07-12-59-473353 | h22_futures_tsmom_voltarget | 2026-10-14 07:12:59 UTC | fa4c1d0f | completed | — | data_source=unknown | 22 artifacts | — |
| 07-15-23-322705 | h22_futures_tsmom_voltarget | 2026-10-14 07:15:23 UTC | fa4c1d0f | completed | — | data_source=unknown | 22 artifacts | — |
| 07-32-43-425839 | h22_futures_tsmom_voltarget | 2026-10-14 07:32:43 UTC | fa4c1d0f | completed | — | data_source=unknown | 22 artifacts | — |
| 08-20-39-255883 | h9_intraday_tsmom_ctexits_v2 | 2026-10-14 08:20:39 UTC | 37224854 | completed | — | data_source=unknown | 13 artifacts | — |
| 08-26-18-385545 | ts_momentum_20etf_v1 | 2026-10-14 08:26:18 UTC | 37224854 | completed | — | data_source=unknown | 11 artifacts | — |
| 08-27-02-650342 | futures_tsmom_v1 | 2026-10-14 08:27:02 UTC | 37224854 | completed | — | data_source=unknown | 8 artifacts | — |
| 08-34-46-739801 | h23_crypto_futures_tsmom | 2026-10-14 08:34:46 UTC | 37224854 | failed | — | data_source=unknown | 1 artifacts | (252, None, True) |
| 08-48-49-412372 | h23_crypto_futures_tsmom | 2026-10-14 08:48:49 UTC | 37224854 | completed | — | data_source=unknown | 19 artifacts | — |
| 09-28-59-592390 | h23_crypto_futures_tsmom | 2026-10-14 09:28:59 UTC | 48b045ed | completed | — | data_source=unknown | 20 artifacts | — |
| 09-32-25-959733 | h23_crypto_futures_tsmom | 2026-10-14 09:32:25 UTC | 48b045ed | completed | — | data_source=unknown | 20 artifacts | — |
| 09-39-07-412533 | h23_crypto_futures_tsmom | 2026-10-14 09:39:07 UTC | 48b045ed | completed | — | data_source=unknown | 20 artifacts | — |
| 10-04-52-936640 | h23_crypto_futures_tsmom | 2026-10-14 10:04:52 UTC | 26d08fcf | completed | — | data_source=unknown | 20 artifacts | — |
| 11-53-37-996139 | h23_crypto_futures_tsmom | 2026-10-14 11:53:37 UTC | c9845a5f | completed | — | data_source=unknown | 20 artifacts | — |
| 18-10-38-263726 | h23_crypto_futures_tsmom | 2026-10-14 18:10:38 UTC | f3bb0f30 | failed | — | data_source=unknown | 1 artifacts | name 'h23' is not defined |
| 18-13-09-457781 | h23_crypto_futures_tsmom | 2026-10-14 18:13:09 UTC | f3bb0f30 | completed | — | data_source=unknown | 21 artifacts | — |
| 18-52-08-943792 | h22_futures_tsmom_voltarget | 2026-10-14 18:52:08 UTC | fd0635e3 | completed | — | data_source=unknown | 22 artifacts | — |
| 19-46-14-356479 | h25_futures_tsmom_pfmargin | 2026-10-14 19:46:14 UTC | 499913ba | completed | — | data_source=unknown | 22 artifacts | — |
| 20-00-08-312708 | h25_futures_tsmom_pfmargin | 2026-10-14 20:00:08 UTC | 499913ba | completed | — | data_source=unknown | 22 artifacts | — |
| 20-02-45-189859 | h25_futures_tsmom_pfmargin | 2026-10-14 20:02:45 UTC | 499913ba | completed | — | data_source=unknown | 22 artifacts | — |
| 20-08-34-613690 | h25_futures_tsmom_pfmargin | 2026-10-14 20:08:34 UTC | cecc9d54 | completed | — | data_source=unknown | 22 artifacts | — |
| 18-56-08-872500 | h7_intraday_tsmom_v1 | 2026-10-19 18:56:08 UTC | 7cb48c10 | completed | — | data_source=unknown | 4 artifacts | — |
| 18-56-58-553612 | h7_intraday_tsmom_v1 | 2026-10-19 18:56:58 UTC | 7cb48c10 | completed | — | data_source=unknown | 4 artifacts | — |

### Cross-Sectional Momentum

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 20-59-28-306148 | cs_momentum_10etf_v1 | 2026-10-10 20:59:28 UTC | 2bb82523 | completed | — | data_source=unknown | 10 artifacts | — |
| 21-09-06-830199 | cs_momentum_10etf_v1 | 2026-10-10 21:09:06 UTC | 2bb82523 | completed | — | data_source=unknown | 10 artifacts | — |

### Regime-Gated

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 21-27-13-928282 | regime_gated_momentum_20etf_v1 | 2026-10-10 21:27:13 UTC | 2ac48e7c | completed | — | data_source=unknown | 11 artifacts | — |
| 21-28-20-920399 | regime_gated_momentum_20etf_v1 | 2026-10-10 21:28:20 UTC | 2ac48e7c | completed | — | data_source=unknown | 11 artifacts | — |
| 18-20-38-363385 | nf_20261105_14_credit_regime | 2026-11-05 18:20:38 UTC | a683fad3 | completed | oos_sharpe=0.9254<br>oos_trades=318.0000 | data_source=unknown | 1 artifacts | — |
| 22-09-06-247157 | nf_20261105_15_corr_regime | 2026-11-05 22:09:06 UTC | 417cc7d4 | completed | oos_sharpe=0.7264<br>oos_trades=254.0000 | data_source=unknown | 1 artifacts | — |
| 17-24-06-550812 | nf_20261105_14_credit_regime | 2026-11-10 17:24:06 UTC | 022a9e16 | completed | oos_sharpe=0.9254<br>oos_trades=318.0000 | data_source=unknown | 1 artifacts | — |

### Volatility / VRP

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 21-46-52-446478 | h17_vrp | 2026-10-13 21:46:52 UTC | dcf5f8be | completed | — | data_source=unknown | 12 artifacts | — |
| 21-48-22-444352 | h17_vrp | 2026-10-13 21:48:22 UTC | dcf5f8be | completed | — | data_source=unknown | 12 artifacts | — |
| 21-51-45-034237 | h17_vrp | 2026-10-13 21:51:45 UTC | dcf5f8be | completed | — | data_source=unknown | 12 artifacts | — |
| 01-42-41-776602 | nf_20261104_01_vix_termstru... | 2026-11-05 01:42:41 UTC | 763f2566 | failed | — | data_source=unknown | — | min_periods must be an integer |
| 01-42-56-985927 | nf_20261104_01_vix_termstru... | 2026-11-05 01:42:56 UTC | 763f2566 | failed | — | data_source=unknown | — | window must be an integer 0 or greater |
| 01-43-20-575295 | nf_20261104_01_vix_termstru... | 2026-11-05 01:43:20 UTC | 763f2566 | completed | — | data_source=unknown | 7 artifacts | — |
| 13-35-05-405528 | nf_20261106_07_vvix_stress | 2026-11-06 13:35:05 UTC | e75eee81 | completed | oos_sharpe=0.7831<br>oos_trades=977<br>oos_pf=1.1578<br>gates_passed=4 | data_source=unknown | — | — |
| 21-57-20-802037 | nf_20261106_26_vix9d_vix_te... | 2026-11-06 21:57:20 UTC | 5daeccd1 | REJECT | — | data_source=unknown | — | — |
| 10-33-55-038242 | nf_20261107_08_vix9d_fear_s... | 2026-11-07 10:33:55 UTC | 00d209e6 | REJECT | oos_sharpe=1.0378<br>oos_trades=678<br>oos_pf=1.2060<br>oos_max_dd=-0.0249<br>wf_ratio=1.0919<br>worst_regime=-1.0457<br>benchmark_p=1.0000<br>benchmark_ir=-0.7519... | data_source=unknown | — | — |

### Volume Predictive

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 22-36-40-860592 | h19_volume_predictive | 2026-10-13 22:36:40 UTC | 532f0e56 | completed | — | data_source=unknown | 10 artifacts | — |
| 22-39-24-772135 | h19_volume_predictive | 2026-10-13 22:39:24 UTC | 532f0e56 | failed | — | data_source=unknown | 10 artifacts | name 'start_time' is not defined |
| 22-39-55-233900 | h19_volume_predictive | 2026-10-13 22:39:55 UTC | 532f0e56 | failed | — | data_source=unknown | 10 artifacts | name 'start_time' is not defined |
| 22-40-15-688927 | h19_volume_predictive | 2026-10-13 22:40:15 UTC | 532f0e56 | failed | — | data_source=unknown | 10 artifacts | name 'start_time' is not defined |
| 22-40-41-870350 | h19_volume_predictive | 2026-10-13 22:40:41 UTC | 532f0e56 | completed | — | data_source=unknown | 11 artifacts | — |
| 23-06-33-191710 | h20_signed_volume | 2026-10-13 23:06:33 UTC | 02e4025d | completed | — | data_source=unknown | 11 artifacts | — |

### Hypothesis H10-H29

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 18-36-51-113738 | h11_robustness_certification | 2026-10-11 18:36:51 UTC | d7942dbd | completed | — | data_source=unknown | 15 artifacts | — |
| 18-39-28-358766 | h11_robustness_certification | 2026-10-11 18:39:28 UTC | d7942dbd | failed | — | data_source=unknown | — | type object 'datetime.datetime' has no attribute '... |
| 18-40-37-427062 | h11_robustness_certification | 2026-10-11 18:40:37 UTC | d7942dbd | completed | — | data_source=unknown | 15 artifacts | — |
| 20-25-36-443045 | h11_robustness_certification | 2026-10-11 20:25:36 UTC | d7942dbd | completed | — | data_source=unknown | 13 artifacts | — |
| 12-51-06-515939 | h12_selection_bias_audit | 2026-10-13 12:51:06 UTC | 80154136 | completed | — | data_source=unknown | 4 artifacts | — |
| 14-26-42-499302 | h13_oos_deflation_pf_audit | 2026-10-13 14:26:42 UTC | 4a2c5939 | failed | — | data_source=unknown | — | name 'make_futures_config' is not defined |
| 14-35-58-316759 | h13_oos_deflation_pf_audit | 2026-10-13 14:35:58 UTC | 4a2c5939 | completed | — | data_source=unknown | 7 artifacts | — |
| 18-55-24-067184 | h14_pf_margin_selection_audit | 2026-10-13 18:55:24 UTC | c97d28cc | failed | — | data_source=unknown | — | make_futures_config() got an unexpected keyword ar... |
| 18-55-37-285183 | h14_pf_margin_selection_audit | 2026-10-13 18:55:37 UTC | c97d28cc | failed | — | data_source=unknown | — | cannot access local variable 'vol_scaled_tsmom_hou... |
| 18-55-53-930281 | h14_pf_margin_selection_audit | 2026-10-13 18:55:53 UTC | c97d28cc | failed | — | data_source=unknown | — | regime_labels() takes 1 positional argument but 2 ... |
| 19-00-08-666237 | h14_pf_margin_selection_audit | 2026-10-13 19:00:08 UTC | c97d28cc | failed | — | data_source=unknown | — | per_symbol_contributions() takes 3 positional argu... |
| 19-00-54-976572 | h14_pf_margin_selection_audit | 2026-10-13 19:00:54 UTC | c97d28cc | failed | — | data_source=unknown | — | 'ExperimentTracker' object has no attribute 'exper... |
| 19-01-59-371405 | h14_pf_margin_selection_audit | 2026-10-13 19:01:59 UTC | c97d28cc | completed | — | data_source=unknown | 2 artifacts | — |
| 15-44-25-288950 | h28_h25_control | 2026-10-19 15:44:25 UTC | bce2bf18 | completed | — | data_source=unknown | 22 artifacts | — |
| 15-46-01-180776 | h28_h25_causal | 2026-10-19 15:46:01 UTC | bce2bf18 | completed | — | data_source=unknown | 22 artifacts | — |
| 15-46-16-261803 | h28_h10_control | 2026-10-19 15:46:16 UTC | bce2bf18 | completed | — | data_source=unknown | 21 artifacts | — |
| 16-41-44-683912 | h28_h10_causal | 2026-10-19 16:41:44 UTC | bce2bf18 | completed | — | data_source=unknown | 21 artifacts | — |
| 17-38-03-570526 | h28_h21_control | 2026-10-19 17:38:03 UTC | bce2bf18 | completed | — | data_source=unknown | 21 artifacts | — |
| 17-38-21-389139 | h28_h21_causal | 2026-10-19 17:38:21 UTC | bce2bf18 | completed | — | data_source=unknown | 21 artifacts | — |
| 17-38-39-157337 | h28_h22_control | 2026-10-19 17:38:39 UTC | bce2bf18 | completed | — | data_source=unknown | 22 artifacts | — |
| 17-38-50-887609 | h28_h22_causal | 2026-10-19 17:38:50 UTC | bce2bf18 | completed | — | data_source=unknown | 22 artifacts | — |
| 17-39-02-719690 | h28_h25_control | 2026-10-19 17:39:02 UTC | bce2bf18 | completed | — | data_source=unknown | 22 artifacts | — |
| 17-39-12-729639 | h28_h25_causal | 2026-10-19 17:39:12 UTC | bce2bf18 | completed | — | data_source=unknown | 22 artifacts | — |

### New Family (NF) - Recent

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 01-15-02-402660 | nf_20261104_02_cross_asset_... | 2026-11-05 01:15:02 UTC | 79e8f0ea | failed | — | data_source=unknown | — | 'NoneType' object has no attribute 'shift' |
| 01-17-49-208916 | nf_20261104_02_cross_asset_... | 2026-11-05 01:17:49 UTC | 79e8f0ea | completed | — | data_source=unknown | 10 artifacts | — |
| 01-22-22-092087 | nf_20261104_02_cross_asset_... | 2026-11-05 01:22:22 UTC | 79e8f0ea | completed | — | data_source=unknown | 10 artifacts | — |
| 01-24-02-934356 | nf_20261104_02_cross_asset_... | 2026-11-05 01:24:02 UTC | 79e8f0ea | completed | — | data_source=unknown | 10 artifacts | — |
| 02-48-06-511409 | nf_20261105_01_opening_gap | 2026-11-05 02:48:06 UTC | 5b86720b | failed | — | data_source=unknown | — | 'train_wf_sharpe' |
| 02-49-32-323700 | nf_20261105_01_opening_gap | 2026-11-05 02:49:32 UTC | 5b86720b | failed | — | data_source=unknown | — | name 'sel' is not defined |
| 02-49-45-265009 | nf_20261105_01_opening_gap | 2026-11-05 02:49:45 UTC | 5b86720b | failed | — | data_source=unknown | — | name 'train_mask' is not defined |
| 02-50-07-076659 | nf_20261105_01_opening_gap | 2026-11-05 02:50:07 UTC | 5b86720b | failed | — | data_source=unknown | — | name 'rng' is not defined |
| 02-50-47-294718 | nf_20261105_01_opening_gap | 2026-11-05 02:50:47 UTC | 5b86720b | failed | — | data_source=unknown | — | name 'ablations' is not defined |
| 02-51-06-343400 | nf_20261105_01_opening_gap | 2026-11-05 02:51:06 UTC | 5b86720b | completed | — | data_source=unknown | 7 artifacts | — |
| 02-53-13-703271 | nf_20261105_01_opening_gap | 2026-11-05 02:53:13 UTC | 5b86720b | failed | — | data_source=unknown | — | 'train_wf_sharpe' |
| 02-55-28-772744 | nf_20261105_01_opening_gap | 2026-11-05 02:55:28 UTC | 5b86720b | failed | — | data_source=unknown | — | 'train_wf_sharpe' |
| 04-44-31-638354 | nf_20261105_01_opening_gap | 2026-11-05 04:44:31 UTC | 29afd6b1 | completed | — | data_source=unknown | 7 artifacts | — |
| 11-33-50-642571 | nf_20261105_01_opening_gap | 2026-11-05 11:33:50 UTC | cea78aa2 | completed | — | data_source=unknown | 7 artifacts | — |
| 11-50-45-085940 | nf_20261105_06_gold_oil_rv | 2026-11-05 11:50:45 UTC | 808e0487 | failed | — | data_source=unknown | — | CL=F: 4 non-positive price(s) in the fetched panel... |
| 12-16-14-717827 | nf_20261105_06_gold_oil_rv | 2026-11-05 12:16:14 UTC | e5e871fd | failed | — | data_source=unknown | — | CL=F: 4 non-positive price(s) in the fetched panel... |
| 12-24-33-350043 | nf_20261105_06_gold_oil_rv | 2026-11-05 12:24:33 UTC | 4c0f05dd | completed | — | data_source=unknown | 7 artifacts | — |
| 12-36-06-158635 | nf_20261105_07_skew_tail_ti... | 2026-11-05 12:36:06 UTC | 10f62a52 | completed | — | data_source=unknown | 7 artifacts | — |
| 13-22-09-693533 | nf_20261105_08_fomc_event_d... | 2026-11-05 13:22:09 UTC | 1ad8b196 | completed | — | data_source=unknown | 7 artifacts | — |
| 13-32-16-258120 | nf_20261105_09_turn_of_month | 2026-11-05 13:32:16 UTC | 0cb44dfd | completed | — | data_source=unknown | 7 artifacts | — |
| 13-32-55-648939 | nf_20261105_09_turn_of_month | 2026-11-05 13:32:55 UTC | 0cb44dfd | completed | — | data_source=unknown | 7 artifacts | — |
| 15-24-22-849461 | nf_20261105_10_equity_bond_... | 2026-11-05 15:24:22 UTC | dbcaab55 | completed | — | data_source=unknown | 8 artifacts | — |
| 15-40-24-218763 | nf_20261105_10_equity_bond_... | 2026-11-05 15:40:24 UTC | 953a8d25 | completed | — | data_source=unknown | 8 artifacts | — |
| 18-05-46-174209 | nf_20261105_10_equity_bond_... | 2026-11-05 18:05:46 UTC | a02859f9 | completed | — | data_source=unknown | 8 artifacts | — |
| 18-09-06-924039 | nf_20261105_13_idiosyncrati... | 2026-11-05 18:09:06 UTC | e414964a | completed | — | data_source=unknown | 8 artifacts | — |
| 18-11-49-464520 | nf_20261105_10_equity_bond_... | 2026-11-05 18:11:49 UTC | e10507b6 | completed | — | data_source=unknown | 8 artifacts | — |
| 18-12-36-229696 | nf_20261105_10_equity_bond_... | 2026-11-05 18:12:36 UTC | f2157468 | completed | — | data_source=unknown | 8 artifacts | — |
| 19-06-45-864432 | nf_20261105_16_usd_macro | 2026-11-05 19:06:45 UTC | 76db131e | completed | oos_sharpe=0.6089<br>oos_trades=289.0000 | data_source=unknown | 1 artifacts | — |
| 19-09-07-377344 | nf_20261105_16_usd_macro | 2026-11-05 19:09:07 UTC | 76db131e | completed | oos_sharpe=0.8141<br>oos_trades=88.0000 | data_source=unknown | 1 artifacts | — |
| 22-15-20-636539 | nf_20261105_18_concentratio... | 2026-11-05 22:15:20 UTC | b2e2631f | completed | oos_sharpe=0.7239<br>oos_trades=364.0000 | data_source=unknown | 1 artifacts | — |
| 01-28-49-517869 | nf_20261105_19_pead | 2026-11-06 01:28:49 UTC | 7d442fe4 | completed | oos_sharpe=0.7680<br>oos_trades=775.0000 | data_source=unknown | 1 artifacts | — |
| 01-30-29-259047 | nf_20261105_19_pead | 2026-11-06 01:30:29 UTC | 7d442fe4 | completed | oos_sharpe=0.8261<br>oos_trades=942.0000 | data_source=unknown | 1 artifacts | — |
| 02-00-06-752931 | nf_20261105_10_equity_bond_... | 2026-11-06 02:00:06 UTC | f251af3c | completed | — | data_source=unknown | 8 artifacts | — |
| 02-17-43-039138 | nf_20261105_10_equity_bond_... | 2026-11-06 02:17:43 UTC | fdf76d7e | completed | — | data_source=unknown | 8 artifacts | — |
| 03-04-40-778747 | nf_20261106_01_miner_gold_rv | 2026-11-06 03:04:40 UTC | e00c722e | completed | oos_sharpe=0.3287<br>oos_trades=1286.0000 | data_source=unknown | 1 artifacts | — |
| 03-36-48-479398 | nf_20261105_10_equity_bond_... | 2026-11-06 03:36:48 UTC | d86fe229 | completed | — | data_source=unknown | 8 artifacts | — |
| 04-23-47-511988 | nf_20261105_10_equity_bond_... | 2026-11-06 04:23:47 UTC | d6e4b3cf | completed | — | data_source=unknown | 8 artifacts | — |
| 13-51-39-621785 | nf_20261106_14_fxy_safehaven | 2026-11-06 13:51:39 UTC | 012ea055 | REJECT | — | data_source=unknown | — | — |
| 13-53-01-203238 | nf_20261106_14_fxy_safehaven | 2026-11-06 13:53:01 UTC | 012ea055 | REJECT | — | data_source=unknown | — | — |
| 14-35-47-117897 | nf_20261106_16_kre_stress | 2026-11-06 14:35:47 UTC | 92e83d0a | REJECT | — | data_source=unknown | — | — |
| 14-46-17-382075 | nf_20261106_19_lqd_hyg_quality | 2026-11-06 14:46:17 UTC | ae105ef2 | REJECT | — | data_source=unknown | — | — |
| 15-35-20-311536 | nf_20261106_17_xop_xle_energy | 2026-11-06 15:35:20 UTC | ab6bcd73 | REJECT | — | data_source=unknown | — | — |
| 15-41-44-600009 | nf_20261106_20_xly_xlp_cons... | 2026-11-06 15:41:44 UTC | d744de45 | REJECT | — | data_source=unknown | — | — |
| 15-52-07-899045 | nf_20261106_22_smh_qqq_semi... | 2026-11-06 15:52:07 UTC | e07cae0f | REJECT | — | data_source=unknown | — | — |
| 16-36-24-805357 | nf_20261106_25_max_lottery | 2026-11-06 16:36:24 UTC | f52931ae | REJECT | — | data_source=unknown | — | — |
| 23-06-21-278809 | nf_20261106_27_sphb_splv_style | 2026-11-06 23:06:21 UTC | f537aa8c | REJECT | — | data_source=unknown | — | — |
| 23-32-03-009243 | nf_20261106_29_rsp_spy_breadth | 2026-11-06 23:32:03 UTC | 4cef14bd | REJECT | — | data_source=unknown | — | — |
| 03-38-17-251553 | nf_20261107_04_amihud_illiq | 2026-11-07 03:38:17 UTC | bfc38559 | REJECT | oos_sharpe=0.8693<br>oos_trades=971<br>oos_pf=1.1758<br>oos_max_dd=-0.0316<br>wf_ratio=0.9634<br>worst_regime=-0.9190<br>benchmark_p=1.0000<br>benchmark_ir=-0.7730... | data_source=unknown | — | — |
| 04-18-08-373455 | nf_20261107_04_amihud_illiq | 2026-11-07 04:18:08 UTC | 7a3b454e | REJECT | oos_sharpe=0.8693<br>oos_trades=971<br>oos_pf=1.1758<br>oos_max_dd=-0.0316<br>wf_ratio=0.9634<br>worst_regime=-0.9190<br>benchmark_p=1.0000<br>benchmark_ir=-0.7730... | data_source=unknown | — | — |
| 05-23-54-586792 | nf_20261107_07_realized_sem... | 2026-11-07 05:23:54 UTC | a47dfb51 | REJECT | oos_sharpe=0.8114<br>oos_trades=1174<br>oos_pf=1.1731<br>oos_max_dd=-0.0292<br>wf_ratio=0.9099<br>worst_regime=-0.7603<br>benchmark_p=1.0000<br>benchmark_ir=-0.7787... | data_source=unknown | — | — |
| 10-42-29-663331 | nf_20261107_09_max_lottery | 2026-11-07 10:42:29 UTC | d0ecfa18 | REJECT | — | data_source=unknown | — | — |

### New Family (NF) - Factor/Other

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 21-11-25-266808 | h16_factor_timing | 2026-10-13 21:11:25 UTC | c4372053 | failed | — | data_source=unknown | — | Encountered all NA values |
| 21-11-45-843908 | h16_factor_timing | 2026-10-13 21:11:45 UTC | c4372053 | completed | — | data_source=unknown | 11 artifacts | — |
| 21-13-09-580962 | h16_factor_timing | 2026-10-13 21:13:09 UTC | c4372053 | completed | — | data_source=unknown | 11 artifacts | — |
| 21-18-23-178134 | h16_factor_timing | 2026-10-13 21:18:23 UTC | c4372053 | completed | — | data_source=unknown | 11 artifacts | — |
| 21-22-02-751156 | h16_factor_timing | 2026-10-13 21:22:02 UTC | c4372053 | completed | — | data_source=unknown | 11 artifacts | — |

### Other / Uncategorized

| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |
|---|---|---|---|---|---|---|---|---|
| 17-08-58-697938 | alternative_strategies_v1 | 2026-10-10 17:08:58 UTC | 41a04698 | failed | — | data_source=unknown | 2 artifacts | Unknown strategy: ema_crossover. Available: ['ma_c... |
| 17-09-34-333145 | alternative_strategies_v1 | 2026-10-10 17:09:34 UTC | 41a04698 | completed | — | data_source=unknown | 6 artifacts | — |
| 08-05-24-884142 | exp2 | 2026-11-03 08:05:24 UTC | 2d27f108 | completed | — | data_source=unknown | — | — |

## Git Commit Timeline

| Git Commit | Date | Experiments | Categories |
|---|---|---|---|
| 41a04698 | 2026-10-10 17:00:29 UTC to 2026-10-10 17:09:34 UTC | 10 | Baseline / MA Crossover, Other / Uncategorized |
| 2bb82523 | 2026-10-10 20:56:30 UTC to 2026-10-10 21:09:06 UTC | 5 | Cross-Sectional Momentum, Time-Series Momentum |
| 2ac48e7c | 2026-10-10 21:27:13 UTC to 2026-10-10 21:28:20 UTC | 2 | Regime-Gated |
| e6a36808 | 2026-10-10 21:58:07 UTC to 2026-10-10 21:59:16 UTC | 3 | Time-Series Momentum |
| cd8cd603 | 2026-10-10 22:59:01 UTC | 1 | Time-Series Momentum |
| ffb2647b | 2026-10-11 00:25:56 UTC to 2026-10-11 00:26:35 UTC | 4 | Time-Series Momentum |
| a6b40706 | 2026-10-11 00:34:05 UTC | 1 | Time-Series Momentum |
| f7ab792b | 2026-10-11 02:44:40 UTC | 1 | Time-Series Momentum |
| eee6cd45 | 2026-10-11 02:46:37 UTC | 1 | Time-Series Momentum |
| 8193bdcf | 2026-10-11 07:18:25 UTC to 2026-10-11 07:18:39 UTC | 2 | Time-Series Momentum |
| 0df82803 | 2026-10-11 08:02:22 UTC | 1 | Time-Series Momentum |
| 8ad8f231 | 2026-10-11 15:21:31 UTC | 1 | Time-Series Momentum |
| 0174ca64 | 2026-10-11 15:53:04 UTC to 2026-10-11 15:54:17 UTC | 3 | Time-Series Momentum |
| ab2141a6 | 2026-10-11 16:44:06 UTC to 2026-10-11 16:46:06 UTC | 2 | Time-Series Momentum |
| 0fdf2488 | 2026-10-11 16:52:38 UTC | 1 | Time-Series Momentum |
| 3d4e7096 | 2026-10-11 17:23:43 UTC to 2026-10-11 17:24:14 UTC | 2 | Time-Series Momentum |
| d9b6b082 | 2026-10-11 17:41:18 UTC | 1 | Time-Series Momentum |
| d7942dbd | 2026-10-11 18:36:51 UTC to 2026-10-11 20:25:36 UTC | 4 | Hypothesis H10-H29 |
| 80154136 | 2026-10-13 12:51:06 UTC | 1 | Hypothesis H10-H29 |
| 4a2c5939 | 2026-10-13 14:26:42 UTC to 2026-10-13 14:35:58 UTC | 2 | Hypothesis H10-H29 |
| c97d28cc | 2026-10-13 18:55:24 UTC to 2026-10-13 19:01:59 UTC | 6 | Hypothesis H10-H29 |
| c4372053 | 2026-10-13 21:11:25 UTC to 2026-10-13 21:22:02 UTC | 5 | New Family (NF) - Factor/Other |
| dcf5f8be | 2026-10-13 21:46:52 UTC to 2026-10-13 21:51:45 UTC | 3 | Volatility / VRP |
| 11f5d01d | 2026-10-13 22:13:37 UTC to 2026-10-13 22:14:50 UTC | 3 | Time-Series Momentum |
| 532f0e56 | 2026-10-13 22:36:40 UTC to 2026-10-13 22:40:41 UTC | 5 | Volume Predictive |
| 02e4025d | 2026-10-13 23:06:33 UTC | 1 | Volume Predictive |
| 61290014 | 2026-10-13 23:22:46 UTC to 2026-10-13 23:27:52 UTC | 5 | Time-Series Momentum |
| fa4c1d0f | 2026-10-14 07:11:16 UTC to 2026-10-14 07:32:43 UTC | 6 | Time-Series Momentum |
| 37224854 | 2026-10-14 08:20:39 UTC to 2026-10-14 08:48:49 UTC | 6 | Baseline / MA Crossover, Time-Series Momentum |
| 48b045ed | 2026-10-14 09:28:59 UTC to 2026-10-14 09:39:07 UTC | 3 | Time-Series Momentum |
| 26d08fcf | 2026-10-14 10:04:52 UTC | 1 | Time-Series Momentum |
| c9845a5f | 2026-10-14 11:53:37 UTC | 1 | Time-Series Momentum |
| f3bb0f30 | 2026-10-14 18:10:38 UTC to 2026-10-14 18:13:09 UTC | 2 | Time-Series Momentum |
| fd0635e3 | 2026-10-14 18:52:08 UTC | 1 | Time-Series Momentum |
| 499913ba | 2026-10-14 19:46:14 UTC to 2026-10-14 20:02:45 UTC | 3 | Time-Series Momentum |
| cecc9d54 | 2026-10-14 20:08:34 UTC | 1 | Time-Series Momentum |
| bce2bf18 | 2026-10-19 15:44:25 UTC to 2026-10-19 17:39:12 UTC | 10 | Hypothesis H10-H29 |
| 7cb48c10 | 2026-10-19 18:56:08 UTC to 2026-10-19 18:56:58 UTC | 2 | Time-Series Momentum |
| 2d27f108 | 2026-11-03 08:05:24 UTC | 1 | Other / Uncategorized |
| 79e8f0ea | 2026-11-05 01:15:02 UTC to 2026-11-05 01:24:02 UTC | 4 | New Family (NF) - Recent |
| 763f2566 | 2026-11-05 01:42:41 UTC to 2026-11-05 01:43:20 UTC | 3 | Volatility / VRP |
| 5b86720b | 2026-11-05 02:48:06 UTC to 2026-11-05 02:55:28 UTC | 8 | New Family (NF) - Recent |
| 29afd6b1 | 2026-11-05 04:44:31 UTC | 1 | New Family (NF) - Recent |
| cea78aa2 | 2026-11-05 11:33:50 UTC | 1 | New Family (NF) - Recent |
| 808e0487 | 2026-11-05 11:50:45 UTC | 1 | New Family (NF) - Recent |
| e5e871fd | 2026-11-05 12:16:14 UTC | 1 | New Family (NF) - Recent |
| 4c0f05dd | 2026-11-05 12:24:33 UTC | 1 | New Family (NF) - Recent |
| 10f62a52 | 2026-11-05 12:36:06 UTC | 1 | New Family (NF) - Recent |
| 1ad8b196 | 2026-11-05 13:22:09 UTC | 1 | New Family (NF) - Recent |
| 0cb44dfd | 2026-11-05 13:32:16 UTC to 2026-11-05 13:32:55 UTC | 2 | New Family (NF) - Recent |
| dbcaab55 | 2026-11-05 15:24:22 UTC | 1 | New Family (NF) - Recent |
| 953a8d25 | 2026-11-05 15:40:24 UTC | 1 | New Family (NF) - Recent |
| a02859f9 | 2026-11-05 18:05:46 UTC | 1 | New Family (NF) - Recent |
| e414964a | 2026-11-05 18:09:06 UTC | 1 | New Family (NF) - Recent |
| e10507b6 | 2026-11-05 18:11:49 UTC | 1 | New Family (NF) - Recent |
| f2157468 | 2026-11-05 18:12:36 UTC | 1 | New Family (NF) - Recent |
| a683fad3 | 2026-11-05 18:20:38 UTC | 1 | Regime-Gated |
| 76db131e | 2026-11-05 19:06:45 UTC to 2026-11-05 19:09:07 UTC | 2 | New Family (NF) - Recent |
| 417cc7d4 | 2026-11-05 22:09:06 UTC | 1 | Regime-Gated |
| b2e2631f | 2026-11-05 22:15:20 UTC | 1 | New Family (NF) - Recent |
| 7d442fe4 | 2026-11-06 01:28:49 UTC to 2026-11-06 01:30:29 UTC | 2 | New Family (NF) - Recent |
| f251af3c | 2026-11-06 02:00:06 UTC | 1 | New Family (NF) - Recent |
| fdf76d7e | 2026-11-06 02:17:43 UTC | 1 | New Family (NF) - Recent |
| e00c722e | 2026-11-06 03:04:40 UTC | 1 | New Family (NF) - Recent |
| d86fe229 | 2026-11-06 03:36:48 UTC | 1 | New Family (NF) - Recent |
| d6e4b3cf | 2026-11-06 04:23:47 UTC | 1 | New Family (NF) - Recent |
| e75eee81 | 2026-11-06 13:35:05 UTC | 1 | Volatility / VRP |
| 012ea055 | 2026-11-06 13:51:39 UTC to 2026-11-06 13:53:01 UTC | 2 | New Family (NF) - Recent |
| 92e83d0a | 2026-11-06 14:35:47 UTC | 1 | New Family (NF) - Recent |
| ae105ef2 | 2026-11-06 14:46:17 UTC | 1 | New Family (NF) - Recent |
| ab6bcd73 | 2026-11-06 15:35:20 UTC | 1 | New Family (NF) - Recent |
| d744de45 | 2026-11-06 15:41:44 UTC | 1 | New Family (NF) - Recent |
| e07cae0f | 2026-11-06 15:52:07 UTC | 1 | New Family (NF) - Recent |
| f52931ae | 2026-11-06 16:36:24 UTC | 1 | New Family (NF) - Recent |
| 5daeccd1 | 2026-11-06 21:57:20 UTC | 1 | Volatility / VRP |
| f537aa8c | 2026-11-06 23:06:21 UTC | 1 | New Family (NF) - Recent |
| 4cef14bd | 2026-11-06 23:32:03 UTC | 1 | New Family (NF) - Recent |
| bfc38559 | 2026-11-07 03:38:17 UTC | 1 | New Family (NF) - Recent |
| 7a3b454e | 2026-11-07 04:18:08 UTC | 1 | New Family (NF) - Recent |
| a47dfb51 | 2026-11-07 05:23:54 UTC | 1 | New Family (NF) - Recent |
| 00d209e6 | 2026-11-07 10:33:55 UTC | 1 | Volatility / VRP |
| d0ecfa18 | 2026-11-07 10:42:29 UTC | 1 | New Family (NF) - Recent |
| 022a9e16 | 2026-11-10 17:24:06 UTC | 1 | Regime-Gated |
