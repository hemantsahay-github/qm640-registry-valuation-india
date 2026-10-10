"""
parse_index2.py — Turn raw Index-II text (Marathi) into structured English fields.

Index-II extracts use numbered fields, which are stable even when label
spelling varies between SROs, so parsing keys on the numbers:
  (1) deed type   (2) consideration   (3) market value per ASR
  (4) property description   (5) area   (7) executant   (8) claimant
  (9) execution date   (10) registration date   (12) stamp duty   (13) reg. fee
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.clean.translate_marathi import (DISTRICTS, DOC_TYPES, to_arabic_digits,
                                         translate_description, translate_sro,
                                         transliterate_place)
from src.config import BUILTUP_TO_CARPET, SQFT_PER_SQM

FIELD_RE = re.compile(r"\((\d{1,2})\)\s*(.*?)(?=\n\s*\(\d{1,2}\)|\Z)", re.S)
FIELD_MAP = {1: "doc_type_mr", 2: "consideration_txt", 3: "asr_value_txt",
             4: "property_description_mr", 5: "area_txt", 7: "executant_name",
             8: "claimant_name", 9: "exec_date_txt", 10: "reg_date_txt",
             12: "stamp_duty_txt", 13: "reg_fee_txt"}


def split_fields(text: str) -> dict:
    out = {}
    for num, chunk in FIELD_RE.findall(text or ""):
        key = FIELD_MAP.get(int(num))
        if key:   # value = text after the first ':' (labels sometimes lack one)
            out[key] = (chunk.split(":", 1)[1] if ":" in chunk else chunk).strip()
    return out


def parse_amount(txt: str) -> float:
    """'१,२५,००,०००' -> 12500000.0 ; returns NaN when absent."""
    if not isinstance(txt, str):
        return np.nan
    m = re.search(r"[\d,]+(?:\.\d+)?", to_arabic_digits(txt))
    return float(m.group(0).replace(",", "")) if m else np.nan


def parse_area(txt: str) -> tuple[float, int]:
    """Return (carpet area in m2, area_basis) where area_basis = 1 if carpet
    area was recorded directly, 0 if converted from built-up/sq ft."""
    if not isinstance(txt, str):
        return np.nan, 0
    t = to_arabic_digits(txt)
    m = re.search(r"([\d.]+)\s*(चौ\.मी\.|चौ\.मीटर|sq\.?\s*m|चौ\.फूट|sq\.?\s*ft)", t)
    if not m:
        return np.nan, 0
    val, unit = float(m.group(1)), m.group(2)
    m2 = val / SQFT_PER_SQM if ("फूट" in unit or "ft" in unit) else val
    is_carpet = "कार्पेट" in t or "carpet" in t.lower()
    return (m2 if is_carpet else m2 * BUILTUP_TO_CARPET), int(is_carpet)


def parse_floor(desc: str) -> float:
    if not isinstance(desc, str):
        return np.nan
    t = to_arabic_digits(desc)
    if "तळमजला" in t or "ground floor" in t.lower():
        return 0
    m = re.search(r"(\d{1,3})\s*(?:वा|वे|था|ला|रा|st|nd|rd|th)?\s*(?:मजला|floor)", t)
    return float(m.group(1)) if m else np.nan


def parse_date(txt: str) -> pd.Timestamp:
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", to_arabic_digits(txt or ""))
    return pd.Timestamp(f"{m.group(3)}-{m.group(2)}-{m.group(1)}") if m else pd.NaT


def parse_record(row: pd.Series) -> dict:
    f = split_fields(row["index2_text"])
    desc = f.get("property_description_mr", "")
    carpet, basis = parse_area(f.get("area_txt", ""))
    doc_type_raw = re.sub(r"\s+", " ", f.get("doc_type_mr", "")).strip()
    return {
        "sro_name": translate_sro(row["sro_name"]), "doc_no": row["doc_no"],
        "district": DISTRICTS.get(row["district_mr"], row["district_mr"]),
        "micro_market": transliterate_place(row["village_mr"]),
        "doc_type": DOC_TYPES.get(doc_type_raw, "other"),
        "reg_date": parse_date(f.get("reg_date_txt")),
        "consideration_inr": parse_amount(f.get("consideration_txt")),
        "asr_value_inr": parse_amount(f.get("asr_value_txt")),
        "stamp_duty_inr": parse_amount(f.get("stamp_duty_txt")),
        "carpet_area_m2": carpet, "area_basis": basis,
        "floor_no": parse_floor(desc),
        "parking": int("पार्किंग" in desc and "पार्किंग नाही" not in desc),
        "new_sale": int("प्रवर्तक" in desc or "प्रथम विक्री" in desc),
        "municipal_corp": int("म.न.पा." in desc or "महानगरपालिका" in desc),
        "property_description_en": translate_description(desc),
        "executant_name": f.get("executant_name"),   # dropped in masking step
        "claimant_name": f.get("claimant_name"),     # dropped in masking step
        "is_synthetic": row.get("is_synthetic", 0),
    }


def parse_raw(raw: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([parse_record(r) for _, r in raw.iterrows()])
