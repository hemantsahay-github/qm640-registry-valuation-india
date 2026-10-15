"""
fetch_all.py — One command to see and refresh every live source.

    python -m src.live.fetch_all --check        # status table: access route, credentials, files present
    python -m src.live.fetch_all --run osm      # live API pull (OpenStreetMap stations + geocodes)
    python -m src.live.fetch_all --run rbi_api  # data.gov.in mirror of RBI HPI (needs API key + resource ID)

File-based sources are loaded with their own module (--load <file>):
    src.live.rbi_hpi, src.live.nhb_residex, src.live.igr_asr, src.live.maharera
Index-II records are captured with src.ingest.igr_index2 (CAPTCHA, on your laptop).
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.live.sources import SOURCES


def status() -> pd.DataFrame:
    rows = []
    for key, s in SOURCES.items():
        out = Path(s["output"])
        present = out.exists() and (out.is_file() or any(out.glob("*.csv")))
        if present and key == "osm":                    # seed files are not live data
            st = out / "stations.csv"
            if st.exists() and pd.read_csv(st)["source"].astype(str).str.contains("approximate seed").any():
                present = False
        cred = s["credential"]
        env = cred.split()[0] if cred else None
        rows.append({
            "source": key, "access": s["access"].split(" (")[0],
            "credential": "n/a" if not cred else ("set" if os.environ.get(env) else f"MISSING {env}"),
            "data_file": "present" if present else "missing",
            "last_modified": datetime.fromtimestamp(out.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                             if present and out.is_file() else "",
            "next_step": "ok" if present else s["next_step"],
        })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--run", choices=["osm", "rbi_api"])
    a = ap.parse_args()
    if a.run == "osm":
        from src.live.osm import run
        print(run())
    elif a.run == "rbi_api":
        from src.live.rbi_hpi import from_api
        print(f"{len(from_api())} RBI HPI rows")
    if a.check or not a.run:
        with pd.option_context("display.max_colwidth", 60, "display.width", 200):
            print(status().to_string(index=False))


if __name__ == "__main__":
    main()
