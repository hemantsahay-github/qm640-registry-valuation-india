"""
nhb_residex.py — National Housing Bank RESIDEX (HPI @ assessment price), Pune and Thane.

Access : https://residex.nhbonline.org.in publishes city indices for download
         (Excel/PDF tables); there is no public API. Download the city table
         (or transcribe the quarterly values into CSV), then:
             python -m src.live.nhb_residex --load path/to/residex.xlsx
Output : data/external/residex/residex.csv  (city, quarter FYyyQq, index, series, source)
         — the file rq4_anchoring.py and rq4_external_validation.py look for.
"""
from __future__ import annotations

import argparse

from src.config import EXTERNAL_DIR
from src.live.http import log_provenance
from src.live.index_utils import normalise_index, read_any

OUT = EXTERNAL_DIR / "residex" / "residex.csv"
SERIES = "NHB RESIDEX HPI @ assessment price"


def load_export(path):
    df = normalise_index(read_any(path), SERIES, f"NHB RESIDEX download: {path}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    log_provenance("nhb_residex", f"file://{path}", 200, OUT.read_bytes(), note=f"{len(df)} rows normalised")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--load", required=True)
    d = load_export(ap.parse_args().load)
    print(f"{len(d)} rows -> {OUT}")
