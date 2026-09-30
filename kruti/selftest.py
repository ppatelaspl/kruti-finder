"""Build check: verifies the packaged app can import its engine and OCR Devanagari.

    KrutiFinder --selftest result.json [sample.png]
"""
import json
import sys
import traceback


def run_selftest(out_path, sample_png=None):
    report = {"ok": False}
    try:
        import openpyxl, pymupdf, rapidfuzz  # noqa: F401,E401 - import check
        from .config import merged
        from .ocr_setup import configure_ocr
        report["python"] = sys.version.split()[0]
        report["ocr"] = configure_ocr(merged(None))
        report["ok"] = report["ocr"]["ok"]
        if sample_png and report["ok"]:
            from PIL import Image
            import pytesseract
            text = pytesseract.image_to_string(Image.open(sample_png), lang="hin+guj+san")
            report["sample_text"] = text.strip()
            report["ok"] = "जिनवर" in text
    except Exception:  # noqa: BLE001
        report["ok"] = False          # any failure, e.g. Tesseract unable to read the image
        report["error"] = traceback.format_exc()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return 0 if report["ok"] else 1
