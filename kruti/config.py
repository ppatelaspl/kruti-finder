"""Default settings. config.yaml (CLI) or the app's Advanced panel override these."""
import os

DEFAULTS = {
    # Excel input
    "excel_sheet": 0,
    "excel_columns": {"kruti_no": "कृति क्र.", "name": "कृति परि. नाम",
                      "aadi": "आदिवाक्य", "ant": "अंत वा."},
    # Text extraction / OCR
    "min_text_chars": 30,
    "min_indic_ratio": 0.6,
    "max_broken_ratio": 0.02,
    "force_ocr": False,
    "ocr_engine": "tesseract",
    "tesseract_langs": "hin+guj+san",
    "tesseract_cmd": "",
    "google_language_hints": ["hi", "gu", "sa"],
    "ocr_dpi": 300,
    "ocr_workers": max(1, min(4, (os.cpu_count() or 2) - 1)),
    "low_ocr_confidence": 70,
    "cache_dir": ".kruti_cache",
    # Matching Kruti from the books to the Excel
    "found_threshold": 85,
    "min_candidate_score": 65,
    "query_max_chars": 160,
    "max_kruti_pages": 40,
    # Kruti detection
    "min_verses": 2,
    "max_opening_chars": 600,
    "title_keywords": ["स्तवन", "सज्झाय", "स्वाध्याय", "स्तुति", "थोय", "थुई", "चैत्यवंदन", "गीत",
                       "पद", "लावणी", "छंद", "रास", "स्तोत्र", "स्तव", "गहूंली", "गहुंली", "भास",
                       "चोवीसी", "बावनी", "छत्तीसी", "बत्तीसी", "पच्चीसी", "अष्टक", "सूत्र", "आरती",
                       "पूजा", "विनती", "प्रभाती", "सवैया", "कवित्त", "हरियाली", "फेरी", "भगवान"],
    # parts inside one Kruti (a sajjhay/ras in several dhals, with dohas and a kalash):
    # their verse numbers restart, but they do not start a new Kruti
    "section_keywords": ["ढाल", "ढाळ", "दुहा", "दूहा", "दुहो", "दूहो", "दोहा", "दोहरा", "कलश", "सोरठा",
                         "सोरठो", "चोपाई", "चौपाई",
                         # frequent OCR misreadings of ढाल / दुहा (only on heading-shaped lines)
                         "हाल", "हाळ", "टाल", "टाळ", "टाई", "डाल", "डाळ", "डुहा", "डूहा"],
    "name_match_threshold": 85,
    "max_kruti_pages_check": 8,
    "live_count_seconds": 10,       # how often "Kruti found" is refreshed while reading     # a Kruti longer than this is flagged for review
    "duplicate_threshold": 88,
}


def merged(overrides: dict | None) -> dict:
    cfg = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
           for k, v in DEFAULTS.items()}
    for k, v in (overrides or {}).items():
        if v is not None:
            cfg[k] = v
    return cfg
