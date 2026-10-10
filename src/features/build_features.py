"""
build_features.py — Derive analysis variables (see docs/data_dictionary.csv).

Locational features use a gazetteer of locality centroids and a list of
rail/metro stations. In the study these come from OpenStreetMap via
src/features/osm_features.py (run in Colab); the bundled CSVs in
data/external/osm/ are approximate seeds used for pipeline validation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import ANCHOR_HI, ANCHOR_LO, EXTERNAL_DIR

CBD = {"Pune": (18.5308, 73.8475),    # Shivajinagar
       "Thane": (19.1860, 72.9759)}   # Thane station area


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dlmb = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def fiscal_year(d: pd.Timestamp) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[-2:]}"


def add_location(df: pd.DataFrame) -> pd.DataFrame:
    gaz = pd.read_csv(EXTERNAL_DIR / "osm" / "locality_gazetteer.csv")
    st = pd.read_csv(EXTERNAL_DIR / "osm" / "stations.csv")
    df = df.merge(gaz[["micro_market", "lat", "lon"]], on="micro_market", how="left")
    s_lat, s_lon = st["lat"].to_numpy(), st["lon"].to_numpy()
    df["dist_rail_km"] = [np.nan if pd.isna(a) else float(haversine_km(a, b, s_lat, s_lon).min())
                          for a, b in zip(df["lat"], df["lon"])]
    df["dist_cbd_km"] = [np.nan if pd.isna(a) else float(haversine_km(a, b, *CBD[d]))
                         for a, b, d in zip(df["lat"], df["lon"], df["district"])]
    return df


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["fy"] = df["reg_date"].map(fiscal_year)
    # Indian FY quarter label, e.g. 2024-12-20 -> "FY25Q3" (FY 2024-25, Oct-Dec quarter)
    df["quarter"] = "FY" + df["reg_date"].dt.to_period("Q-MAR").astype(str).str[2:]
    sros = sorted(df["sro_name"].unique())
    df["sro_code"] = df["sro_name"].map({s: f"SRO{i:02d}" for i, s in enumerate(sros)})
    df["asr_rate_m2"] = df["asr_value_inr"] / df["carpet_area_m2"]
    df["value_m2"] = df["consideration_inr"] / df["carpet_area_m2"]
    df["ln_value_m2"] = np.log(df["value_m2"])
    df["ln_asr_rate_m2"] = np.log(df["asr_rate_m2"])
    df["ln_carpet_area"] = np.log(df["carpet_area_m2"])
    df["r_ratio"] = df["consideration_inr"] / df["asr_value_inr"]
    df["anchored"] = df["r_ratio"].between(ANCHOR_LO, ANCHOR_HI).astype(int)
    return df
