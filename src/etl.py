"""
etl.py — Stage 1: Extract -> Translate -> Mask (DPDP) -> Clean -> Feature -> Load.

Input : data/raw/index2_raw.csv (real, from igr_index2.py)
        or data/raw/index2_raw_SYNTHETIC.csv (validation only)
Output: data/interim/index2_masked_en.csv   (masked, English, all rows)
        data/processed/analysis_dataset.csv  (analysis-ready, publishable)
        data/processed/exclusion_log.csv     (why each row was excluded)
        docs/provenance_log.csv              (one line per ETL run)
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.clean.dpdp_masking import assert_no_personal_data, mask_dataframe, publishable_view
from src.clean.parse_index2 import parse_raw
from src.config import (ANALYSIS_FILE, AREA_MAX_M2, AREA_MIN_M2, DOC_TYPES_IN_SCOPE, DOCS_DIR,
                        EXCLUSION_LOG, FY_END, FY_START, INTERIM_FILE, R_MAX, R_MIN, RAW_FILE)
from src.features.build_features import add_derived, add_location


def load_raw(use_synthetic: bool) -> pd.DataFrame:
    path = RAW_FILE.with_name("index2_raw_SYNTHETIC.csv") if use_synthetic else RAW_FILE
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run src.ingest.igr_index2 (real) or "
                                "src.ingest.synthetic_validation (validation).")
    raw = pd.read_csv(path, dtype=str, encoding="utf-8")
    raw["is_synthetic"] = raw["is_synthetic"].astype(int)
    return raw.drop(columns=[c for c in raw.columns if c.startswith("_true_")])


def apply_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sequential, logged exclusions (scope + quality)."""
    rules = [
        ("duplicate_record", lambda d: d.duplicated("record_id", keep="first")),
        ("out_of_scope_doc_type", lambda d: ~d["doc_type"].isin(DOC_TYPES_IN_SCOPE)),
        ("outside_study_period", lambda d: ~d["reg_date"].between(FY_START, FY_END)),
        ("missing_core_value", lambda d: d[["consideration_inr", "asr_value_inr",
                                            "carpet_area_m2"]].isna().any(axis=1)),
        ("implausible_area", lambda d: ~d["carpet_area_m2"].between(AREA_MIN_M2, AREA_MAX_M2)),
        ("implausible_r_ratio", lambda d: ~(d["consideration_inr"] / d["asr_value_inr"]).between(R_MIN, R_MAX)),
        ("not_geocoded", lambda d: d["lat"].isna()),
    ]
    excluded = []
    for name, rule in rules:
        mask = rule(df)
        excluded.append(df.loc[mask, ["record_id"]].assign(reason=name))
        df = df.loc[~mask]
    return df.reset_index(drop=True), pd.concat(excluded, ignore_index=True)


def live_checks(clean: pd.DataFrame, masked: pd.DataFrame) -> dict:
    """Optional cross-checks against live public sources (src/live). Each runs only
    when its normalised file exists; results go to data/processed/ for the audit."""
    from src.config import EXTERNAL_DIR, PROCESSED_DIR
    out = {}
    asr_file = EXTERNAL_DIR / "asr_rates" / "asr_rates.csv"
    if asr_file.exists():
        from src.live.igr_asr import check_against_index2
        chk = check_against_index2(clean, pd.read_csv(asr_file))
        chk.to_csv(PROCESSED_DIR / "asr_check.csv", index=False)
        out["asr_check_flagged"] = int(chk["asr_check_flag"].sum())
    rera_file = EXTERNAL_DIR / "maharera" / "projects.csv"
    if rera_file.exists():
        from src.live.maharera import verify_new_sale
        v = verify_new_sale(masked[masked["record_id"].isin(clean["record_id"])], pd.read_csv(rera_file))
        v.to_csv(PROCESSED_DIR / "maharera_new_sale_check.csv", index=False)
        out["maharera_new_sale_mismatches"] = int(v["mismatch"].sum())
    return out


def run(use_synthetic: bool = False) -> dict:
    raw = load_raw(use_synthetic)
    parsed = parse_raw(raw)                                   # Marathi -> English
    masked, audit = mask_dataframe(parsed)                    # DPDP controls
    assert_no_personal_data(masked)                           # hard gate
    masked = add_location(masked)
    INTERIM_FILE.parent.mkdir(parents=True, exist_ok=True)
    masked.to_csv(INTERIM_FILE, index=False, encoding="utf-8")

    clean, excl = apply_filters(masked)
    clean = add_derived(clean)
    excl.to_csv(EXCLUSION_LOG, index=False)
    publishable_view(clean).to_csv(ANALYSIS_FILE.with_name("analysis_dataset_publishable.csv"), index=False)
    clean.drop(columns=["property_description_en"], errors="ignore").to_csv(ANALYSIS_FILE, index=False)

    prov = DOCS_DIR / "provenance_log.csv"
    entry = pd.DataFrame([{
        "run_ts": datetime.now().isoformat(timespec="seconds"),
        "source": "SYNTHETIC validation" if use_synthetic else "IGR Maharashtra Index-II free search",
        "scraper_version": raw["scraper_version"].iloc[0], "rows_raw": len(raw),
        "rows_analysis": len(clean), "columns_dropped_dpdp": ";".join(audit["columns_dropped"]),
        "redactions": audit.get("redactions_in_property_description_en", 0)}])
    entry.to_csv(prov, mode="a", header=not prov.exists(), index=False)

    live = live_checks(clean, masked)                         # optional, only if live files exist
    return {**live, "rows_raw": len(raw), "rows_after_masking": len(masked),
            "rows_analysis": len(clean), "exclusions": excl["reason"].value_counts().to_dict(),
            "dpdp_columns_dropped": audit["columns_dropped"],
            "dpdp_free_text_redactions": audit.get("redactions_in_property_description_en", 0),
            "anchored_share": round(clean["anchored"].mean(), 4)}
