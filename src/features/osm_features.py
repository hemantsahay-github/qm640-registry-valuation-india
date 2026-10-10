"""
osm_features.py — Build the locality gazetteer and station list from
OpenStreetMap (ODbL). Run in Colab or on a laptop (OSM is not reachable from
the cloud workspace used to develop this repo).

    pip install osmnx geopy
    python -m src.features.osm_features

Outputs replace the approximate seeds in data/external/osm/.
"""
from __future__ import annotations

import time

import pandas as pd

from src.config import EXTERNAL_DIR

BBOX = {"Pune": (18.35, 73.65, 18.80, 74.05),     # south, west, north, east
        "Thane": (19.05, 72.80, 19.45, 73.35)}


def fetch_stations() -> pd.DataFrame:
    import osmnx as ox
    rows = []
    for district, (s, w, n, e) in BBOX.items():
        tags = {"railway": ["station", "halt"], "station": ["subway", "light_rail"]}
        gdf = ox.features_from_bbox(bbox=(w, s, e, n), tags=tags)
        gdf = gdf[gdf.geometry.notna()].copy()
        pts = gdf.geometry.centroid
        rows += [{"station": nm, "district": district, "lat": p.y, "lon": p.x,
                  "mode": "metro" if gdf.loc[i].get("station") in ("subway", "light_rail") else "rail",
                  "source": "OpenStreetMap (ODbL)"}
                 for (i, nm), p in zip(gdf.get("name", pd.Series(index=gdf.index)).items(), pts)]
    return pd.DataFrame(rows).dropna(subset=["station"]).drop_duplicates("station")


def geocode_localities(names: list[tuple[str, str]]) -> pd.DataFrame:
    """names = [(micro_market, district), ...]; Nominatim, 1 request/second."""
    from geopy.geocoders import Nominatim
    geo = Nominatim(user_agent="qm640-capstone-research")
    out = []
    for mm, d in names:
        loc = geo.geocode(f"{mm}, {d} district, Maharashtra, India")
        out.append({"micro_market": mm, "district": d,
                    "lat": loc.latitude if loc else None, "lon": loc.longitude if loc else None,
                    "source": "OpenStreetMap Nominatim (ODbL)"})
        time.sleep(1.1)
    return pd.DataFrame(out)


if __name__ == "__main__":
    st = fetch_stations()
    st.to_csv(EXTERNAL_DIR / "osm" / "stations.csv", index=False)
    gaz = pd.read_csv(EXTERNAL_DIR / "osm" / "locality_gazetteer.csv")
    new = geocode_localities(list(zip(gaz["micro_market"], gaz["district"])))
    new.to_csv(EXTERNAL_DIR / "osm" / "locality_gazetteer.csv", index=False)
    print(f"stations: {len(st)}, localities: {new['lat'].notna().sum()}/{len(new)} geocoded")
