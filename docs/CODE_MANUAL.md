# Code Manual (Ready Reckoner)

**Project:** Correcting for Circle-Rate Anchoring in Indian Residential Property Valuation: A Registry-Based Machine Learning Study
**Author / IP owner:** Hemant Kumar Sahay · QM 640 Data Analytics Capstone, Walsh College
**Manual version:** 1.1 (11 October 2026), covering Stage 0 (setup), ETL, EDA, RQ1 and RQ2. Sections for RQ3–RQ4 are added as each stage is run.

---

## 1. One-page overview

| Step | Command | Reads | Writes | Answers |
|---|---|---|---|---|
| 0 Sample size | `python scripts/sample_size.py` | — | `outputs/sample_size.csv` | Synopsis Table 4 |
| 1 Collect | `python -m src.ingest.igr_index2 --district Pune` | IGR portal | `data/raw/index2_raw.csv` | — |
| 1v Validate | `python -m src.ingest.synthetic_validation` | — | `data/raw/index2_raw_SYNTHETIC.csv` | — |
| 2 ETL | `python -m src.pipeline --stage etl [--synthetic]` | raw CSV | `data/interim/…`, `data/processed/…` | Data readiness |
| 3 EDA | `python -m src.pipeline --stage eda` | analysis dataset | `outputs/eda/` | Data profile |
| 4 RQ1 | `python -m src.pipeline --stage rq1` | analysis dataset | `outputs/rq1/` | Extent of anchoring |
| 5 RQ2 | `--stage rq2` | analysis dataset | `outputs/rq2/` | Drivers beyond ASR |
| 6 RQ3 | `--stage rq3` | analysis dataset | `outputs/rq3/` | XGBoost vs OLS |
| 7 RQ4 | `--stage rq4` | analysis dataset + RQ3 model | `outputs/rq4/` | Anchoring drivers, correction factor |

Every stage adds a dated entry to `docs/RESULTS_LOG.md`. Each entry has the data label (synthetic or study), the key numbers, an interpretation and the file list. Use that log when you write the interim and final reports.

## 2. Folder map and purpose

| Path | Purpose | Committed? |
|---|---|---|
| `src/config.py` | Single source of truth: paths, study period, anchoring window, bin width, seeds, DPDP whitelist | Yes |
| `src/pipeline.py` | Command-line entry point; runs one stage at a time and logs results | Yes |
| `src/etl.py` | Extract → translate → mask → clean → feature → load | Yes |
| `src/eda.py` | Exploratory data analysis tables and figures | Yes |
| `src/ingest/` | Data acquisition (portal capture, synthetic validation data) | Yes |
| `src/clean/` | Marathi translation, Index-II parsing, DPDP masking | Yes |
| `src/features/` | Derived variables, OSM distances | Yes |
| `src/models/` | One module per research question | Yes |
| `src/utils/` | Results logger, figure style | Yes |
| `data/raw/` | Portal captures, which contain names | **Never** |
| `data/interim/` | Masked, English, pre-filter | No (local/Drive) |
| `data/processed/` | Analysis-ready, de-identified | Yes (publishable view) |
| `data/external/` | ASR, RESIDEX, RBI, OSM reference files | Yes |
| `outputs/<stage>/` | RQ-wise CSV, PNG, `summary.json` | Yes |
| `docs/` | This manual, results log, data dictionary, provenance log, Emergent.ai integration script | Yes |
| `colab/` | Google Colab runner for large data | Yes |
| `tests/` | Unit tests (`pytest`) | Yes |

## 3. File-by-file reference

### 3.1 `src/config.py`
* **Purpose:** keeps every tunable value in one place, so a change propagates to all stages.
* **Key values:** `ANCHOR_LO/HI = 0.98/1.02`; `BIN_WIDTH = 0.01`; `BUNCH_RANGE = (0.80, 2.00)`; `POLY_DEGREE = 7`; `BOOTSTRAP_REPS = 500`; `RANDOM_SEED = 640`; `MIN_N_FINAL = 1068`; `K_ANON_MIN = 5`; `PUBLISHABLE_COLUMNS` (whitelist).
* **Colab:** set `QM640_DATA_ROOT` to move all data folders to Google Drive.
* **Secret:** `QM640_HASH_SALT` comes from an environment variable and is never committed.

### 3.2 `src/ingest/igr_index2.py` — portal capture
* **Logic:** opens a visible Chromium browser on the IGR free-search portal. You type the search keys and the CAPTCHA. Every Index-II tab you open is detected (it contains "(2)" and "मोबदला") and saved as one row in `data/raw/index2_raw.csv`. A random pause of 6–12 s keeps the request rate polite.
* **Why human-in-the-loop:** the portal uses a CAPTCHA and offers no bulk export. Solving it by hand respects the portal's terms.
* **Columns:** `capture_ts, scraper_version, source_url, district_mr, sro_name, village_mr, doc_no, index2_text, is_synthetic`.

### 3.3 `scripts/make_search_keys.py` — sampling plan
* **Logic:** strata are district × SRO × Indian-FY quarter (144 strata), with 25 random village and survey-number searches each, for about 1,800 raw records. This makes the sample randomized and stratified rather than a convenience sample.

### 3.4 `src/ingest/synthetic_validation.py` — test data (not study data)
* **Logic:** writes Index-II-style Marathi text with Devanagari numerals, fake names and fake PANs (to test masking), out-of-scope deeds, unparseable areas and 1% duplicates. The data-generating process is known: the true anchored share is about 13.8%. A correct RQ1 estimator should recover a value close to that, and in validation it recovered 12.1% excess share and 13.4% observed.

### 3.5 `src/clean/translate_marathi.py` — language handling
| Function | What it does |
|---|---|
| `to_arabic_digits` | ०-९ → 0-9 |
| `FIELD_LABELS`, `DOC_TYPES`, `TERMS`, `LOCALITIES`, `SRO_NAMES` | Deterministic Marathi→English glossaries; extend as new terms appear |
| `translate_description` | Replaces glossary terms in free text, longest first; converts ordinals ("१२ वा मजला" → "12th floor") |
| `transliterate_place` | Uses the glossary first, then IAST/HK transliteration with schwa deletion |
| `translate_sro` | "हवेली 11" → "Haveli 11" |
| `machine_translate` | Optional Google translation (deep-translator) for leftover free text; off by default and never used for numbers |

The glossary approach is reproducible and auditable, which a thesis needs. Machine translation is only a fallback.

### 3.6 `src/clean/parse_index2.py` — structuring
* **Logic:** Index-II fields are numbered (1)…(13), so the parser keys on the numbers, not on label spellings that vary between SROs.
* `parse_amount` handles Indian grouping (1,25,00,000). `parse_area` reads m² or sq ft, carpet or built-up, and converts built-up to carpet with ÷1.2 (`area_basis = 0`). `parse_floor` maps तळमजला to 0. `parking`, `new_sale` and `municipal_corp` are keyword flags.

### 3.7 `src/clean/dpdp_masking.py` — privacy (DPDP Act 2023, DPDP Rules 2025)
| Control | Implementation |
|---|---|
| Data minimisation | Drops `executant_name`, `claimant_name`, `doc_no` and any PAN/Aadhaar/phone/e-mail column |
| Redaction | Regex replaces PAN, Aadhaar, phone, e-mail and flat numbers in free text with `[PAN]`, `[FLAT_NO]` and so on |
| Pseudonymisation | `record_id = SHA-256(salt + SRO + doc_no + year)[:16]`, which still allows de-duplication |
| Hard gate | `assert_no_personal_data` raises an error, which stops the run, if any identifier pattern survives |
| Small-cell suppression | Micro-markets with fewer than 5 records become `SUPPRESSED_SMALL_CELL` in the publishable file |
| Storage limitation | `data/raw` and `data/interim` are git-ignored; delete raw files after the 5% manual audit |

### 3.8 `src/features/build_features.py` and `osm_features.py`
* `add_location` joins locality centroids and computes haversine distances to the nearest station and to the CBD (Shivajinagar for Pune, Thane station for Thane).
* `add_derived` creates `fy`, `quarter` (FY25Q3 style), `sro_code`, `asr_rate_m2`, `value_m2`, logs, `r_ratio` and `anchored` (0.98 ≤ R < 1.02).
* `osm_features.py` replaces the approximate seed coordinates with OpenStreetMap stations and Nominatim geocodes. Run it in Colab or on a laptop.

### 3.9 `src/etl.py`
Filters run in order and each excluded row is logged in `data/processed/exclusion_log.csv`: duplicate → out-of-scope deed → outside FY 2023-24 to 2025-26 → missing core value → implausible area (outside 15–400 m²) → implausible R (outside 0.5–3.0) → not geocoded. Outputs:
* `analysis_dataset.csv`: the full analysis file.
* `analysis_dataset_publishable.csv`: whitelisted columns with small cells suppressed.
* `docs/provenance_log.csv`: one line per run.

### 3.10 `src/eda.py`
| Output | Content |
|---|---|
| `01_dataset_info.txt` | `df.info()`: shape, dtypes, non-null counts, memory |
| `02_null_values.csv`, `02b_…before_cleaning.csv` | Null count and % per column, after and before exclusions |
| `03_descriptive_stats.csv` | count, mean, **median**, std, min, Q1, Q3, max, skew, kurtosis |
| `04_category_counts.csv` | Frequencies of district, FY, doc type, SRO, micro-market, binaries |
| `05_group_means.csv` | Mean and median value per m², median ASR, median R and anchored share by district × FY |
| `06_correlation_pearson/spearman.csv` | Correlation matrices |
| `07_outliers_iqr.csv` | IQR outlier counts |
| `fig_01`–`fig_06` | Histograms, boxplots, correlation heatmap, value vs ASR scatter, R distribution, counts |

### 3.11 `src/models/rq1_bunching.py`
1. Bin R in widths of 0.01 over [0.80, 2.00).
2. Fit a degree-7 polynomial to the counts outside the window [0.98, 1.02), which covers 4 bins.
3. Apply the integration constraint: scale counts above the window by (1 + B / N_above) and iterate until B converges.
4. Compute B = Σ(observed − counterfactual) in the window, b = B ÷ the mean counterfactual count per window bin, and excess share = B ÷ N.
5. Run 500 bootstrap resamples for the 95% CI and the one-sided p-value; compute a Wilson 95% CI for the observed anchored share.
6. Robustness grid: degrees 5–9 × windows ±1, ±2 and ±5%, plus round-number dummies. Segment estimates by district and FY.

**Outputs:** `summary.json`, `rq1_bins.csv`, `rq1_robustness.csv`, `rq1_by_segment.csv`, `fig_rq1_bunching_pooled.png`, `fig_rq1_bunching_by_district.png`, `fig_rq1_bootstrap.png`.

**How to explain it to a mentor:** "b is how many times larger the spike at R = 1 is than a normal bin would be. Excess share is the fraction of all deals that moved to the circle rate instead of their market price."

### 3.11a `src/models/rq2_hedonic.py`
1. **Restricted model:** ln_value_m2 ~ ln_asr_rate_m2. **Full model:** adds 11 attributes (ln carpet area, area basis, floor, new sale, parking, distance to station, distance to CBD, Thane dummy, municipal corporation, FY 2024–25 and FY 2025–26 dummies). So *u* = 11 and *k* = 12.
2. **Partial F test** (synopsis Equation 2) for ΔR², plus an HC3-robust Wald F test of the same 11 restrictions. Cohen's f² measures the size of the increment.
3. **Coefficients** use HC3 robust errors. Errors clustered by micro-market are the conservative sensitivity check. Dummy effects are reported as % = 100 × (e^b − 1), and standardized betas rank the drivers.
4. **ASR elasticity test**, H0: β_ASR = 1. An elasticity near 1 combined with a small ΔR² would itself indicate anchoring.
5. **Diagnostics:** VIF (target < 5), Breusch–Pagan, Jarque–Bera, Durbin–Watson, condition number, residual-vs-fitted plot and Q–Q plot.

**Outputs:** `rq2_coefficients_full.csv`, `rq2_coefficients_restricted.csv`, `rq2_model_comparison.csv`, `rq2_vif.csv`, `rq2_diagnostics.csv`, `rq2_full_model_summary.txt`, `fig_rq2_r2_increase.png`, `fig_rq2_standardized_coefficients.png`, `fig_rq2_diagnostics.png`, `summary.json`.

**How to explain it to a mentor:** "The ASR rate alone explains most of the variation in registered value. The question is whether flat-level and location attributes add anything beyond it. If they add little and the ASR elasticity is about 1, registered values are simply tracking the circle rate."

### 3.12 `src/utils/results_log.py` and `plotstyle.py`
The logger writes the RQ-labelled entries in `RESULTS_LOG.md`. The style module fixes colors (Pune blue, Thane orange), uses a diverging map for correlations, and adds a data-source footer to every figure so synthetic figures can never be mistaken for findings.

### 3.13 `scripts/sample_size.py`
This script recomputes every minimum N. RQ1: CI for a proportion → 1,068. RQ2: noncentral F, f² = .02, u = 11 → 850. RQ3: paired t, d = .20, 20% held out → 995. RQ4: Hsieh with P = .12 and OR = 1.5 → 646; EPV → 1,000. Final N = max = **1,068**.

### 3.14 Execution surfaces
| Surface | Use it for |
|---|---|
| Laptop | Portal collection (CAPTCHA), small runs |
| Google Colab (`colab/…ipynb`) | Large data, stored in Drive under `QM640_DATA_ROOT` |
| GitHub Actions (`pipeline.yml`) | Rerunning one RQ stage on the committed de-identified dataset; commits outputs and the log |

## 4. Outcome register (filled as stages complete)

| Stage | Date | Data | Headline | Where |
|---|---|---|---|---|
| ETL | 11-Oct-2026 | Synthetic validation | 1,818 raw → 1,710 analysable (63 out-of-scope deeds, 25 missing core values, 20 duplicates); 3 personal fields dropped; 1,818 free-text redactions; DPDP gate passed | RESULTS_LOG §ETL |
| EDA | 11-Oct-2026 | Synthetic validation | No nulls after cleaning (26 missing areas before); r(ln value, ln ASR) = .93; median R = 1.31 | `outputs/eda/` |
| RQ1 | 11-Oct-2026 | Synthetic validation | b = 35.2, bootstrap 95% CI [25.6, 52.7], p < .002; excess share 12.1% vs known truth ≈ 13.8%, so the estimator works; robust across degrees 5–9 (b 21.9–36.6) | `outputs/rq1/` |
| RQ2 | 11-Oct-2026 | Synthetic validation | R² 0.864 → 0.891 (ΔR² = .027, f² = .25); partial F(11, 1697) = 38.2, p < .001 (HC3 Wald F = 40.5). Recovered the effects built into the synthetic data: floor +0.34%/floor, parking +4.1%, FY drift +4.8% and +9.3%. Correctly found no effect for area, area basis, station distance or municipal status. ASR elasticity 1.24. VIF max 5.18 (ln ASR rate, collinear with CBD distance). Breusch–Pagan significant, so HC3 is needed. The negative-residual cluster in the residual plot is the anchoring signature that RQ3/RQ4 target | `outputs/rq2/` |
| RQ3 | — | — | pending | — |
| RQ4 | — | — | pending | — |

Study-data rows replace the synthetic rows once real Index-II records are collected.

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| `FileNotFoundError … index2_raw.csv` | Collect data first, or add `--synthetic` |
| `DPDP gate failed — PAN pattern …` | A new identifier format has appeared: extend `PATTERNS` in `dpdp_masking.py` and rerun |
| Many `missing_core_value` exclusions | New area-unit spelling: add it to the regex in `parse_area` |
| Locality stays in Devanagari | Add it to `LOCALITIES` in `translate_marathi.py` |
| `not_geocoded` exclusions | Add the locality to `data/external/osm/locality_gazetteer.csv` or run `osm_features.py` |
| Portal layout changed | Capture still works (it reads page text); check `_extract_header` patterns |

## 6. Glossary

ASR is the Annual Statement of Rates (ready reckoner or circle rate). Index-II is the registered-document extract. SRO is the Sub-Registrar Office. *R* is consideration divided by ASR value. Anchored means 0.98 ≤ R < 1.02. Excess mass *b* is defined in Equation 1 of the synopsis. CF is the correction factor, the median of predicted ÷ registered value. DPDP is the Digital Personal Data Protection Act, 2023.
