"""
dpdp_masking.py — Privacy controls aligned with India's Digital Personal Data
Protection Act, 2023 (DPDP Act) and the DPDP Rules, 2025.

Principles applied (Act s. 4-8; research/statistics carve-out s. 17(2)(b)):
  * Purpose limitation  — data used only for aggregate valuation research;
                          no decision is taken about any individual.
  * Data minimisation   — party names, addresses, PAN/Aadhaar, phone, e-mail
                          are dropped or redacted at parse time.
  * Pseudonymisation    — record_id = salted SHA-256(sro|doc_no|year); salt kept
                          outside the repository (env var QM640_HASH_SALT).
  * Storage limitation  — raw pages stay on the researcher's machine, are
                          git-ignored, and are deleted after the audit sample.
  * Re-identification   — micro-markets with < K_ANON_MIN records are suppressed
    risk                  in published outputs; flat numbers are never kept.
"""
from __future__ import annotations

import hashlib
import re

import pandas as pd

from src.config import HASH_SALT, K_ANON_MIN, PUBLISHABLE_COLUMNS

PERSONAL_COLUMNS = ["executant_name", "claimant_name", "party_address",
                    "pan", "aadhaar", "phone", "email"]

PATTERNS = {
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "AADHAAR": re.compile(r"\b[2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b"),
    "PHONE": re.compile(r"(?:\+91[\s-]?)?\b[6-9][0-9]{9}\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
    "FLAT_NO": re.compile(r"(?:flat|सदनिका)\s*(?:no\.?|नं\.?|क्र\.?)\s*[\w/-]+", re.I),
}


def pseudonymise(*parts: object, salt: str = HASH_SALT) -> str:
    """Deterministic, non-reversible ID. Same inputs + same salt -> same ID,
    so duplicates can still be detected without storing the document number."""
    key = "|".join(str(p) for p in parts)
    return hashlib.sha256(f"{salt}|{key}".encode("utf-8")).hexdigest()[:16]


def redact_text(text: str) -> str:
    """Replace identifiers in free text with typed placeholders."""
    if not isinstance(text, str):
        return text
    for label, pat in PATTERNS.items():
        text = pat.sub(f"[{label}]", text)
    return text


def mask_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Drop personal columns, pseudonymise IDs, redact free text.
    Returns the masked frame and an audit dict for the provenance log."""
    audit = {"rows_in": len(df)}
    df = df.copy()
    df["record_id"] = [pseudonymise(s, d, y) for s, d, y in
                       zip(df["sro_name"], df["doc_no"], df["reg_date"].astype(str).str[:4])]
    dropped = [c for c in PERSONAL_COLUMNS if c in df.columns]
    df = df.drop(columns=dropped + ["doc_no"], errors="ignore")
    audit["columns_dropped"] = dropped + ["doc_no"]
    for col in df.select_dtypes(include="object").columns:
        if col.startswith("property_description"):
            before = df[col].copy()
            df[col] = df[col].map(redact_text)
            audit[f"redactions_in_{col}"] = int((before != df[col]).sum())
    return df, audit


def assert_no_personal_data(df: pd.DataFrame) -> None:
    """Hard gate before anything is written outside data/raw."""
    leaked = [c for c in PERSONAL_COLUMNS if c in df.columns]
    if leaked:
        raise ValueError(f"DPDP gate failed — personal columns present: {leaked}")
    for col in df.select_dtypes(include="object").columns:
        s = df[col].dropna().astype(str)
        for label in ("PAN", "AADHAAR", "PHONE", "EMAIL"):
            if s.str.contains(PATTERNS[label]).any():
                raise ValueError(f"DPDP gate failed — {label} pattern in column '{col}'")


def publishable_view(df: pd.DataFrame) -> pd.DataFrame:
    """Whitelist columns and suppress small micro-market cells (k-anonymity)."""
    cols = [c for c in PUBLISHABLE_COLUMNS if c in df.columns]
    out = df[cols].copy()
    counts = out["micro_market"].map(out["micro_market"].value_counts())
    out.loc[counts < K_ANON_MIN, "micro_market"] = "SUPPRESSED_SMALL_CELL"
    assert_no_personal_data(out)
    return out
