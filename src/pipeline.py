"""
pipeline.py — Single entry point. Runs stages in order, one RQ at a time.

    python -m src.pipeline --stage etl   [--synthetic]
    python -m src.pipeline --stage eda   [--synthetic]
    python -m src.pipeline --stage rq1   [--synthetic]
    python -m src.pipeline --stage rq2 | rq3 | rq4
    python -m src.pipeline --stage all   [--synthetic]

--synthetic uses data/raw/index2_raw_SYNTHETIC.csv (pipeline validation only).
Every stage appends an RQ-labelled entry to docs/RESULTS_LOG.md.
"""
from __future__ import annotations

import argparse
import importlib

import pandas as pd

from src.config import ANALYSIS_FILE
from src.utils.results_log import data_label, log_stage

INTERPRET = {
    "ETL": "Raw Index-II text was parsed from Marathi, personal data removed under DPDP controls, "
           "scope and quality filters applied, and features derived. Compare rows_analysis with N = 1,068.",
    "EDA": "Profiles the analysis dataset: completeness, distributions, central tendency, correlations "
           "and outliers. The R-ratio histogram is the visual precursor to RQ1.",
    "RQ1": "b > 0 with a bootstrap CI excluding 0 means more transactions sit at the ASR threshold "
           "than a smooth distribution predicts — evidence of circle-rate anchoring. Excess share is the "
           "fraction of all transactions that moved to the threshold.",
    "RQ2": "A significant partial F test means property and locational attributes explain registered "
           "value beyond the ASR rate. A small dR^2 together with an ASR elasticity close to 1 would "
           "itself point to anchoring (registered values tracking the circle rate). Read significance "
           "with HC3 errors; the clustered errors are the conservative check.",
    "RQ3": "Models are compared only on micro-markets never seen in training. A positive mean d with "
           "p < .05 (paired t, Wilcoxon, Diebold-Mariano) means XGBoost predicts registered value more "
           "accurately than OLS. The cluster bootstrap is the conservative check because errors within "
           "a locality are correlated. SHAP shows which features drive the XGBoost predictions.",
}
STAGES = {"etl": "src.etl", "eda": "src.eda", "rq1": "src.models.rq1_bunching",
          "rq2": "src.models.rq2_hedonic", "rq3": "src.models.rq3_gbm_vs_ols",
          "rq4": "src.models.rq4_anchoring"}


def run_stage(stage: str, synthetic: bool) -> dict:
    mod = importlib.import_module(STAGES[stage])
    if stage == "etl":
        summary, files = mod.run(use_synthetic=synthetic), [ANALYSIS_FILE]
    else:
        if ANALYSIS_FILE.exists():
            synthetic = bool(pd.read_csv(ANALYSIS_FILE, usecols=["is_synthetic"])["is_synthetic"].max())
        summary, files = mod.run(data_label(synthetic))
    log_stage(stage.upper(), synthetic, summary, files, INTERPRET.get(stage.upper(), ""))
    print(f"\n=== {stage.upper()} complete — {data_label(synthetic)} ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=list(STAGES) + ["all"])
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    for s in (list(STAGES) if a.stage == "all" else [a.stage]):
        run_stage(s, a.synthetic)


if __name__ == "__main__":
    main()
