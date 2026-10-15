# Code Manual (Ready Reckoner)

**Project:** Correcting for Circle-Rate Anchoring in Indian Residential Property Valuation: A Registry-Based Machine Learning Study
**Author / IP owner:** Hemant Kumar Sahay · QM 640 Data Analytics Capstone, Walsh College
**Manual version:** 2.1 (16 October 2026). This version adds the live-data connectors (`src/live/`) and the RQ4 external validation against RBI HPI and NHB RESIDEX. The synthetic-data logic is unchanged and is also frozen on GitHub branch `archive/v1.0-synthetic-validation`.

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
| L0 Live status | `python -m src.live.fetch_all --check` | `src/live/sources.py` | console table | Which live sources are loaded, which credentials are missing |
| L1 Live pull | `python -m src.live.fetch_all --run osm`, plus each `src.live.<source> --load <file>` | public APIs / official exports | `data/external/<source>/` | Real locations, ASR rates, RERA projects, market indices |
| 8 RQ4 external | `--stage rq4ext` | RQ4 factors + RBI HPI / RESIDEX | `outputs/rq4/external/` | Does the correction factor move with the market? |

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
| `src/live/` | **Live-data connectors** for the sources in synopsis Table 2 (APIs, export loaders, catalogue, status check) | Yes |
| `.env.example` | Names of the secrets and settings the live connectors read (copy to `.env`, never commit) | Yes |
| `data/external/cache/` | Raw HTTP responses from live APIs | **No** (git-ignored) |
| `docs/live_provenance_log.csv` | One line per live request or file load: time, source, URL with keys removed, status, SHA-256 | Yes |
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

### 3.11b `src/models/rq3_gbm_vs_ols.py`
1. **Hold-out:** about 20% of *micro-markets* are held out with `GroupShuffleSplit` (seed 640), so every test locality is unseen in training. The test set must have at least 199 cases (synopsis RQ3 sample size).
2. **Models:** OLS uses the RQ2 full specification. XGBoost uses the same 12 predictors plus latitude and longitude, and its parameters are tuned by a 30-draw randomized search with 5-fold `GroupKFold` on the training markets (MAE objective).
3. **Metrics:** RMSE, MAE and R² on the log scale, and RMSE, MAE and MAPE in ₹ per m² (synopsis Equations 3–4).
4. **Tests on d = |e_OLS| − |e_XGB|** (Equation 5):
   - paired *t* (one-sided)
   - Wilcoxon signed-rank
   - Diebold–Mariano with the HLN correction. For a cross-section with h = 1 it equals the paired *t*, which is expected.
   - cluster bootstrap over test micro-markets, the conservative check
5. **Robustness:** 5-fold grouped CV over all localities, for both models.
6. **Bias audit:** MAE by district, price tercile, new-sale status and anchoring status.
7. **SHAP:** TreeExplainer on the test set, with a beeswarm plot and a mean-|SHAP| importance chart.
8. **Saved model:** `xgb_model.json` and `best_params.json`, which RQ4 reuses.

**Power check (unit test):** `test_rq3_paired_tests_detect_a_real_advantage` builds data with an interaction OLS cannot fit. It confirms that XGBoost wins and that the one-sided tests reject H0, so a "no advantage" result is not caused by the code.

**How to explain it to a mentor:** "Both models predict prices in neighbourhoods they have never seen. If boosting's errors are smaller by a margin the paired tests call significant, the extra complexity is justified. If not, the simpler hedonic model is the better tool, which is also a useful finding."

### 3.11c `src/models/rq4_anchoring.py`
**Part A: what predicts anchoring** (anchored = 1 if 0.98 ≤ R < 1.02)
1. **Logistic regression** on the full sample, using the 12 RQ2 predictors. Outputs:
   - odds ratios with 95% CIs
   - likelihood-ratio test against the null model
   - McFadden pseudo-R²
   - events-per-variable check (target ≥ 10)
   - Box–Tidwell test, which adds x·ln x terms for the positive continuous predictors to check linearity in the logit
2. **Out-of-sample check** on the same held-out micro-markets as RQ3:
   - logistic regression against a tuned XGBoost classifier (grouped CV, AUC objective)
   - AUC, Brier score, precision, recall, F1 and the confusion matrix
   - the classification threshold is set on the training data (Youden J), never on the test data
   - a bootstrap CI for the AUC difference between the two models

**Part B: correction factor**
3. **Value model:** the RQ3 winner, read automatically from `rq3/summary.json` (OLS unless XGBoost won significantly). It is retrained on **non-anchored** deals only and then predicts the value of anchored deals.
4. **Factor:** CF_i = predicted ÷ registered value. CF_m is the median over the anchored deals in each micro-market, with a bootstrap 95% CI. It is marked `reportable` only when there are at least 20 anchored deals.
5. **Thin micro-markets:** an empirical-Bayes shrinkage factor (`cf_eb`) pools each micro-market toward its district mean. SRO-level factors (`rq4_cf_by_sro.csv`) give a coarser unit that reaches the threshold sooner.
6. **Outputs:**
   - `correction_factors.csv`, in the schema Estima uploads (see the Emergent.ai script, Phase 1)
   - CF by district and FY
   - a RESIDEX direction check when `data/external/residex/residex.csv` exists
   - figures: ROC curve, odds-ratio forest plot, correction factors, calibration

**Synthetic truth check:** `python -m scripts.validate_synthetic_truth` compares the estimated CF with the true CF that the generator stores. It works only on synthetic data.

**How to explain it to a mentor:** "The logit tells us *who* registers at the circle rate. The correction factor tells us *by how much* those registrations understate value. A CF of 1.30 means the registered figure is about 30% below what comparable non-anchored deals imply. Because even non-anchored deals can be understated, this is a lower bound."

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

### 3.15 Live-data connectors (`src/live/`) — real data for the study run
**Why this package exists.** The study must run on real public data, not the synthetic validation set. Each source in synopsis Table 2 gets its own clearly named module. The access method follows what the source actually offers. Only data.gov.in and OpenStreetMap have official public APIs. RBI DBIE, NHB RESIDEX, IGR eASR and MahaRERA publish data on their websites or as downloads with no public API. Index-II requires a CAPTCHA for every search.

| Module | Source | Access route | Credential | Normalised output | Feeds |
|---|---|---|---|---|---|
| `datagovin.py` | Open Government Data Platform (data.gov.in) | **Official REST API**: `https://api.data.gov.in/resource/{id}?api-key=…&format=json&offset=…&limit=…&filters[field]=value`; paginated | `DATAGOVIN_API_KEY` | `data/external/datagovin/<name>.csv` | Any OGD dataset; RBI HPI mirror |
| `osm.py` | OpenStreetMap | **Official open APIs**: Overpass (stations), Nominatim (locality geocodes); 1 request/s, identifying User-Agent, ODbL attribution | `QM640_CONTACT_EMAIL` | `osm/stations.csv`, `osm/locality_gazetteer.csv` | `dist_rail_km`, `dist_cbd_km`, lat/lon |
| `rbi_hpi.py` | RBI DBIE House Price Index, which covers 18 cities including **Pune and Thane** (base 2022-23 = 100) | DBIE table export (`--load`); optional data.gov.in mirror (`--api`) | key only for `--api` | `rbi_dbie/rbi_hpi.csv` | RQ4 external validation |
| `nhb_residex.py` | NHB RESIDEX, HPI at assessment price | Downloaded city table (`--load`) | — | `residex/residex.csv` | RQ4 external validation |
| `igr_asr.py` | IGR eASR (ready reckoner) | Rates recorded into a generated template (`--template`, then `--load`) | — | `asr_rates/asr_rates.csv` | ETL check that each Index-II ASR value matches rate × area |
| `maharera.py` | MahaRERA project registry | Project search results saved as CSV (`--load`); promoter names dropped (DPDP) | — | `maharera/projects.csv` | ETL check of the `new_sale` flag |
| `src/ingest/igr_index2.py` (unchanged) | IGR Index-II | Assisted capture; you type the CAPTCHA | — | `data/raw/index2_raw.csv` | ETL → RQ1–RQ4 (core data) |

**Shared plumbing**
- `http.py` (`LiveClient`):
  - retries with back-off on 429 and 5xx responses
  - a minimum interval between requests to the same host
  - a User-Agent that includes your contact e-mail
  - an on-disk response cache
  - `log_provenance()`, which strips API keys from URLs before anything is logged
- `index_utils.py` reads both wide and long index tables and normalises period labels such as "Q1:2025-26", "2025-26 Q1", "Q1 FY26" and dates to `FYyyQq`.
- `sources.py` is the catalogue of all sources, and `fetch_all.py --check` prints its status table.

**How live data reaches the RQs**
1. `etl.py` → `live_checks()`. If `asr_rates.csv` exists, the ETL writes `data/processed/asr_check.csv`. If `projects.csv` exists, it writes `data/processed/maharera_new_sale_check.csv`. The counts of flagged records go into the ETL results-log entry. Neither check changes any analysis variable; both feed the 5% manual audit.
2. Running `osm.py` replaces the approximate seed coordinates, so the distances in RQ2–RQ4 use real station locations.
3. `rq4_anchoring.py` now also writes `rq4_anchored_cf.csv`, the record-level factors. This is an extra output only; the RQ4 logic is unchanged.
4. `src/models/rq4_external_validation.py` (stage `rq4ext`):
   - for each district × FY, it compares the change in the median correction factor with the *gap* between index growth and ASR growth
   - it reports the direction-agreement share and Spearman ρ, and draws a figure
   - it skips cleanly when no index file is loaded
   - with 2 districts × 3 FYs it is a face-validity check, not a significance test

**Live-data run order**
1. Set up `.env` from `.env.example` with a salt, contact e-mail and data.gov.in key.
2. Run `python -m src.live.fetch_all --check`.
3. Run `python -m src.live.fetch_all --run osm`.
4. Run `python -m src.live.igr_asr --template`, fill the template from eASR, then run `--load`.
5. Load the MahaRERA project list with `src.live.maharera --load`.
6. Load the RBI HPI export (`src.live.rbi_hpi --load`) and the RESIDEX download (`src.live.nhb_residex --load`).
7. Collect Index-II with `src.ingest.igr_index2`.
8. Run the pipeline stages `etl` → `eda` → `rq1` … `rq4` → `rq4ext`, all **without** `--synthetic`.

**Testing.** `tests/test_live.py` has 15 tests. They mock every network call with responses in each API's documented format, so they run offline and on GitHub Actions. They cover:
- pagination and filters for data.gov.in
- that the API key never appears in the provenance log
- parsing Overpass responses
- quarter-label parsing and normalising wide and long index tables
- range validation of ASR rates and the Index-II cross-check
- MahaRERA matching
- the direction logic of the RQ4 external validation

**Limitation.** The cloud workspace used to build this package cannot reach the government sites. The connectors are tested against the documented formats, not yet against live responses. The first live run on your laptop or in Colab is the integration test. Check `docs/live_provenance_log.csv` after that run.

**Preserved logic.** `src/ingest/synthetic_validation.py`, `scripts/validate_synthetic_truth.py`, the `--synthetic` flag and `src/features/osm_features.py` are kept unchanged for reference. Branch `archive/v1.0-synthetic-validation` is a frozen snapshot of the full synthetic-validated pipeline (commit 45c4b01).

## 4. Outcome register (filled as stages complete)

| Stage | Date | Data | Headline | Where |
|---|---|---|---|---|
| ETL | 11-Oct-2026 | Synthetic validation | 1,818 raw → 1,710 analysable (63 out-of-scope deeds, 25 missing core values, 20 duplicates); 3 personal fields dropped; 1,818 free-text redactions; DPDP gate passed | RESULTS_LOG §ETL |
| EDA | 11-Oct-2026 | Synthetic validation | No nulls after cleaning (26 missing areas before); r(ln value, ln ASR) = .93; median R = 1.31 | `outputs/eda/` |
| RQ1 | 11-Oct-2026 | Synthetic validation | b = 35.2, bootstrap 95% CI [25.6, 52.7], p < .002; excess share 12.1% vs known truth ≈ 13.8%, so the estimator works; robust across degrees 5–9 (b 21.9–36.6) | `outputs/rq1/` |
| RQ2 | 11-Oct-2026 | Synthetic validation | R² 0.864 → 0.891 (ΔR² = .027, f² = .25); partial F(11, 1697) = 38.2, p < .001 (HC3 Wald F = 40.5). Recovered the effects built into the synthetic data: floor +0.34%/floor, parking +4.1%, FY drift +4.8% and +9.3%. Correctly found no effect for area, area basis, station distance or municipal status. ASR elasticity 1.24. VIF max 5.18 (ln ASR rate, collinear with CBD distance). Breusch–Pagan significant, so HC3 is needed. The negative-residual cluster in the residual plot is the anchoring signature that RQ3/RQ4 target | `outputs/rq2/` |
| RQ3 | 12-Oct-2026 | Synthetic validation | 8 held-out micro-markets, n_test = 404 (≥ 199). OLS beat XGBoost: MAE_log 0.102 vs 0.109, MAPE 10.4% vs 11.3%. Mean d = −0.0069, paired t(403) = −2.66, one-sided p = .996, so H0 is not rejected. OLS won all 5 grouped-CV folds. This is the correct outcome, because the synthetic data are log-linear with no interactions. A unit-test power check confirms the tests do detect a real XGBoost advantage. Bias audit: anchored deals have about 2× the error (0.21 vs 0.09), which motivates RQ4. Top SHAP features: ASR rate, new sale, FY 2025–26, floor, carpet area | `outputs/rq3/` |
| RQ4 | 12-Oct-2026 | Synthetic validation | 229 anchored (EPV = 19.1). LR χ²(12) = 59.9, p < .001; McFadden R² = .045. Significant odds ratios: new sale 0.41 (the generator's true value is 0.41), FY 2025–26 0.64, floor 0.98. Held-out AUC: logit .59, XGBoost .57 (difference not significant). Low predictability is expected because synthetic anchoring is mostly random. Pooled CF = 1.31 [1.28, 1.36] (Pune 1.35, Thane 1.29). **Truth check:** true CF = 1.38, so the estimate recovers 95%, and the shortfall is the built-in under-statement of non-anchored deals (lower bound confirmed). 0 of 35 micro-markets reach 20 anchored (median 6); 5 of 12 SROs do, so EB shrinkage and SRO-level factors are provided | `outputs/rq4/` |

| Live connectors | 16-Oct-2026 | Code + offline tests | 7 live modules and the `rq4ext` stage added. 27 of 27 unit tests pass (15 new). A synthetic regression rerun reproduced every earlier result exactly (1,710 rows; b = 35.168; ΔR² = .027; CF = 1.3095). `rq4ext` skips until an index file is loaded | `src/live/`, `tests/test_live.py` |

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
| `DATAGOVIN_API_KEY is not set` | Add the key to `.env` (data.gov.in → My Account) or a Colab secret |
| `Cannot identify city/period/index columns` (RBI/RESIDEX load) | Rename the export's columns to City / Quarter / Index, or keep the wide layout with one column per city |
| HTTP 429 from Overpass or Nominatim | Wait and rerun. Responses are cached, so finished requests are not repeated |
| `rq4ext` status SKIPPED | Run `--stage rq4` first, then load at least one index file |
| `fetch_all --check` shows osm "missing" although files exist | They are the approximate seed files. Run `python -m src.live.fetch_all --run osm` |

## 6. Glossary

ASR is the Annual Statement of Rates (ready reckoner or circle rate). Index-II is the registered-document extract. SRO is the Sub-Registrar Office. *R* is consideration divided by ASR value. Anchored means 0.98 ≤ R < 1.02. Excess mass *b* is defined in Equation 1 of the synopsis. CF is the correction factor, the median of predicted ÷ registered value. DPDP is the Digital Personal Data Protection Act, 2023.
