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
    # Matching
    "found_threshold": 85,
    "min_candidate_score": 65,
    "query_max_chars": 160,
    "max_kruti_pages": 40,
    # New-Kruti detection
    "gap_min_verses": 2,
    "gap_max_verse_chars": 600,
    "title_keywords": ["स्तवन", "सज्झाय", "स्तुति", "थोय", "चैत्यवंदन", "गीत", "पद", "लावणी",
                       "छंद", "ढाल", "ढाळ", "रास", "कलश", "स्तोत्र", "गहूंली", "भास",
                       "चोवीसी", "बावनी"],
    "duplicate_threshold": 88,
}


def merged(overrides: dict | None) -> dict:
    cfg = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
           for k, v in DEFAULTS.items()}
    for k, v in (overrides or {}).items():
        if v is not None:
            cfg[k] = v
    return cfg
