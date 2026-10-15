"""
maharera.py — MahaRERA registered-project list for Pune and Thane districts.

Access : https://maharera.maharashtra.gov.in has a public project search
         (by district/taluka/village) but no public API or bulk download.
         Copy the search results for each study village into CSV (or save the
         results table), then:
             python -m src.live.maharera --load projects.csv
Privacy: only project-level fields are kept. Promoter names are dropped at load
         (they can be individuals) — DPDP data minimisation.
Use    : verify_new_sale() marks an Index-II record as a first sale when its
         micro-market has a registered project AND the deed text names that
         project or carries the promoter/first-sale wording; mismatches with the
         parsed new_sale flag are reported for the 5% manual audit.
Output : data/external/maharera/projects.csv
"""
from __future__ import annotations

import argparse
import difflib
import re

import pandas as pd

from src.config import EXTERNAL_DIR
from src.live.http import log_provenance

OUT = EXTERNAL_DIR / "maharera" / "projects.csv"
KEEP = ["registration_no", "project_name", "district", "taluka", "micro_market", "pincode",
        "project_status", "proposed_completion"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", str(s).lower()).strip()


def load(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if "registration_no" not in df.columns:
        cand = [c for c in df.columns if "reg" in c]
        if not cand:
            raise ValueError("No registration number column found")
        df = df.rename(columns={cand[0]: "registration_no"})
    df = df[[c for c in KEEP if c in df.columns]].drop_duplicates("registration_no")
    if not df["registration_no"].astype(str).str.match(r"^P\d{11}$").all():
        bad = (~df["registration_no"].astype(str).str.match(r"^P\d{11}$")).sum()
        print(f"warning: {bad} registration numbers do not match the MahaRERA P########### pattern")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    log_provenance("maharera", f"file://{path}", 200, OUT.read_bytes(), note=f"{len(df)} projects")
    return df


def verify_new_sale(interim: pd.DataFrame, projects: pd.DataFrame, cutoff: float = 0.85) -> pd.DataFrame:
    """interim = data/interim/index2_masked_en.csv (needs property_description_en)."""
    names = projects.groupby("micro_market")["project_name"].apply(lambda s: [_norm(x) for x in s]).to_dict()
    out = []
    for r in interim.itertuples():
        desc = _norm(getattr(r, "property_description_en", ""))
        cands = names.get(r.micro_market, [])
        best = max((difflib.SequenceMatcher(None, c, desc).find_longest_match(0, len(c), 0, len(desc)).size / max(len(c), 1)
                    for c in cands), default=0.0)
        wording = "promoter" in desc or "first sale" in desc
        out.append({"record_id": r.record_id, "project_match_score": round(best, 3),
                    "rera_new_sale": int(best >= cutoff or (wording and bool(cands))),
                    "parsed_new_sale": int(getattr(r, "new_sale", 0))})
    v = pd.DataFrame(out)
    v["mismatch"] = v["rera_new_sale"] != v["parsed_new_sale"]
    return v


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--load", required=True)
    print(f"{len(load(ap.parse_args().load))} projects -> {OUT}")
