"""Unit tests: Marathi parsing, DPDP masking, bunching estimator, sample size."""
import numpy as np
import pandas as pd
import pytest

from src.clean.dpdp_masking import assert_no_personal_data, pseudonymise, redact_text
from src.clean.parse_index2 import parse_amount, parse_area, parse_floor, split_fields
from src.clean.translate_marathi import to_arabic_digits, translate_description
from src.models.rq1_bunching import estimate


def test_devanagari_digits():
    assert to_arabic_digits("१,२५,००,०००") == "1,25,00,000"


def test_parse_amount_indian_grouping():
    assert parse_amount("₹ १,२५,००,०००/-") == 12_500_000


def test_parse_area_carpet_and_builtup():
    m2, basis = parse_area("कार्पेट क्षेत्र ८५.५ चौ.मी.")
    assert m2 == pytest.approx(85.5) and basis == 1
    m2, basis = parse_area("बिल्ट अप क्षेत्र 1076.39 चौ.फूट")
    assert m2 == pytest.approx(100 / 1.2, rel=1e-3) and basis == 0


def test_parse_floor():
    assert parse_floor("सदनिका, १२ वा मजला") == 12
    assert parse_floor("तळमजला") == 0


def test_split_fields():
    f = split_fields("(1) विलेखाचा प्रकार: करारनामा\n(2) मोबदला: ५०,००,०००")
    assert f["doc_type_mr"] == "करारनामा" and f["consideration_txt"] == "५०,००,०००"


def test_translation():
    assert "12th floor" in translate_description("१२ वा मजला")


def test_redaction_and_gate():
    t = redact_text("PAN ABCDE1234F, mob 9876543210, a@b.com, Aadhaar 2345 6789 0123")
    assert "[PAN]" in t and "[PHONE]" in t and "[EMAIL]" in t and "[AADHAAR]" in t
    with pytest.raises(ValueError):
        assert_no_personal_data(pd.DataFrame({"executant_name": ["x"]}))


def test_pseudonymise_deterministic_and_salted():
    assert pseudonymise("a", 1, salt="s") == pseudonymise("a", 1, salt="s")
    assert pseudonymise("a", 1, salt="s") != pseudonymise("a", 1, salt="t")


def test_bunching_recovers_known_mass():
    rng = np.random.default_rng(1)
    smooth = rng.lognormal(np.log(1.3), 0.15, 5000)
    smooth = smooth[(smooth > 0.8) & (smooth < 2.0)]
    bunch = rng.uniform(0.995, 1.012, 500)
    est = estimate(np.concatenate([smooth, bunch]))
    assert est["B_excess_count"] == pytest.approx(500, rel=0.15)
    assert estimate(smooth)["b_normalised"] < 2


def test_rq2_design_has_u11_k12():
    from src.models.rq2_hedonic import ATTRS, BASE, design
    df = pd.DataFrame({"ln_asr_rate_m2": [11.0], "ln_carpet_area": [4.0], "area_basis": [1], "floor_no": [3],
                       "new_sale": [0], "parking": [1], "dist_rail_km": [2.0], "dist_cbd_km": [8.0],
                       "municipal_corp": [1], "district": ["Thane"], "fy": ["2025-26"]})
    X = design(df)
    assert len(ATTRS) == 11 and X.shape[1] == 12 and X["district_Thane"].iloc[0] == 1 and X["fy_2025_26"].iloc[0] == 1
