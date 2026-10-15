"""
igr_asr.py — Maharashtra Annual Statement of Rates (ASR / ready reckoner).

Access : IGR Maharashtra eASR (https://igrmaharashtra.gov.in) shows rates by
         district -> taluka -> village -> zone for each financial year; there is
         no public API or bulk download. Record the residential (flat) rate per
         m2 for each study village and FY into the template, then load it:
             python -m src.live.igr_asr --template          # writes the CSV template
             python -m src.live.igr_asr --load filled.csv   # validates + normalises
Use    : check_against_index2() compares the ASR value printed on each Index-II
         record with rate x carpet area (x floor-rise factor). Large gaps flag
         parsing errors or non-standard zones before RQ1 is run.
Output : data/external/asr_rates/asr_rates.csv
"""
from __future__ import annotations

import argparse

import pandas as pd

from src.config import EXTERNAL_DIR, FISCAL_YEARS
from src.live.http import log_provenance

OUT = EXTERNAL_DIR / "asr_rates" / "asr_rates.csv"
COLUMNS = ["district", "taluka", "micro_market", "village_mr", "zone_no", "fy",
           "residential_rate_inr_m2", "source_page", "retrieved_on"]


def make_template() -> pd.DataFrame:
    gaz = pd.read_csv(EXTERNAL_DIR / "osm" / "locality_gazetteer.csv")
    rows = [{"district": r.district, "taluka": "", "micro_market": r.micro_market,
             "village_mr": getattr(r, "micro_market_mr", ""), "zone_no": "", "fy": fy,
             "residential_rate_inr_m2": "", "source_page": "", "retrieved_on": ""}
            for r in gaz.itertuples() for fy in FISCAL_YEARS]
    t = pd.DataFrame(rows, columns=COLUMNS)
    path = OUT.with_name("asr_rates_TEMPLATE.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(path, index=False)
    return t


def load(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in ("district", "micro_market", "fy", "residential_rate_inr_m2") if c not in df.columns]
    if missing:
        raise ValueError(f"ASR file missing columns: {missing}")
    df["residential_rate_inr_m2"] = pd.to_numeric(df["residential_rate_inr_m2"], errors="coerce")
    bad = df["residential_rate_inr_m2"].notna() & ~df["residential_rate_inr_m2"].between(5_000, 1_000_000)
    if bad.any():
        raise ValueError(f"{int(bad.sum())} ASR rates outside ₹5,000–10,00,000 per m²; check units (m² not ft²)")
    df = df.dropna(subset=["residential_rate_inr_m2"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    log_provenance("igr_asr", f"file://{path}", 200, OUT.read_bytes(), note=f"{len(df)} rates")
    return df


def check_against_index2(analysis: pd.DataFrame, asr: pd.DataFrame, floor_rise: float = 1.05,
                         tolerance: float = 0.15) -> pd.DataFrame:
    """Implied rate = asr_value_inr / carpet_area_m2 (adjusted for floor rise above
    the 4th floor) vs. published rate. Returns per-record ratio and a flag."""
    m = analysis.merge(asr[["micro_market", "fy", "residential_rate_inr_m2"]], on=["micro_market", "fy"], how="left")
    adj = m["floor_no"].fillna(0).gt(4).map({True: floor_rise, False: 1.0})
    m["asr_check_ratio"] = (m["asr_value_inr"] / m["carpet_area_m2"]) / (m["residential_rate_inr_m2"] * adj)
    m["asr_check_flag"] = (m["asr_check_ratio"] - 1).abs() > tolerance
    return m[["record_id", "micro_market", "fy", "asr_check_ratio", "asr_check_flag"]]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--template", action="store_true")
    g.add_argument("--load")
    a = ap.parse_args()
    if a.template:
        print(f"template rows: {len(make_template())} -> {OUT.with_name('asr_rates_TEMPLATE.csv')}")
    else:
        print(f"{len(load(a.load))} ASR rates -> {OUT}")
