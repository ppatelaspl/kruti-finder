"""Download the OCR language models bundled with the app.

tessdata_best is the most accurate. On Linux the app also carries tessdata_fast: the
Tesseract 4.x of Ubuntu 20.04/22.04 runs the best models about 2.5x slower than the fast
ones (and no more accurately), so the app switches to them there.
"""
import sys
import urllib.request
from pathlib import Path

LANGS = ("hin", "guj", "san")
URL = "https://github.com/tesseract-ocr/{}/raw/main/{}.traineddata"
VENDOR = Path(__file__).resolve().parent.parent / "vendor"


def fetch(repo, out):
    (out / "configs").mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        target = out / f"{lang}.traineddata"
        if not target.exists():
            print("downloading", repo, lang)
            urllib.request.urlretrieve(URL.format(repo, lang), target)
    # pytesseract.image_to_data() asks Tesseract for the 'tsv' config
    (out / "configs" / "tsv").write_text("tessedit_create_tsv 1\n")
    (out / "configs" / "txt").write_text("tessedit_create_txt 1\n")
    print("models ready in", out)


def main():
    fetch("tessdata_best", VENDOR / "tessdata")
    if sys.platform.startswith("linux"):
        fetch("tessdata_fast", VENDOR / "tessdata_fast")


if __name__ == "__main__":
    main()
