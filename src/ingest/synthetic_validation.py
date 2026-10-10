"""
synthetic_validation.py — SYNTHETIC test data that mimics Index-II extracts.

!!! NOT STUDY DATA !!!
Walsh QM 640 forbids projects built on fictitious data. This generator exists
only to (a) unit-test the Marathi parser and DPDP masking, and (b) run the
RQ1-RQ4 code end-to-end before real records are collected. Every row carries
is_synthetic = 1 and every output produced from it is stamped
"PIPELINE VALIDATION — SYNTHETIC". Replace with data/raw/index2_raw.csv from
src.ingest.igr_index2 for the actual study.

Data-generating process (so results can be checked against known truth):
  ASR rate     ~ micro-market base rate x yearly ASR revision
  market value = ASR value x micro-market premium x hedonic effects x noise
  declared     = ASR value (anchored, prob. depends on premium & resale)
               | market value x partial under-statement (non-anchored)
Known truth (for validating RQ1/RQ4): anchored share ~ 12-15%.
"""
from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd

from src.config import RANDOM_SEED, RAW_FILE

ANCHOR_FLOOR = 1.0

# (Marathi name, English, district, base ASR Rs/m2, lat, lon, premium, municipal)
MICRO_MARKETS = [
    ("बाणेर", "Baner", "Pune", 98000, 18.559, 73.786, 1.32, 1),
    ("वाकड", "Wakad", "Pune", 82000, 18.599, 73.763, 1.25, 1),
    ("हिंजवडी", "Hinjewadi", "Pune", 72000, 18.591, 73.739, 1.18, 0),
    ("खराडी", "Kharadi", "Pune", 95000, 18.551, 73.940, 1.35, 1),
    ("हडपसर", "Hadapsar", "Pune", 76000, 18.503, 73.926, 1.15, 1),
    ("वाघोली", "Wagholi", "Pune", 56000, 18.580, 73.983, 1.08, 0),
    ("कोथरूड", "Kothrud", "Pune", 112000, 18.507, 73.807, 1.30, 1),
    ("औंध", "Aundh", "Pune", 118000, 18.558, 73.807, 1.38, 1),
    ("विमाननगर", "Viman Nagar", "Pune", 110000, 18.567, 73.914, 1.33, 1),
    ("उंड्री", "Undri", "Pune", 60000, 18.457, 73.910, 1.10, 1),
    ("पिंपळे सौदागर", "Pimple Saudagar", "Pune", 84000, 18.599, 73.796, 1.22, 1),
    ("रावेत", "Ravet", "Pune", 64000, 18.648, 73.743, 1.12, 1),
    ("मोशी", "Moshi", "Pune", 52000, 18.672, 73.851, 1.06, 1),
    ("धानोरी", "Dhanori", "Pune", 70000, 18.591, 73.904, 1.14, 1),
    ("बावधन", "Bavdhan", "Pune", 92000, 18.515, 73.776, 1.28, 1),
    ("सूस", "Sus", "Pune", 68000, 18.546, 73.752, 1.16, 0),
    ("ताथवडे", "Tathawade", "Pune", 66000, 18.618, 73.747, 1.13, 1),
    ("पुनावळे", "Punawale", "Pune", 62000, 18.633, 73.736, 1.11, 1),
    ("कोंढवा", "Kondhwa", "Pune", 64000, 18.473, 73.890, 1.12, 1),
    ("चाकण", "Chakan", "Pune", 38000, 18.761, 73.861, 1.03, 0),
    ("माजिवडे", "Majiwada", "Thane", 128000, 19.229, 72.982, 1.30, 1),
    ("कोलशेत", "Kolshet", "Thane", 118000, 19.224, 72.986, 1.27, 1),
    ("बाळकुम", "Balkum", "Thane", 124000, 19.218, 72.981, 1.28, 1),
    ("कासारवडवली", "Kasarvadavali", "Thane", 108000, 19.262, 72.968, 1.22, 1),
    ("वाघबीळ", "Waghbil", "Thane", 112000, 19.252, 72.973, 1.24, 1),
    ("कळवा", "Kalwa", "Thane", 92000, 19.199, 72.999, 1.12, 1),
    ("डोंबिवली", "Dombivli", "Thane", 82000, 19.218, 73.087, 1.12, 1),
    ("कल्याण", "Kalyan", "Thane", 74000, 19.244, 73.130, 1.10, 1),
    ("मीरा रोड", "Mira Road", "Thane", 104000, 19.281, 72.869, 1.20, 1),
    ("भिवंडी", "Bhiwandi", "Thane", 52000, 19.296, 73.063, 1.05, 1),
    ("अंबरनाथ", "Ambernath", "Thane", 54000, 19.209, 73.186, 1.06, 1),
    ("बदलापूर", "Badlapur", "Thane", 50000, 19.155, 73.265, 1.05, 1),
    ("उल्हासनगर", "Ulhasnagar", "Thane", 62000, 19.221, 73.164, 1.08, 1),
    ("पाचपाखाडी", "Panchpakhadi", "Thane", 140000, 19.196, 72.975, 1.34, 1),
    ("मानपाडा", "Manpada", "Thane", 116000, 19.236, 72.976, 1.25, 1),
    ("टिटवाळा", "Titwala", "Thane", 42000, 19.297, 73.204, 1.04, 0),
]
SRO = {"Pune": ["हवेली 1", "हवेली 4", "हवेली 11", "हवेली 18", "मुळशी", "खेड"],
       "Thane": ["ठाणे 2", "ठाणे 5", "ठाणे 9", "कल्याण 3", "उल्हासनगर 1", "भिवंडी 2"]}
FY_ASR_REVISION = {2023: 1.00, 2024: 1.00, 2025: 1.045}   # ASR revised 1 Apr 2025
FIRST = ["राहुल", "प्रिया", "अमित", "स्नेहा", "संदीप", "पूजा", "विकास", "अश्विनी"]
LAST = ["पाटील", "जोशी", "देशमुख", "कुलकर्णी", "शिंदे", "पवार", "गायकवाड", "जाधव"]
DEV = str.maketrans("0123456789", "०१२३४५६७८९")


def _dev(n) -> str:
    """Render a number with Devanagari digits, as on the portal."""
    return str(n).translate(DEV)


def _fmt_inr(x: float) -> str:
    """Indian digit grouping, e.g. 12500000 -> 1,25,00,000."""
    s = str(int(round(x)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def generate(n: int = 1800, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    random.seed(seed)
    rows = []
    start = pd.Timestamp("2023-04-01")
    for i in range(n):
        mm = MICRO_MARKETS[rng.integers(len(MICRO_MARKETS))]
        mr, en, dist, base, lat, lon, prem, muni = mm
        reg_date = start + pd.Timedelta(days=int(rng.integers(0, 1096)))
        fy_start = reg_date.year if reg_date.month >= 4 else reg_date.year - 1
        asr_rate = base * FY_ASR_REVISION[fy_start]
        carpet = float(np.clip(rng.lognormal(math.log(62), 0.35), 25, 260))
        floor = int(rng.integers(0, 32))
        new_sale = int(rng.random() < 0.45)
        parking = int(rng.random() < 0.65)
        builtup_only = int(rng.random() < 0.15)
        # ASR value includes the floor rise rule (+5% above 4th floor in many zones)
        floor_adj = 1.05 if floor > 4 else 1.0
        asr_value = asr_rate * carpet * floor_adj
        # latent market value: premium x hedonic effects x yearly drift x noise
        drift = 1 + 0.06 * (reg_date - start).days / 365
        hed = (1 + 0.004 * floor) * (1.04 if parking else 1) * (1.05 if new_sale else 1)
        mkt = asr_value * prem * hed * drift * rng.lognormal(0, 0.10)
        # anchoring propensity rises with premium; developers anchor less
        p_anchor = 1 / (1 + math.exp(-(-3.4 + 2.6 * (prem - 1.0) + 0.9 * (1 - new_sale)
                                         + 0.4 * (dist == "Thane"))))
        if rng.random() < p_anchor:
            declared = asr_value * rng.uniform(0.995, 1.012)
        elif mkt < asr_value:
            declared = mkt * rng.uniform(0.97, 1.0)          # below-ASR deals
        else:
            declared = mkt * rng.uniform(0.88, 1.0)            # partial under-statement
            if declared < asr_value * ANCHOR_FLOOR:              # duty is on ASR anyway ->
                declared = asr_value * rng.uniform(0.995, 1.012)  # declare at ASR
        stamp = 0.06 * max(declared, asr_value)                # 5% duty + 1% cess
        reg_fee = min(30000, 0.01 * max(declared, asr_value))
        doc_type = "करारनामा" if new_sale else "खरेदीखत"
        if rng.random() < 0.04:                                 # out-of-scope docs
            doc_type = random.choice(["बक्षीसपत्र", "गहाणखत", "भाडेकरार"])
        area_txt = (f"बिल्ट अप क्षेत्र {_dev(round(carpet * 1.2 * 10.7639, 0))} चौ.फूट"
                    if builtup_only else f"कार्पेट क्षेत्र {_dev(round(carpet, 2))} चौ.मी.")
        floor_txt = "तळमजला" if floor == 0 else f"{_dev(floor)} वा मजला"
        parties = f"{random.choice(FIRST)} {random.choice(LAST)}"
        pan = f"ZZZPZ{rng.integers(1000, 9999)}Z"
        desc = (f"पालिकेचे नाव: {'म.न.पा.' if muni else 'ग्रामपंचायत'}, "
                f"इतर माहिती: सदनिका नं. {_dev(int(rng.integers(101, 3204)))}, {floor_txt}, "
                f"{area_txt}{', कार पार्किंग' if parking else ''}"
                f"{', प्रवर्तक प्रथम विक्री' if new_sale else ''}, गाव {mr}")
        text = (f"(1) विलेखाचा प्रकार: {doc_type}\n(2) मोबदला: {_dev(_fmt_inr(declared))}\n"
                f"(3) बाजारभाव: {_dev(_fmt_inr(asr_value))}\n(4) भू-मापन, पोटहिस्सा व घरक्रमांक: {desc}\n"
                f"(5) क्षेत्रफळ: {area_txt}\n(7) लिहून देणाऱ्याचे नाव: {parties}, पॅन नं: {pan}\n"
                f"(8) लिहून घेणाऱ्याचे नाव: {random.choice(FIRST)} {random.choice(LAST)}\n"
                f"(9) दस्तऐवज करुन दिल्याचा दिनांक: {_dev(reg_date.strftime('%d/%m/%Y'))}\n"
                f"(10) दस्त नोंदणी केल्याचा दिनांक: {_dev(reg_date.strftime('%d/%m/%Y'))}\n"
                f"(12) बाजारभावाप्रमाणे मुद्रांक शुल्क: {_dev(_fmt_inr(stamp))}\n"
                f"(13) बाजारभावाप्रमाणे नोंदणी शुल्क: {_dev(_fmt_inr(reg_fee))}")
        if rng.random() < 0.02:                                 # unparseable area -> excluded
            text = text.replace("चौ.मी.", "").replace("चौ.फूट", "")
        rows.append({"capture_ts": "SYNTHETIC", "scraper_version": "synthetic-1.0",
                     "source_url": "SYNTHETIC", "district_mr": {"Pune": "पुणे", "Thane": "ठाणे"}[dist],
                     "sro_name": random.choice(SRO[dist]), "village_mr": mr,
                     "doc_no": f"{rng.integers(1000, 29999)}/{reg_date.year}",
                     "index2_text": text, "is_synthetic": 1,
                     "_true_market_value": round(mkt), "_true_anchored": int(abs(declared / asr_value - 1) <= 0.02)})
    df = pd.DataFrame(rows)
    # inject 1% exact duplicates (real portal re-captures happen)
    df = pd.concat([df, df.sample(frac=0.01, random_state=seed)], ignore_index=True)
    return df


if __name__ == "__main__":
    out = generate()
    RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
    synthetic_path = RAW_FILE.with_name("index2_raw_SYNTHETIC.csv")
    out.to_csv(synthetic_path, index=False, encoding="utf-8")
    print(f"SYNTHETIC validation data: {len(out)} rows -> {synthetic_path}")
