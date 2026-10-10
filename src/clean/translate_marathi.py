"""
translate_marathi.py — Marathi (Devanagari) to English normalisation for Index-II.

Why   : Maharashtra Index-II extracts are published largely in Marathi, with
        Devanagari numerals (०-९) and Marathi field labels. Models need English
        column names and Arabic numerals.
How   : 1) deterministic glossary for field labels, document types, units and
           locality names (reproducible, auditable — preferred for research);
        2) rule-based transliteration fallback for unseen place names;
        3) OPTIONAL online machine translation (deep-translator) for residual
           free text, used only in Colab and logged, never for numeric fields.
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------- numerals
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def to_arabic_digits(text: str) -> str:
    """'१२,५०,०००' -> '12,50,000'."""
    return text.translate(DEVANAGARI_DIGITS) if isinstance(text, str) else text


# --------------------------------------------------------------------------- field labels
FIELD_LABELS = {
    "दस्त क्रमांक": "doc_no",
    "दुय्यम निबंधक": "sro_name",
    "नोंदणीचा दिनांक": "reg_date",
    "दस्तऐवजाचा प्रकार": "doc_type_mr",
    "गावाचे नाव": "village_mr",
    "मोबदला": "consideration",
    "बाजारभाव": "market_value_asr",
    "मुद्रांक शुल्क": "stamp_duty",
    "नोंदणी शुल्क": "registration_fee",
    "मालमत्तेचे वर्णन": "property_description_mr",
    "लिहून देणाऱ्याचे नाव": "executant_name",     # personal data -> dropped
    "लिहून घेणाऱ्याचे नाव": "claimant_name",       # personal data -> dropped
    "जिल्हा": "district_mr",
}

# --------------------------------------------------------------------------- document types
DOC_TYPES = {
    "खरेदीखत": "conveyance",
    "करारनामा": "agreement_for_sale",
    "विक्री करार": "agreement_for_sale",
    "बक्षीसपत्र": "gift",
    "गहाणखत": "mortgage",
    "भाडेपट्टा": "lease",
    "भाडेकरार": "leave_and_licence",
}

DISTRICTS = {"पुणे": "Pune", "ठाणे": "Thane"}

# --------------------------------------------------------------------------- property-description terms
TERMS = {
    "सदनिका": "flat",
    "मजला": "floor",
    "कार्पेट क्षेत्र": "carpet area",
    "बिल्ट अप क्षेत्र": "built-up area",
    "चौ.मी.": "sq m",
    "चौ.फूट": "sq ft",
    "कार पार्किंग": "car parking",
    "पार्किंग": "parking",
    "तळमजला": "ground floor",
    "इमारत": "building",
    "प्रवर्तक": "promoter",
    "प्रथम विक्री": "first sale",
    "पालिकेचे नाव": "local body",
    "म.न.पा.": "Municipal Corporation",
    "महानगरपालिका": "Municipal Corporation",
    "ग्रामपंचायत": "Gram Panchayat",
    "इतर माहिती": "other details",
    "गाव": "village",
    "नं.": "no.",
}

SRO_NAMES = {"हवेली": "Haveli", "मुळशी": "Mulshi", "खेड": "Khed", "ठाणे": "Thane",
             "कल्याण": "Kalyan", "उल्हासनगर": "Ulhasnagar", "भिवंडी": "Bhiwandi",
             "मावळ": "Maval", "अंबरनाथ": "Ambernath", "मीरा भाईंदर": "Mira Bhayandar"}

# --------------------------------------------------------------------------- localities (extend as data arrives)
LOCALITIES = {
    # Pune district
    "बाणेर": "Baner", "वाकड": "Wakad", "हिंजवडी": "Hinjewadi", "खराडी": "Kharadi",
    "हडपसर": "Hadapsar", "वाघोली": "Wagholi", "कोथरूड": "Kothrud", "औंध": "Aundh",
    "विमाननगर": "Viman Nagar", "उंड्री": "Undri", "पिंपळे सौदागर": "Pimple Saudagar",
    "रावेत": "Ravet", "मोशी": "Moshi", "धानोरी": "Dhanori", "बावधन": "Bavdhan",
    "सूस": "Sus", "ताथवडे": "Tathawade", "पुनावळे": "Punawale", "कोंढवा": "Kondhwa",
    "चाकण": "Chakan",
    # Thane district
    "माजिवडे": "Majiwada", "कोलशेत": "Kolshet", "बाळकुम": "Balkum",
    "कासारवडवली": "Kasarvadavali", "वाघबीळ": "Waghbil", "कळवा": "Kalwa",
    "डोंबिवली": "Dombivli", "कल्याण": "Kalyan", "मीरा रोड": "Mira Road",
    "भिवंडी": "Bhiwandi", "अंबरनाथ": "Ambernath", "बदलापूर": "Badlapur",
    "उल्हासनगर": "Ulhasnagar", "घोडबंदर": "Ghodbunder", "पाचपाखाडी": "Panchpakhadi",
    "वर्तकनगर": "Vartak Nagar", "मानपाडा": "Manpada", "ओवळा": "Owale",
    "टिटवाळा": "Titwala", "शीळ": "Shil",
}


def translate_term(value: str, table: dict[str, str]) -> str | None:
    """Exact glossary lookup after whitespace normalisation."""
    if not isinstance(value, str):
        return None
    return table.get(re.sub(r"\s+", " ", value).strip())


def translate_description(text: str) -> str:
    """Replace known Marathi terms inside free text and convert numerals.
    Longest terms first so 'कार पार्किंग' wins over 'पार्किंग'."""
    if not isinstance(text, str):
        return text
    out = to_arabic_digits(text)
    glossary = {**LOCALITIES, **TERMS}
    for mr in sorted(glossary, key=len, reverse=True):
        out = out.replace(mr, glossary[mr])
    out = re.sub(r"(\d+)\s*(?:वा|वे|था|ला|रा)\s+floor",
                 lambda m: f"{_ordinal(int(m.group(1)))} floor", out)          # ordinals
    return out


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def translate_sro(name_mr: str) -> str:
    """'हवेली 11' -> 'Haveli 11'."""
    if not isinstance(name_mr, str):
        return name_mr
    out = to_arabic_digits(name_mr)
    for mr, en in SRO_NAMES.items():
        out = out.replace(mr, en)
    return out.strip()


def transliterate_place(name_mr: str) -> str:
    """Glossary first, else IAST transliteration with simple schwa deletion."""
    hit = translate_term(name_mr, LOCALITIES)
    if hit:
        return hit
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        latin = transliterate(name_mr, sanscript.DEVANAGARI, sanscript.HK)
        latin = re.sub(r"a\b", "", latin)            # drop word-final inherent 'a'
        return latin.title()
    except Exception:                               # library absent -> keep original
        return name_mr


def machine_translate(text: str, enabled: bool = False) -> str:
    """Optional online translation for residual free text (Colab only).
    Disabled by default to keep the pipeline offline and reproducible."""
    if not enabled or not isinstance(text, str):
        return text
    from deep_translator import GoogleTranslator    # pip install deep-translator
    return GoogleTranslator(source="mr", target="en").translate(text)
