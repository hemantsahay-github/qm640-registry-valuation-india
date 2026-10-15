"""
index_utils.py — Normalise price-index files (RBI HPI, NHB RESIDEX) into one
long format:  city | quarter (FYyyQq) | index | series | source

Handles the two layouts these publishers use:
  * long : one row per city x period  (columns like City, Quarter, Index)
  * wide : one row per period, one column per city (Pune, Thane, ...)
and the period spellings seen in RBI/NHB releases, e.g. "Q1:2025-26",
"2025-26 Q1", "Q1 FY26", "Jun-2025", "2025-06-30".
"""
from __future__ import annotations

import re

import pandas as pd

from src.config import STUDY_CITIES

# Indian FY quarters: Q1 Apr-Jun, Q2 Jul-Sep, Q3 Oct-Dec, Q4 Jan-Mar
_MONTH_Q = {4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3, 1: 4, 2: 4, 3: 4}


def fy_quarter(value) -> str | None:
    """Return 'FY26Q1' style label (FY named by its ending year), or None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    m = re.search(r"Q\s*([1-4])\s*[:\-, ]*\s*(?:FY)?\s*(\d{4})\s*[-/–]\s*(\d{2,4})", s, re.I)  # Q1:2025-26
    if m:
        q, y1 = int(m.group(1)), int(m.group(2))
        return f"FY{str(y1 + 1)[-2:]}Q{q}"
    m = re.search(r"(\d{4})\s*[-/–]\s*(\d{2,4})\s*[:\-, ]*\s*Q\s*([1-4])", s, re.I)            # 2025-26 Q1
    if m:
        return f"FY{str(int(m.group(1)) + 1)[-2:]}Q{int(m.group(3))}"
    m = re.search(r"Q\s*([1-4])\s*FY\s*(\d{2,4})", s, re.I)                                   # Q1 FY26
    if m:
        return f"FY{m.group(2)[-2:]}Q{int(m.group(1))}"
    try:                                                                                    # dates / Jun-2025
        d = pd.to_datetime(s, dayfirst=False)
    except (ValueError, TypeError):
        return None
    fy_end = d.year + 1 if d.month >= 4 else d.year
    return f"FY{str(fy_end)[-2:]}Q{_MONTH_Q[d.month]}"


def _find(cols, *cands):
    low = {c.lower().strip(): c for c in cols}
    for cand in cands:
        for lc, orig in low.items():
            if cand in lc:
                return orig
    return None


def normalise_index(df: pd.DataFrame, series: str, source: str,
                    cities: tuple = STUDY_CITIES) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    city_cols = [c for c in df.columns if c.strip().lower() in {x.lower() for x in cities}]
    if city_cols:                                                    # wide layout
        per = _find(df.columns, "quarter", "period", "date", "month", "year") or df.columns[0]
        long = df.melt(id_vars=[per], value_vars=city_cols, var_name="city", value_name="index")
        long = long.rename(columns={per: "period"})
    else:                                                            # long layout
        c_city = _find(df.columns, "city", "centre", "center", "location")
        c_per = _find(df.columns, "quarter", "period", "date", "month")
        c_val = _find(df.columns, "index", "hpi", "value", "assessment")
        if not (c_city and c_per and c_val):
            raise ValueError(f"Cannot identify city/period/index columns in {list(df.columns)}")
        long = df.rename(columns={c_city: "city", c_per: "period", c_val: "index"})[["city", "period", "index"]]
    long["city"] = long["city"].astype(str).str.strip().str.title()
    long = long[long["city"].isin(cities)].copy()
    long["quarter"] = long["period"].map(fy_quarter)
    long["index"] = pd.to_numeric(long["index"].astype(str).str.replace(",", ""), errors="coerce")
    long = long.dropna(subset=["quarter", "index"])
    long["series"], long["source"] = series, source
    return long[["city", "quarter", "index", "series", "source"]].sort_values(["city", "quarter"]).reset_index(drop=True)


def read_any(path) -> pd.DataFrame:
    p = str(path).lower()
    if p.endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    return pd.read_csv(path)
