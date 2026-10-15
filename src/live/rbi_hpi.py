"""
rbi_hpi.py — RBI All-India House Price Index (HPI), Pune and Thane series.

Coverage : 18 cities incl. Pune and Thane (and Mumbai); base 2022-23 = 100;
           quarterly; published in RBI DBIE -> Statistics -> Real Sector ->
           Prices & Wages (https://data.rbi.org.in/DBIE/#/dbie/home).
Access   : DBIE offers table export (Excel/CSV) but no documented public API.
           Route A (default): export the HPI table from DBIE, then
               python -m src.live.rbi_hpi --load path/to/export.xlsx
           Route B (if a data.gov.in mirror exists): put its resource ID in
               data/external/live_config.json as {"datagovin": {"rbi_hpi": "<uuid>"}}
               python -m src.live.rbi_hpi --api
Output   : data/external/rbi_dbie/rbi_hpi.csv  (city, quarter FYyyQq, index, series, source)
"""
from __future__ import annotations

import argparse

import pandas as pd

from src.config import EXTERNAL_DIR
from src.live.http import log_provenance
from src.live.index_utils import normalise_index, read_any

OUT = EXTERNAL_DIR / "rbi_dbie" / "rbi_hpi.csv"
SERIES = "RBI HPI (base 2022-23=100)"


def load_export(path) -> pd.DataFrame:
    df = normalise_index(read_any(path), SERIES, f"RBI DBIE export: {path}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    log_provenance("rbi_hpi", f"file://{path}", 200, OUT.read_bytes(), note=f"{len(df)} rows normalised")
    return df


def from_api() -> pd.DataFrame:
    from src.live.datagovin import configured_resources, fetch
    rid = configured_resources().get("rbi_hpi")
    if not rid:
        raise RuntimeError('Add {"datagovin": {"rbi_hpi": "<resource-uuid>"}} to data/external/live_config.json')
    df = normalise_index(fetch(rid), SERIES, f"data.gov.in API resource {rid}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--load", help="DBIE export file (.xlsx/.csv)")
    g.add_argument("--api", action="store_true", help="use the data.gov.in mirror")
    a = ap.parse_args()
    d = load_export(a.load) if a.load else from_api()
    print(f"{len(d)} rows ({d['city'].unique().tolist()}) -> {OUT}")
