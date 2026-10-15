"""
src/live — LIVE DATA CONNECTORS for the real-data study run.

Every module here connects to one of the public sources named in the
synopsis (Table 2). The access method follows what each source actually
offers — there is no single "government API" for all of them:

  module             source                         access method
  ---------------    ----------------------------   ---------------------------------
  datagovin.py       Open Government Data (OGD)     official REST API (api-key)
  osm.py             OpenStreetMap                  official Overpass + Nominatim APIs
  rbi_hpi.py         RBI DBIE house price index     DBIE export file (no public API);
                                                    optional data.gov.in API mirror
  nhb_residex.py     NHB RESIDEX                    published download file (no API)
  igr_asr.py         IGR Maharashtra ASR / eASR     exported rate table (no API)
  maharera.py        MahaRERA project registry      exported project list (no API)
  (src/ingest/igr_index2.py)  IGR Index-II          assisted capture, CAPTCHA (no API)

Shared plumbing: http.py (retries, rate limits, cache, provenance log),
index_utils.py (quarter parsing / index normalisation), sources.py (catalogue).
CLI: python -m src.live.fetch_all --check

The synthetic-data logic is untouched and preserved on the git branch
archive/v1.0-synthetic-validation.
"""
