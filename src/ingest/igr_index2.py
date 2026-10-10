"""
igr_index2.py — Assisted collection of Maharashtra Index-II extracts.

Source : IGR Maharashtra free search, https://freesearchigrservice.maharashtra.gov.in
Access : free, but every search requires a CAPTCHA, so collection is
         *human-in-the-loop*: the researcher types the CAPTCHA and opens
         Index-II pages; this script captures each opened page, extracts the
         numbered Index-II fields, and appends ONE row per document to
         data/raw/index2_raw.csv. Party names are captured into the raw file
         only so that the masking step can prove it removed them; raw files are
         git-ignored and deleted after the 5% manual audit (DPDP storage limit).

Run (on your own laptop — portal is not reachable from cloud runners):
    pip install playwright && playwright install chromium
    python -m src.ingest.igr_index2 --district Pune --year 2024 --max 200

Sampling: stratify by SRO x quarter; within each stratum pick random
property / survey numbers (scripts/make_search_keys.py) so the sample is
randomised rather than convenience-based.
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import time
from datetime import datetime

from src.config import RAW_FILE, SCRAPE_DELAY_SECONDS

PORTAL_URL = "https://freesearchigrservice.maharashtra.gov.in"
SCRAPER_VERSION = "0.3.0"
RAW_FIELDS = ["capture_ts", "scraper_version", "source_url", "district_mr",
              "sro_name", "village_mr", "doc_no", "index2_text", "is_synthetic"]


def _clean_page_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _extract_header(text: str) -> dict:
    """Pull SRO, document number and village from the Index-II header block."""
    sro = re.search(r"दुय्यम निबंधक\s*[:：]?\s*([^\n]+)", text)
    doc = re.search(r"दस्त क्रमांक\s*[:：]?\s*([0-9०-९/]+)", text)
    vil = re.search(r"गावाचे नाव\s*[:：]?\s*([^\n]+)", text)
    return {"sro_name": sro.group(1).strip() if sro else "",
            "doc_no": doc.group(1).strip() if doc else "",
            "village_mr": vil.group(1).strip() if vil else ""}


def capture_session(district_mr: str, max_docs: int) -> int:
    """Open a visible browser; every new tab containing an Index-II extract is
    captured automatically. Close the browser when done."""
    from playwright.sync_api import sync_playwright   # imported lazily

    RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
    new_file = not RAW_FILE.exists()
    captured = 0
    with sync_playwright() as p, open(RAW_FILE, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RAW_FIELDS)
        if new_file:
            writer.writeheader()
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(locale="mr-IN")
        page = ctx.new_page()
        page.goto(PORTAL_URL)
        print("Search manually (district, year, village, property no., CAPTCHA).\n"
              "Click 'IndexII' on each result; pages are captured automatically.")

        def on_page(new_page):
            nonlocal captured
            new_page.wait_for_load_state("domcontentloaded")
            text = _clean_page_text(new_page.inner_text("body"))
            if "(2)" not in text or "मोबदला" not in text:
                return                                   # not an Index-II page
            row = {"capture_ts": datetime.now().isoformat(timespec="seconds"),
                   "scraper_version": SCRAPER_VERSION, "source_url": new_page.url,
                   "district_mr": district_mr, "index2_text": text, "is_synthetic": 0,
                   **_extract_header(text)}
            writer.writerow(row)
            fh.flush()
            captured += 1
            print(f"  captured {captured}: doc {row['doc_no']}")
            time.sleep(random.uniform(*SCRAPE_DELAY_SECONDS))  # polite rate limit

        ctx.on("page", on_page)
        while captured < max_docs and browser.is_connected():
            try:
                page.wait_for_timeout(1000)
            except Exception:
                break
        browser.close()
    return captured


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--district", choices=["Pune", "Thane"], required=True)
    ap.add_argument("--max", type=int, default=200)
    a = ap.parse_args()
    n = capture_session({"Pune": "पुणे", "Thane": "ठाणे"}[a.district], a.max)
    print(f"Done: {n} Index-II documents appended to {RAW_FILE}")
