"""
validate_synthetic_truth.py — SYNTHETIC DATA ONLY.

The synthetic generator stores each record's true market value. This script
compares the RQ4 correction factor estimated by the pipeline with the true
factor (true market value / declared value) for anchored transactions, which
shows how much the method recovers and in which direction it errs.
Cannot be run on real data (true prices are unobserved by design).

    python -m scripts.validate_synthetic_truth
"""
import json

import numpy as np
import pandas as pd

from src.clean.dpdp_masking import pseudonymise
from src.clean.parse_index2 import parse_raw
from src.config import ANALYSIS_FILE, OUTPUT_DIR, RAW_FILE

raw = pd.read_csv(RAW_FILE.with_name("index2_raw_SYNTHETIC.csv"), dtype=str)
parsed = parse_raw(raw.assign(is_synthetic=1))
raw["record_id"] = [pseudonymise(s, d, y) for s, d, y in
                    zip(parsed["sro_name"], parsed["doc_no"], parsed["reg_date"].astype(str).str[:4])]
truth = raw.drop_duplicates("record_id").set_index("record_id")["_true_market_value"].astype(float)

df = pd.read_csv(ANALYSIS_FILE)
a = df[df["anchored"] == 1].copy()
a["true_cf"] = a["record_id"].map(truth) / a["consideration_inr"]
est = json.loads((OUTPUT_DIR / "rq4" / "summary.json").read_text())
out = {
    "anchored_matched": int(a["true_cf"].notna().sum()),
    "true_cf_median_pooled": round(float(a["true_cf"].median()), 4),
    "estimated_cf_median_pooled": est["cf_pooled_median"],
    "estimate_over_truth": round(est["cf_pooled_median"] / float(a["true_cf"].median()), 4),
    "true_cf_by_district": a.groupby("district")["true_cf"].median().round(4).to_dict(),
    "estimated_cf_by_district": est["cf_by_district"],
    "note": ("Estimate < truth is expected: the value model is trained on non-anchored deals, "
             "which the generator also understates by 0-12% (mean ~6%). The correction factor "
             "is therefore a LOWER BOUND, as stated in the synopsis limitations."),
}
(OUTPUT_DIR / "rq4" / "synthetic_truth_check.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
