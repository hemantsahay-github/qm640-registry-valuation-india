"""Unit tests for src/live (live-data connectors). Network calls are mocked with
responses in each API's documented format, so tests run offline and in CI."""
import json

import numpy as np
import pandas as pd
import pytest

from src.live import datagovin, http, osm
from src.live.index_utils import fy_quarter, normalise_index


class FakeClient:
    """Stands in for LiveClient; records calls and returns canned payloads."""
    def __init__(self, pages):
        self.pages, self.calls = list(pages), []

    def get_json(self, url, **kw):
        self.calls.append((url, kw))
        return self.pages.pop(0)

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        return json.dumps(self.pages.pop(0)).encode()


@pytest.mark.parametrize("raw,expected", [
    ("Q1:2025-26", "FY26Q1"), ("2025-26 Q3", "FY26Q3"), ("Q4 FY26", "FY26Q4"),
    ("2025-06-30", "FY26Q1"), ("Jan-2026", "FY26Q4"), ("Q2:2024-25", "FY25Q2"), ("n/a", None)])
def test_fy_quarter_parsing(raw, expected):
    assert fy_quarter(raw) == expected


def test_normalise_index_wide_and_long():
    wide = pd.DataFrame({"Quarter": ["Q1:2025-26", "Q2:2025-26"], "Pune": [101.2, 103.0],
                         "Thane": [100.5, 102.1], "Delhi": [99, 98]})
    w = normalise_index(wide, "RBI HPI", "test")
    assert set(w["city"]) == {"Pune", "Thane"} and len(w) == 4 and w["quarter"].iloc[0] == "FY26Q1"
    long = pd.DataFrame({"City Name": ["PUNE", "Thane", "Mumbai"], "Period": ["2025-26 Q1"] * 3,
                         "HPI @ Assessment Price": ["1,234.5", "980", "1500"]})
    lg = normalise_index(long, "RESIDEX", "test")
    assert lg.loc[lg.city == "Pune", "index"].iloc[0] == 1234.5 and len(lg) == 2


def test_datagovin_paginates_and_sends_filters():
    pages = [{"total": 3, "title": "HPI", "records": [{"a": 1}, {"a": 2}]},
             {"total": 3, "records": [{"a": 3}]}]
    fc = FakeClient(pages)
    df = datagovin.fetch("uuid-123", {"city": "Pune"}, page_size=2, api_key="SECRET", client=fc)
    assert len(df) == 3 and df.attrs["title"] == "HPI"
    url, kw = fc.calls[0]
    assert url.endswith("/resource/uuid-123") and kw["params"]["filters[city]"] == "Pune"
    assert kw["params"]["api-key"] == "SECRET" and fc.calls[1][1]["params"]["offset"] == 2


def test_datagovin_requires_key(monkeypatch):
    monkeypatch.setattr(datagovin, "DATAGOVIN_API_KEY", "")
    with pytest.raises(RuntimeError):
        datagovin.fetch("x", client=FakeClient([]))


def test_api_key_never_logged(tmp_path, monkeypatch):
    log = tmp_path / "prov.csv"
    monkeypatch.setattr(http, "LIVE_PROVENANCE", log)
    http.log_provenance("datagovin", "https://api.data.gov.in/resource/x?api-key=SECRET123&format=json", 200, b"{}")
    text = log.read_text()
    assert "SECRET123" not in text and "api-key=***" in text


def test_osm_overpass_parsing():
    payload = {"elements": [
        {"id": 1, "lat": 18.53, "lon": 73.87, "tags": {"railway": "station", "name": "Pune Junction"}},
        {"id": 2, "lat": 18.50, "lon": 73.80, "tags": {"station": "subway", "name:en": "Vanaz"}},
        {"id": 3, "lat": 18.6, "lon": 73.9, "tags": {"railway": "halt"}}]}             # unnamed -> skipped
    st = osm.stations(client=FakeClient([payload, {"elements": []}]))
    assert len(st) == 2 and set(st["mode"]) == {"rail", "metro"}
    assert "railway" in osm.overpass_query(1, 2, 3, 4)


def test_igr_asr_validation_and_check(tmp_path, monkeypatch):
    from src.live import igr_asr
    monkeypatch.setattr(igr_asr, "OUT", tmp_path / "asr.csv")
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"district": ["Pune"], "micro_market": ["Baner"], "fy": ["2024-25"],
                  "residential_rate_inr_m2": [9_000]}).assign(residential_rate_inr_m2=[900]).to_csv(bad, index=False)
    with pytest.raises(ValueError):
        igr_asr.load(bad)
    asr = pd.DataFrame({"micro_market": ["Baner"], "fy": ["2024-25"], "residential_rate_inr_m2": [100_000]})
    an = pd.DataFrame({"record_id": ["r1", "r2"], "micro_market": ["Baner"] * 2, "fy": ["2024-25"] * 2,
                       "asr_value_inr": [5_000_000, 8_000_000], "carpet_area_m2": [50, 50], "floor_no": [2, 2]})
    chk = igr_asr.check_against_index2(an, asr)
    assert chk["asr_check_ratio"].round(2).tolist() == [1.0, 1.6] and chk["asr_check_flag"].tolist() == [False, True]


def test_maharera_verify_new_sale():
    from src.live.maharera import verify_new_sale
    proj = pd.DataFrame({"micro_market": ["Baner"], "project_name": ["Skyline Heights"]})
    interim = pd.DataFrame({"record_id": ["a", "b", "c"], "micro_market": ["Baner", "Baner", "Wakad"],
                            "property_description_en": ["flat in skyline heights, 5th floor",
                                                        "old building resale", "promoter first sale"],
                            "new_sale": [1, 1, 1]})
    v = verify_new_sale(interim, proj).set_index("record_id")
    assert v.loc["a", "rera_new_sale"] == 1 and v.loc["b", "mismatch"] and v.loc["c", "rera_new_sale"] == 0


def test_rq4_external_compare_direction():
    from src.models.rq4_external_validation import compare, fy_of_quarter
    assert fy_of_quarter("FY26Q1") == "2025-26"
    cf = pd.DataFrame({"district": ["Pune"] * 3, "fy": ["2023-24", "2024-25", "2025-26"], "cf": [1.20, 1.30, 1.25]})
    an = pd.DataFrame({"district": ["Pune"] * 3, "fy": ["2023-24", "2024-25", "2025-26"],
                       "asr_rate_m2": [100.0, 100.0, 110.0]})
    idx = pd.DataFrame({"city": ["Pune"] * 3, "quarter": ["FY24Q1", "FY25Q1", "FY26Q1"], "index": [100.0, 108.0, 112.0]})
    t = compare(cf, an, idx)
    # 2024-25: market +8% vs ASR 0% -> gap>0 and CF rose -> agree; 2025-26: +3.7% vs +10% -> gap<0, CF fell -> agree
    assert t["direction_agree"].dropna().astype(bool).all() and np.isclose(t["index_yoy"].iloc[1], 0.08)
