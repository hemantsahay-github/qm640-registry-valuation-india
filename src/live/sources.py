"""
sources.py — Catalogue of every live source in the synopsis (Table 2): where it
lives, how it is accessed, what credential it needs, and where its normalised
file is written. `python -m src.live.fetch_all --check` reads this table.
"""
from __future__ import annotations

from src.config import EXTERNAL_DIR, RAW_FILE

SOURCES = {
    "igr_index2": {
        "next_step": "python -m src.ingest.igr_index2 --district Pune --max 200   (laptop, CAPTCHA)",
        "name": "IGR Maharashtra Index-II free search",
        "url": "https://freesearchigrservice.maharashtra.gov.in",
        "access": "ASSISTED CAPTURE (no public API; CAPTCHA per search)",
        "module": "src.ingest.igr_index2", "credential": None,
        "output": RAW_FILE, "used_by": "ETL -> RQ1-RQ4 (core study data)"},
    "igr_asr": {
        "next_step": "python -m src.live.igr_asr --template ; then --load <filled.csv>",
        "name": "IGR Maharashtra Annual Statement of Rates (eASR)",
        "url": "https://igrmaharashtra.gov.in",
        "access": "EXPORT FILE (no public API) -> src.live.igr_asr --load",
        "module": "src.live.igr_asr", "credential": None,
        "output": EXTERNAL_DIR / "asr_rates" / "asr_rates.csv", "used_by": "ETL check of Index-II ASR value"},
    "maharera": {
        "next_step": "python -m src.live.maharera --load <projects.csv>",
        "name": "MahaRERA project registry",
        "url": "https://maharera.maharashtra.gov.in",
        "access": "EXPORT FILE (no public API) -> src.live.maharera --load",
        "module": "src.live.maharera", "credential": None,
        "output": EXTERNAL_DIR / "maharera" / "projects.csv", "used_by": "new_sale flag verification"},
    "nhb_residex": {
        "next_step": "python -m src.live.nhb_residex --load <residex.xlsx>",
        "name": "NHB RESIDEX",
        "url": "https://residex.nhbonline.org.in",
        "access": "DOWNLOAD FILE (no public API) -> src.live.nhb_residex --load",
        "module": "src.live.nhb_residex", "credential": None,
        "output": EXTERNAL_DIR / "residex" / "residex.csv", "used_by": "RQ4 external validation"},
    "rbi_hpi": {
        "next_step": "python -m src.live.rbi_hpi --load <dbie_export.xlsx>   (or --api)",
        "name": "RBI DBIE All-India House Price Index (18 cities incl. Pune, Thane; base 2022-23)",
        "url": "https://data.rbi.org.in/DBIE/#/dbie/home",
        "access": "DBIE EXPORT FILE (no documented public API); optional data.gov.in API mirror",
        "module": "src.live.rbi_hpi", "credential": "DATAGOVIN_API_KEY (only for API mirror)",
        "output": EXTERNAL_DIR / "rbi_dbie" / "rbi_hpi.csv", "used_by": "RQ4 external validation"},
    "datagovin": {
        "next_step": "python -m src.live.datagovin --resource <uuid> --out <name>",
        "name": "Open Government Data Platform India (data.gov.in)",
        "url": "https://api.data.gov.in/resource/{resource_id}",
        "access": "OFFICIAL REST API (api-key, JSON, offset/limit, filters[field]=value)",
        "module": "src.live.datagovin", "credential": "DATAGOVIN_API_KEY",
        "output": EXTERNAL_DIR / "datagovin", "used_by": "any OGD dataset configured in live_config.json"},
    "osm": {
        "next_step": "python -m src.live.fetch_all --run osm",
        "name": "OpenStreetMap (Overpass + Nominatim)",
        "url": "https://overpass-api.de/api/interpreter ; https://nominatim.openstreetmap.org",
        "access": "OFFICIAL OPEN APIs (ODbL; 1 req/s Nominatim; identifying User-Agent)",
        "module": "src.live.osm", "credential": "QM640_CONTACT_EMAIL (User-Agent)",
        "output": EXTERNAL_DIR / "osm", "used_by": "dist_rail_km, dist_cbd_km, lat/lon"},
}
