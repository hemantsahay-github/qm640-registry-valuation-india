# Results Log — QM 640 Capstone

Each entry is written automatically by `src/pipeline.py`.

## ETL — 2026-10-10 23:23

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
## EDA — 2026-10-10 23:23

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
## RQ1 — 2026-10-10 23:23

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
