"""
datagovin.py — Client for the Open Government Data Platform India REST API.

Endpoint : https://api.data.gov.in/resource/{resource_id}
Params   : api-key (required), format=json, offset, limit, filters[field]=value
Key      : register at data.gov.in -> My Account -> API key; set DATAGOVIN_API_KEY.
Datasets : resource IDs are listed per dataset on data.gov.in ("API" tab). Put the
           IDs you use in data/external/live_config.json, e.g.
           {"datagovin": {"rbi_hpi": "<resource-uuid>", "...": "..."}}

    python -m src.live.datagovin --resource <uuid> --filter city=Pune --out rbi_hpi_pune
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from src.config import DATAGOVIN_API_KEY, EXTERNAL_DIR, LIVE_CONFIG
from src.live.http import LiveClient

BASE = "https://api.data.gov.in/resource/{rid}"


def configured_resources() -> dict:
    if LIVE_CONFIG.exists():
        return json.loads(LIVE_CONFIG.read_text()).get("datagovin", {})
    return {}


def fetch(resource_id: str, filters: dict | None = None, page_size: int = 500,
          max_records: int | None = None, api_key: str | None = None,
          client: LiveClient | None = None) -> pd.DataFrame:
    """Download every record of a resource (paginated) as a DataFrame."""
    key = api_key or DATAGOVIN_API_KEY
    if not key:
        raise RuntimeError("DATAGOVIN_API_KEY is not set (see .env.example).")
    client = client or LiveClient("datagovin")
    rows, offset, title = [], 0, ""
    while True:
        params = {"api-key": key, "format": "json", "offset": offset, "limit": page_size}
        for k, v in (filters or {}).items():
            params[f"filters[{k}]"] = v
        page = client.get_json(BASE.format(rid=resource_id), params=params)
        recs = page.get("records", [])
        title = page.get("title", title)
        rows.extend(recs)
        total = int(page.get("total", len(rows)) or len(rows))
        offset += len(recs)
        if not recs or offset >= total or (max_records and offset >= max_records):
            break
    df = pd.DataFrame(rows)
    df.attrs["title"] = title
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resource", required=True, help="resource UUID or a name from live_config.json")
    ap.add_argument("--filter", action="append", default=[], help="field=value (repeatable)")
    ap.add_argument("--out", required=True, help="output file stem in data/external/datagovin/")
    a = ap.parse_args()
    rid = configured_resources().get(a.resource, a.resource)
    flt = dict(f.split("=", 1) for f in a.filter)
    out = fetch(rid, flt)
    path = EXTERNAL_DIR / "datagovin" / f"{a.out}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    print(f"{len(out)} records -> {path}")
