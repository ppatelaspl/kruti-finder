"""Download the OCR language models bundled with the app (tessdata_best: most accurate)."""
import urllib.request
from pathlib import Path

LANGS = ("hin", "guj", "san")
BASE = "https://github.com/tesseract-ocr/tessdata_best/raw/main/{}.traineddata"
OUT = Path(__file__).resolve().parent.parent / "vendor" / "tessdata"


def main():
    (OUT / "configs").mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        target = OUT / f"{lang}.traineddata"
        if not target.exists():
            print("downloading", lang)
            urllib.request.urlretrieve(BASE.format(lang), target)
    # pytesseract.image_to_data() asks Tesseract for the 'tsv' config
    (OUT / "configs" / "tsv").write_text("tessedit_create_tsv 1\n")
    (OUT / "configs" / "txt").write_text("tessedit_create_txt 1\n")
    print("tessdata ready in", OUT)


if __name__ == "__main__":
    main()
