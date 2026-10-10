"""
make_search_keys.py — Randomised, stratified search plan for Index-II collection.

Strata  : district x SRO x quarter (FY 2023-24 .. 2025-26 = 12 quarters)
Within  : random village + random survey/CTS number per search, so the sample
          is not a convenience sample of the first results the portal shows.
Target  : 1,800 raw records (N = 1,068 / 0.60, rounded) -> 25 per stratum
          with 6 SROs per district (2 x 6 x 12 = 144 strata).
Output  : data/external/search_plan.csv  (tick off 'done' while collecting)

    python scripts/make_search_keys.py --sro-file data/external/sro_villages.csv
sro_villages.csv columns: district, sro_name, village  (copied from the portal dropdowns)
"""
import argparse

import numpy as np
import pandas as pd

from src.config import EXTERNAL_DIR, RANDOM_SEED

QUARTERS = [f"FY{y}Q{q}" for y in (24, 25, 26) for q in (1, 2, 3, 4)]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sro-file", required=True)
    ap.add_argument("--per-stratum", type=int, default=25)
    a = ap.parse_args()
    rng = np.random.default_rng(RANDOM_SEED)
    sv = pd.read_csv(a.sro_file)
    rows = []
    for (d, sro), g in sv.groupby(["district", "sro_name"]):
        for q in QUARTERS:
            for _ in range(a.per_stratum):
                rows.append({"district": d, "sro_name": sro, "quarter": q,
                             "village": g["village"].sample(1, random_state=int(rng.integers(1e9))).iloc[0],
                             "survey_no": int(rng.integers(1, 400)), "done": 0})
    out = pd.DataFrame(rows)
    out.to_csv(EXTERNAL_DIR / "search_plan.csv", index=False)
    print(f"{len(out)} randomised searches across {out.groupby(['sro_name', 'quarter']).ngroups} strata")
