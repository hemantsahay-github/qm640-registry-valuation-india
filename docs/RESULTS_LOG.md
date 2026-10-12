# Results Log — QM 640 Capstone

Each entry is written automatically by `src/pipeline.py`.

## ETL — 2026-10-10 23:26

**Data:** PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)

**Key results**

```json
{
  "rows_raw": 1818,
  "rows_after_masking": 1818,
  "rows_analysis": 1710,
  "exclusions": {
    "out_of_scope_doc_type": 63,
    "missing_core_value": 25,
    "duplicate_record": 20
  },
  "dpdp_columns_dropped": [
    "executant_name",
    "claimant_name",
    "doc_no"
  ],
  "dpdp_free_text_redactions": 1818,
  "anchored_share": 0.1339
}
```

**Interpretation**

Raw Index-II text was parsed from Marathi, personal data removed under DPDP controls, scope and quality filters applied, and features derived. Compare rows_analysis with N = 1,068.

**Output files**

- `/home/claude/work/qm640-registry-valuation-india/data/processed/analysis_dataset.csv`

---
## EDA — 2026-10-10 23:26

**Data:** PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)

**Key results**

```json
{
  "rows": 1710,
  "columns": 30,
  "meets_min_N_1068": true,
  "total_nulls_after_cleaning": 0,
  "nulls_before_cleaning": {
    "carpet_area_m2": 26
  },
  "columns_with_nulls": [],
  "records_by_district": {
    "Pune": 906,
    "Thane": 804
  },
  "records_by_fy": {
    "2023-24": 562,
    "2024-25": 560,
    "2025-26": 588
  },
  "mean_value_m2": 118673,
  "median_value_m2": 108711,
  "median_r_ratio": 1.3108,
  "anchored_share": 0.1339,
  "corr_ln_value_ln_asr": 0.93,
  "top_abs_corr_with_ln_value": {
    "ln_asr_rate_m2": 0.93,
    "dist_cbd_km": 0.789,
    "municipal_corp": 0.411,
    "anchored": 0.239
  },
  "iqr_outliers": {
    "consideration_inr": 48,
    "asr_value_inr": 38,
    "stamp_duty_inr": 48,
    "carpet_area_m2": 47,
    "floor_no": 0,
    "dist_rail_km": 51,
    "dist_cbd_km": 60,
    "asr_rate_m2": 0,
    "value_m2": 9,
    "r_ratio": 10
  }
}
```

**Interpretation**

Profiles the analysis dataset: completeness, distributions, central tendency, correlations and outliers. The R-ratio histogram is the visual precursor to RQ1.

**Output files**

- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/01_dataset_info.txt`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/02_null_values.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/02b_null_values_before_cleaning.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/03_descriptive_stats.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/04_category_counts.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/05_group_means.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/06_correlation_pearson.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/06_correlation_spearman.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/07_outliers_iqr.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/fig_01_histograms.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/fig_02_boxplots.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/fig_03_correlation_heatmap.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/fig_04_value_vs_asr.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/fig_05_r_ratio_distribution.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/eda/fig_06_counts.png`

---
## RQ1 — 2026-10-10 23:26

**Data:** PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)

**Key results**

```json
{
  "n_analysed": 1710,
  "n_in_bunching_range": 1704,
  "window": "[0.98, 1.02)",
  "bins_in_window": 4,
  "observed_in_window": 229.0,
  "counterfactual_in_window": 23.4,
  "excess_count_B": 205.6,
  "b_normalised": 35.168,
  "b_bootstrap_ci95": [
    25.567,
    52.734
  ],
  "p_value_H0_b_eq_0_one_sided": 0.0,
  "decision_alpha_0.05": "Reject H0 (bunching present)",
  "excess_share_of_transactions": 0.1207,
  "anchored_share_observed": 0.1339,
  "anchored_share_ci95_wilson": [
    0.1186,
    0.1509
  ],
  "ci_half_width": 0.0161,
  "robustness_b_range": [
    21.878,
    36.569
  ],
  "by_segment": [
    {
      "segment": "district",
      "level": "Pune",
      "n": 906,
      "anchored_share": 0.1181,
      "b": 40.255
    },
    {
      "segment": "district",
      "level": "Thane",
      "n": 804,
      "anchored_share": 0.1517,
      "b": 31.365
    },
    {
      "segment": "fy",
      "level": "2023-24",
      "n": 562,
      "anchored_share": 0.1566,
      "b": 17.861
    },
    {
      "segment": "fy",
      "level": "2024-25",
      "n": 560,
      "anchored_share": 0.1393,
      "b": 81.253
    },
    {
      "segment": "fy",
      "level": "2025-26",
      "n": 588,
      "anchored_share": 0.1071,
      "b": 63.082
    }
  ]
}
```

**Interpretation**

b > 0 with a bootstrap CI excluding 0 means more transactions sit at the ASR threshold than a smooth distribution predicts — evidence of circle-rate anchoring. Excess share is the fraction of all transactions that moved to the threshold.

**Output files**

- `/home/claude/work/qm640-registry-valuation-india/outputs/rq1/fig_rq1_bootstrap.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq1/fig_rq1_bunching_by_district.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq1/fig_rq1_bunching_pooled.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq1/rq1_bins.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq1/rq1_by_segment.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq1/rq1_robustness.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq1/summary.json`

---
## RQ2 — 2026-10-11 00:00

**Data:** PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)

**Key results**

```json
{
  "n": 1710,
  "k_full": 12,
  "u_tested": 11,
  "R2_restricted": 0.864,
  "R2_full": 0.891,
  "delta_R2": 0.027,
  "adj_R2_full": 0.8902,
  "cohens_f2_increment": 0.2477,
  "partial_F": 38.209,
  "df": [
    11,
    1697
  ],
  "p_partial_F": 5.95e-74,
  "robust_wald_F_HC3": 40.548,
  "robust_wald_p": 2.6e-78,
  "decision_alpha_0.05": "Reject H0: attributes add explanatory power",
  "asr_elasticity": 1.2366,
  "asr_elasticity_ci95": [
    1.1943,
    1.2788
  ],
  "test_asr_elasticity_eq_1_p": 5.02e-28,
  "significant_attributes_hc3": [
    "Floor (per floor)",
    "New sale (promoter)",
    "Parking included",
    "Distance to CBD (km)",
    "Thane (vs. Pune)",
    "FY 2024\u201325 (vs. 2023\u201324)",
    "FY 2025\u201326 (vs. 2023\u201324)"
  ],
  "not_significant_hc3": [
    "ln carpet area (m\u00b2)",
    "Carpet area recorded directly",
    "Distance to station (km)",
    "Municipal corporation"
  ],
  "significant_under_cluster_se": [
    "Floor (per floor)",
    "New sale (promoter)",
    "Parking included",
    "Thane (vs. Pune)",
    "FY 2024\u201325 (vs. 2023\u201324)",
    "FY 2025\u201326 (vs. 2023\u201324)"
  ],
  "top3_by_abs_std_beta": [
    "ln ASR rate (\u20b9/m\u00b2)",
    "FY 2025\u201326 (vs. 2023\u201324)",
    "New sale (promoter)"
  ],
  "diagnostics": {
    "breusch_pagan_LM": 114.987,
    "breusch_pagan_p": 6.15e-19,
    "jarque_bera": 74.987,
    "jarque_bera_p": 5.21e-17,
    "resid_skew": -0.5,
    "resid_kurtosis": 3.228,
    "durbin_watson": 2.029,
    "condition_number": 1969.5,
    "max_vif": 5.178,
    "vars_vif_over_5": [
      "ln_asr_rate_m2"
    ]
  }
}
```

**Interpretation**

A significant partial F test means property and locational attributes explain registered value beyond the ASR rate. A small dR^2 together with an ASR elasticity close to 1 would itself point to anchoring (registered values tracking the circle rate). Read significance with HC3 errors; the clustered errors are the conservative check.

**Output files**

- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/fig_rq2_diagnostics.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/fig_rq2_r2_increase.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/fig_rq2_standardized_coefficients.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/rq2_coefficients_full.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/rq2_coefficients_restricted.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/rq2_diagnostics.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/rq2_full_model_summary.txt`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/rq2_model_comparison.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/rq2_vif.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq2/summary.json`

---
## RQ3 — 2026-10-12 08:10

**Data:** PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)

**Key results**

```json
{
  "n_train": 1306,
  "n_test": 404,
  "min_test_required": 199,
  "test_micro_markets": [
    "Badlapur",
    "Bhiwandi",
    "Dhanori",
    "Kalwa",
    "Kasarvadavali",
    "Pimple Saudagar",
    "Ulhasnagar",
    "Viman Nagar"
  ],
  "n_test_micro_markets": 8,
  "best_params": {
    "subsample": 0.7,
    "reg_lambda": 1.0,
    "n_estimators": 200,
    "min_child_weight": 10,
    "max_depth": 4,
    "learning_rate": 0.05,
    "colsample_bytree": 1.0
  },
  "cv_MAE_log_best": 0.13536,
  "test_metrics_OLS": {
    "RMSE_log": 0.1327,
    "MAE_log": 0.1017,
    "R2_log": 0.8761,
    "RMSE_inr_m2": 15906.8782,
    "MAE_inr_m2": 11161.0919,
    "MAPE_pct": 10.3733
  },
  "test_metrics_XGB": {
    "RMSE_log": 0.1417,
    "MAE_log": 0.1086,
    "R2_log": 0.8587,
    "RMSE_inr_m2": 17260.7128,
    "MAE_inr_m2": 12120.0373,
    "MAPE_pct": 11.2932
  },
  "paired_tests": {
    "n_test": 404,
    "mean_d": -0.00692,
    "sd_d": 0.05215,
    "cohens_dz": -0.13259,
    "paired_t": -2.66499,
    "df": 403,
    "p_t_one_sided": 0.996,
    "wilcoxon_W": 35010.0,
    "p_wilcoxon_one_sided": 0.99397,
    "dm_hln": -2.66499,
    "p_dm_one_sided": 0.996,
    "cluster_boot_ci95_mean_d": [
      -0.013333622817139273,
      -0.0008726193060122635
    ],
    "p_cluster_boot": 0.9905,
    "share_cases_xgb_better": 0.47277
  },
  "decision_alpha_0.05": "Fail to reject H0: no significant advantage for XGBoost",
  "grouped_cv_mean_MAE_log": {
    "OLS": 0.11166,
    "XGB": 0.11898,
    "folds_xgb_better": 0
  },
  "top5_shap": [
    "ln ASR rate (\u20b9/m\u00b2)",
    "New sale (promoter)",
    "FY 2025\u201326 (vs. 2023\u201324)",
    "Floor (per floor)",
    "ln carpet area (m\u00b2)"
  ]
}
```

**Interpretation**

Models are compared only on micro-markets never seen in training. A positive mean d with p < .05 (paired t, Wilcoxon, Diebold-Mariano) means XGBoost predicts registered value more accurately than OLS. The cluster bootstrap is the conservative check because errors within a locality are correlated. SHAP shows which features drive the XGBoost predictions.

**Output files**

- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/best_params.json`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/fig_rq3_error_comparison.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/fig_rq3_pred_vs_actual.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/fig_rq3_shap_beeswarm.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/fig_rq3_shap_importance.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/rq3_bias_audit.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/rq3_grouped_cv.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/rq3_paired_tests.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/rq3_shap_importance.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/rq3_test_metrics.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/rq3_test_predictions.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/summary.json`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq3/xgb_model.json`

---
## RQ4 — 2026-10-12 08:16

**Data:** PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)

**Key results**

```json
{
  "n": 1710,
  "events_anchored": 229,
  "predictors": 12,
  "EPV": 19.1,
  "EPV_ok_ge_10": true,
  "LR_chi2": 59.863,
  "LR_df": 12,
  "LR_p": 2.39e-08,
  "mcfadden_pseudo_R2": 0.0445,
  "decision_alpha_0.05": "Reject H0: predictors are associated with anchoring",
  "significant_predictors_OR": {
    "Floor (per floor)": 0.983,
    "New sale (promoter)": 0.409,
    "FY 2025\u201326 (vs. 2023\u201324)": 0.642
  },
  "box_tidwell_violations": [
    "ln_asr_rate_m2"
  ],
  "test_logistic": {
    "AUC": 0.5927,
    "Brier": 0.1073,
    "threshold": 0.1223,
    "precision": 0.1447,
    "recall": 0.6735,
    "F1": 0.2383,
    "TP": 33,
    "FP": 195,
    "FN": 16,
    "TN": 160
  },
  "test_xgboost": {
    "AUC": 0.5715,
    "Brier": 0.1101,
    "threshold": 0.1595,
    "precision": 0.1481,
    "recall": 0.4082,
    "F1": 0.2174,
    "TP": 20,
    "FP": 115,
    "FN": 29,
    "TN": 240
  },
  "auc_diff_xgb_minus_logit_ci95": [
    -0.0803,
    0.0367
  ],
  "value_model_for_cf": "OLS hedonic (RQ3: no significant XGBoost advantage)",
  "cf_pooled_median": 1.3095,
  "cf_pooled_ci95": [
    1.2795,
    1.358
  ],
  "cf_by_district": {
    "Pune": 1.3477,
    "Thane": 1.2898
  },
  "cf_by_fy": {
    "2023-24": 1.2428,
    "2024-25": 1.3578,
    "2025-26": 1.4306
  },
  "micro_markets_total": 35,
  "micro_markets_reportable": 0,
  "median_anchored_per_micro_market": 6.0,
  "eb_shrinkage_tau2_sigma2": [
    0.00665,
    0.00431
  ],
  "sro_reportable": "5 of 12 SROs",
  "residex_check": "RESIDEX file not present \u2014 run direction check after downloading data/external/residex/residex.csv"
}
```

**Interpretation**

Odds ratios above 1 mark characteristics that make anchoring more likely; the LR test asks whether any predictor matters at all, and AUC on held-out micro-markets shows how well anchoring can be predicted. The correction factor CF is the median of predicted / registered value for anchored deals: CF = 1.20 means registered values understate the model value by about 20%. Because non-anchored deals may also be understated, CF is a lower bound.

**Output files**

- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/correction_factors.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/fig_rq4_calibration.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/fig_rq4_correction_factors.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/fig_rq4_odds_ratios.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/fig_rq4_roc.png`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/rq4_box_tidwell.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/rq4_cf_by_segment.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/rq4_cf_by_sro.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/rq4_classification_test_metrics.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/rq4_logit_odds_ratios.csv`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/rq4_logit_summary.txt`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/summary.json`
- `/home/claude/work/qm640-registry-valuation-india/outputs/rq4/synthetic_truth_check.json`

---
## RQ4 — SYNTHETIC TRUTH CHECK — 2026-10-12 08:16

**Data:** PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)

**Key results**

```json
{
  "anchored_matched": 229,
  "true_cf_median_pooled": 1.3788,
  "estimated_cf_median_pooled": 1.3095,
  "estimate_over_truth": 0.9498,
  "true_cf_by_district": {
    "Pune": 1.4017,
    "Thane": 1.3622
  },
  "estimated_cf_by_district": {
    "Pune": 1.3477,
    "Thane": 1.2898
  },
  "note": "Estimate < truth is expected: the value model is trained on non-anchored deals, which the generator also understates by 0-12% (mean ~6%). The correction factor is therefore a LOWER BOUND, as stated in the synopsis limitations."
}
```

**Interpretation**

The pipeline's correction factor (1.31) recovers 95% of the true factor (1.38) and preserves the district ordering (Pune > Thane). The 5% shortfall equals the under-statement built into non-anchored deals, confirming that the correction factor is a conservative lower bound.

**Output files**

- `outputs/rq4/synthetic_truth_check.json`

---
