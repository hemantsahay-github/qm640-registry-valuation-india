"""
osm.py — Live OpenStreetMap connectors (official open APIs, ODbL licence).

  stations()   Overpass API  -> rail stations/halts and metro/light-rail stations
                                inside the Pune and Thane district bounding boxes
  geocode()    Nominatim API -> locality centroids for every micro-market
  run()        writes data/external/osm/stations.csv and locality_gazetteer.csv,
               replacing the approximate seed files used in pipeline validation

Policy compliance: identifying User-Agent with contact e-mail
(QM640_CONTACT_EMAIL), max 1 request/second to Nominatim, results cached,
attribution "© OpenStreetMap contributors" in every figure/table using them.

    python -m src.live.osm
(Supersedes src/features/osm_features.py, which is kept unchanged for reference.)
"""
from __future__ import annotations

import json

import pandas as pd

from src.config import EXTERNAL_DIR
from src.live.http import LiveClient

OVERPASS = "https://overpass-api.de/api/interpreter"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
BBOX = {"Pune": (18.35, 73.65, 18.80, 74.05),      # south, west, north, east
        "Thane": (19.05, 72.80, 19.45, 73.35)}


def overpass_query(s: float, w: float, n: float, e: float) -> str:
    bb = f"({s},{w},{n},{e})"
    return f"""[out:json][timeout:90];
(
  node["railway"~"^(station|halt)$"]{bb};
  node["station"~"^(subway|light_rail)$"]{bb};
  node["public_transport"="station"]["subway"="yes"]{bb};
);
out body;"""


def stations(client: LiveClient | None = None) -> pd.DataFrame:
    client = client or LiveClient("osm")
    rows = []
    for district, bb in BBOX.items():
        data = json.loads(client.request("POST", OVERPASS, data={"data": overpass_query(*bb)}))
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name:en") or tags.get("name")
            if not name:
                continue
            mode = "metro" if tags.get("station") in ("subway", "light_rail") or tags.get("subway") == "yes" else "rail"
            rows.append({"station": name, "district": district, "lat": el["lat"], "lon": el["lon"],
                         "mode": mode, "osm_id": el["id"], "source": "OpenStreetMap (ODbL)"})
    return pd.DataFrame(rows).drop_duplicates(["station", "district"]).reset_index(drop=True)


def geocode(names: list[tuple[str, str]], client: LiveClient | None = None) -> pd.DataFrame:
    """names = [(micro_market, district), ...]"""
    client = client or LiveClient("osm")
    out = []
    for mm, d in names:
        res = client.get_json(NOMINATIM, params={"q": f"{mm}, {d}, Maharashtra, India", "format": "jsonv2",
                                                 "limit": 1, "countrycodes": "in"})
        hit = res[0] if res else {}
        out.append({"micro_market": mm, "district": d,
                    "lat": float(hit["lat"]) if hit else None, "lon": float(hit["lon"]) if hit else None,
                    "osm_display_name": hit.get("display_name"), "source": "OpenStreetMap Nominatim (ODbL)"})
    return pd.DataFrame(out)


def run() -> dict:
    osm_dir = EXTERNAL_DIR / "osm"
    st = stations()
    st.to_csv(osm_dir / "stations.csv", index=False)
    gaz_path = osm_dir / "locality_gazetteer.csv"
    gaz = pd.read_csv(gaz_path)
    new = geocode(list(zip(gaz["micro_market"], gaz["district"])))
    keep = gaz.drop(columns=[c for c in ("lat", "lon", "source") if c in gaz.columns])
    new = keep.merge(new, on=["micro_market", "district"], how="left")
    new.to_csv(gaz_path, index=False)
    return {"stations": len(st), "localities_geocoded": int(new["lat"].notna().sum()),
            "localities_total": len(new)}


if __name__ == "__main__":
    print(run())
