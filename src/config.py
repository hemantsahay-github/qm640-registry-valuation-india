"""
config.py — Single source of truth for paths, constants and study parameters.

Every module imports from here so that a mentor can change one value
(e.g. the anchoring window) and re-run the whole pipeline consistently.

DATA_ROOT can be redirected to Google Drive when running in Colab:
    os.environ["QM640_DATA_ROOT"] = "/content/drive/MyDrive/qm640_data"
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- paths
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("QM640_DATA_ROOT", REPO_ROOT / "data"))

RAW_DIR = DATA_ROOT / "raw"              # NEVER committed: may contain party names
INTERIM_DIR = DATA_ROOT / "interim"      # parsed + masked, English
PROCESSED_DIR = DATA_ROOT / "processed"  # analysis-ready, de-identified
EXTERNAL_DIR = DATA_ROOT / "external"    # ASR, RESIDEX, RBI, OSM

OUTPUT_DIR = REPO_ROOT / "outputs"       # RQ-wise tables and figures
DOCS_DIR = REPO_ROOT / "docs"
RESULTS_LOG = DOCS_DIR / "RESULTS_LOG.md"

for _d in (RAW_DIR, INTERIM_DIR, PROCESSED_DIR, EXTERNAL_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Dataset file names
RAW_FILE = RAW_DIR / "index2_raw.csv"
INTERIM_FILE = INTERIM_DIR / "index2_masked_en.csv"
ANALYSIS_FILE = PROCESSED_DIR / "analysis_dataset.csv"
EXCLUSION_LOG = PROCESSED_DIR / "exclusion_log.csv"

# --------------------------------------------------------------------------- study scope
DISTRICTS = ("Pune", "Thane")
FY_START, FY_END = "2023-04-01", "2026-03-31"          # FY 2023-24 to 2025-26
FISCAL_YEARS = ("2023-24", "2024-25", "2025-26")
DOC_TYPES_IN_SCOPE = ("conveyance", "agreement_for_sale")

# --------------------------------------------------------------------------- definitions
SQFT_PER_SQM = 10.7639
BUILTUP_TO_CARPET = 1 / 1.20      # carpet ~ built-up / 1.2 when only built-up recorded
ANCHOR_LO, ANCHOR_HI = 0.98, 1.02  # anchoring window on R = consideration / ASR value
R_MIN, R_MAX = 0.50, 3.00          # plausibility filter on R
AREA_MIN_M2, AREA_MAX_M2 = 15, 400  # plausibility filter on carpet area

# --------------------------------------------------------------------------- RQ1 bunching
BIN_WIDTH = 0.01
BUNCH_RANGE = (0.80, 2.00)
POLY_DEGREE = 7
BOOTSTRAP_REPS = 500

# --------------------------------------------------------------------------- statistics
ALPHA = 0.05
POWER = 0.80
RANDOM_SEED = 640                  # QM 640 — fixed for reproducibility
TEST_GROUP_SHARE = 0.20            # share of micro-markets held out (RQ3)
MIN_N_FINAL = 1068                 # N = max(RQ1..RQ4) from scripts/sample_size.py
MIN_ANCHORED_FOR_CF = 20           # correction factor reported only above this

# --------------------------------------------------------------------------- DPDP / privacy
# Salt for pseudonymous IDs. Set in a local .env or Colab secret; never commit.
HASH_SALT = os.environ.get("QM640_HASH_SALT", "LOCAL-DEV-SALT-CHANGE-ME")
K_ANON_MIN = 5                     # suppress micro-market cells with fewer records
PUBLISHABLE_COLUMNS = [            # whitelist: only these leave the machine
    "record_id", "district", "sro_code", "micro_market", "reg_date", "fy", "quarter",
    "doc_type", "consideration_inr", "asr_value_inr", "stamp_duty_inr",
    "carpet_area_m2", "area_basis", "floor_no", "new_sale", "parking",
    "lat", "lon", "dist_rail_km", "dist_cbd_km", "municipal_corp",
    "is_synthetic",
]

# --------------------------------------------------------------------------- rate limiting
SCRAPE_DELAY_SECONDS = (6, 12)     # random pause between portal requests
