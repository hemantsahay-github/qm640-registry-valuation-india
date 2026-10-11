# Correcting for Circle-Rate Anchoring in Indian Residential Property Valuation

**A Registry-Based Machine Learning Study** · QM 640 Data Analytics Capstone, Walsh College
Author: **Hemant Kumar Sahay** · © 2026, all rights reserved (see `LICENSE`). Private repository: access is granted to QM 640 evaluators only.

## What this repository does

It measures how far registered apartment values in Pune and Thane districts (Maharashtra) cluster at the government's Annual Statement of Rates (ASR, or "circle rate"). It then builds a micro-market **correction factor** that converts a registered value into an evidence-based fair value. The work answers four research questions:

| RQ | Question | Method | Module | Status |
|----|----------|--------|--------|--------|
| RQ1 | How much do registered values bunch at the ASR value? | Bunching estimator, bootstrap CI | `src/models/rq1_bunching.py` | ✅ code validated |
| RQ2 | Which attributes explain value beyond the ASR rate? | Hedonic OLS, partial F test, HC3 | `src/models/rq2_hedonic.py` | ✅ code validated |
| RQ3 | Does XGBoost beat OLS on unseen micro-markets? | Grouped CV, paired t / Wilcoxon / DM | `src/models/rq3_gbm_vs_ols.py` | ⏳ next |
| RQ4 | What predicts anchoring, and what is the correction factor? | Logistic regression + XGB classifier | `src/models/rq4_anchoring.py` | ⏳ |

## Quick start

```bash
conda env create -f environment.yml && conda activate qm640      # or: pip install -r requirements.txt
export QM640_HASH_SALT="<your private salt>"                      # never commit
python scripts/sample_size.py                                     # reproduces Table 4 of the synopsis
python -m pytest -q tests                                         # parser, DPDP masking, estimator tests

# A. Pipeline validation (synthetic, no portal access needed)
python -m src.ingest.synthetic_validation
python -m src.pipeline --stage etl --synthetic
python -m src.pipeline --stage eda
python -m src.pipeline --stage rq1

# B. Study run (real data, on your laptop: the portal needs a CAPTCHA)
python scripts/make_search_keys.py --sro-file data/external/sro_villages.csv
python -m src.ingest.igr_index2 --district Pune --max 200          # repeat per stratum
python -m src.pipeline --stage etl                                 # then eda, rq1 ... rq4
```

Large data or no laptop GPU: open `colab/QM640_pipeline_colab.ipynb`. It stores data in Google Drive and pulls code from this private repo. To run one stage from GitHub, open **Actions → RQ pipeline → Run workflow** and pick a stage.

## Data and DPDP compliance

| Source | Content | Access |
|---|---|---|
| IGR Maharashtra Index-II free search | consideration, ASR value, stamp duty, area, floor, parking, date | https://freesearchigrservice.maharashtra.gov.in (free; CAPTCHA) |
| IGR ASR schedule | ASR rates by locality and year | https://igrmaharashtra.gov.in |
| MahaRERA | promoter / first-sale status | https://maharera.maharashtra.gov.in |
| NHB RESIDEX | quarterly price index | https://residex.nhbonline.org.in |
| RBI DBIE | house price index, lending rates | https://data.rbi.org.in |
| OpenStreetMap | stations, locality coordinates (ODbL) | https://www.openstreetmap.org |

Index-II pages name the parties. `src/clean/dpdp_masking.py` drops names, document numbers, PAN, Aadhaar, phone and e-mail. It also redacts flat numbers, replaces IDs with a salted SHA-256 pseudonym, and suppresses micro-markets with fewer than 5 records. A hard gate (`assert_no_personal_data`) stops the pipeline if any identifier survives. `data/raw/` and `data/interim/` are git-ignored.

> **Synthetic data warning.** `index2_raw_SYNTHETIC.csv` exists only to test the code. Every output made from it is stamped *PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)*. Walsh QM 640 does not accept fictitious data as study evidence.

## Layout

```
├── src/
│   ├── config.py               all paths, constants and study parameters
│   ├── pipeline.py             CLI: --stage etl|eda|rq1|rq2|rq3|rq4|all
│   ├── etl.py                  extract → translate → mask → clean → features → load
│   ├── eda.py                  exploratory data analysis (tables + figures)
│   ├── ingest/                 igr_index2.py (portal capture), synthetic_validation.py
│   ├── clean/                  translate_marathi.py, parse_index2.py, dpdp_masking.py
│   ├── features/               build_features.py, osm_features.py
│   ├── models/                 rq1_bunching.py, rq2…rq4 (added stage by stage)
│   └── utils/                  results_log.py, plotstyle.py
├── scripts/                    sample_size.py, make_search_keys.py
├── data/{raw,interim,processed,external}
├── outputs/{eda,rq1,rq2,rq3,rq4}   RQ-wise tables, figures, summary.json
├── docs/                       CODE_MANUAL.md, RESULTS_LOG.md, data_dictionary.csv, provenance_log.csv
├── colab/                      QM640_pipeline_colab.ipynb
├── tests/                      pytest unit tests
└── .github/workflows/          pipeline.yml (manual, one stage per run)
```

See **`docs/CODE_MANUAL.md`** for a file-by-file reference, **`docs/RESULTS_LOG.md`** for every run's outcome, and **`docs/EMERGENT_ESTIMA_INTEGRATION_SCRIPT.md`** for the phased Emergent.ai build script that brings the results into Estima.
