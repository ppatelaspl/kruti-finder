"""Extract page text from PDFs.

Each page is first read from its text layer. If that layer is missing or looks like a
legacy (non-Unicode) Indic font - which copies out as Latin garbage - the page is OCR'd.
Pages are processed one at a time; OCR runs on a small thread pool (Tesseract is a
separate process, so threads are enough and keep memory flat). Every finished page is
appended to a per-book cache, so a cancelled or crashed run resumes where it stopped.
"""
import hashlib
import io
import json
import logging
import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict

import pymupdf

log = logging.getLogger(__name__)
CACHE_VERSION = 3


@dataclass
class PageText:
    page: int            # 1-based page number as printed by the PDF viewer
    source: str          # "text" or "ocr"
    confidence: float    # OCR mean word confidence (0-100); 100 for a good text layer
    text: str


def _indic_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    indic = sum(1 for c in letters if 0x0900 <= ord(c) <= 0x0AFF)
    return indic / len(letters)


def _broken_ratio(text: str) -> float:
    """Share of letters that are Latin-extended / private-use glyph codes. These appear
    when a PDF's text layer was built from glyphs instead of Unicode (broken conjuncts
    and matras), so the page looks right but copies out wrong."""
    def is_bad(c):
        cp = ord(c)
        return (0x00C0 <= cp <= 0x02FF or 0xE000 <= cp <= 0xF8FF or cp == 0xFFFD
                or (cp < 32 and c not in "\n\t\r"))
    letters = [c for c in text if c.isalpha() or is_bad(c)]
    if not letters:
        return 1.0
    bad = sum(1 for c in letters if is_bad(c))
    return bad / len(letters)


def _text_layer_is_usable(text: str, cfg) -> bool:
    return (len(text.strip()) >= cfg["min_text_chars"]
            and _indic_ratio(text) >= cfg["min_indic_ratio"]
            and _broken_ratio(text) <= cfg["max_broken_ratio"])


# ---------------------------------------------------------------- OCR engines
def _ocr_tesseract(png_bytes: bytes, cfg) -> tuple:
    import pytesseract
    from PIL import Image

    data = pytesseract.image_to_data(
        Image.open(io.BytesIO(png_bytes)), lang=cfg["tesseract_langs"],
        output_type=pytesseract.Output.DICT)
    lines, confs = {}, []
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        conf = float(data["conf"][i])
        if conf >= 0:
            confs.append(conf)
    text = "\n".join(" ".join(ws) for _, ws in sorted(lines.items()))
    return text, (sum(confs) / len(confs) if confs else 0.0)


def _ocr_google_vision(png_bytes: bytes, cfg) -> tuple:
    """Optional engine. Needs `pip install google-cloud-vision` and
    GOOGLE_APPLICATION_CREDENTIALS pointing to a service-account key."""
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()
    resp = client.document_text_detection(
        image=vision.Image(content=png_bytes),
        image_context={"language_hints": cfg.get("google_language_hints", ["hi", "gu", "sa"])})
    if resp.error.message:
        raise RuntimeError(resp.error.message)
    ann = resp.full_text_annotation
    confs = [p.confidence * 100 for pg in ann.pages for b in pg.blocks for p in b.paragraphs]
    return ann.text, (sum(confs) / len(confs) if confs else 0.0)


_ENGINES = {"tesseract": _ocr_tesseract, "google_vision": _ocr_google_vision}


def _ocr_png(png: bytes, page_no: int, cfg) -> PageText:
    try:
        text, conf = _ENGINES[cfg["ocr_engine"]](png, cfg)
    except Exception as e:  # noqa: BLE001 - one bad page must not stop a book
        log.warning("OCR failed on page %d: %s", page_no, e)
        text, conf = "", 0.0
    return PageText(page_no, "ocr", round(conf, 1), text)


# ---------------------------------------------------------------- cache
def _cache_path(pdf_path: str, cfg) -> str:
    st = os.stat(pdf_path)
    ident = f"{os.path.abspath(pdf_path)}|{st.st_size}|{int(st.st_mtime)}|" \
            f"{cfg['ocr_engine']}|{cfg['tesseract_langs']}|{cfg['ocr_dpi']}|" \
            f"{cfg['force_ocr']}|{CACHE_VERSION}"
    digest = hashlib.sha1(ident.encode()).hexdigest()[:16]
    os.makedirs(cfg["cache_dir"], exist_ok=True)
    return os.path.join(cfg["cache_dir"], f"{digest}.jsonl")


def _read_cache(path: str, page_count: int) -> dict:
    done = {}
    if not os.path.exists(path):
        return done
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                p = PageText(**json.loads(line))
            except (ValueError, TypeError):
                continue          # a half-written last line after a crash
            if 1 <= p.page <= page_count:
                done[p.page] = p
    return done


def page_count(pdf_path: str) -> int:
    try:
        with pymupdf.open(pdf_path) as doc:
            return doc.page_count
    except Exception:  # noqa: BLE001 - unreadable files are reported later
        return 0


def extract_book(pdf_path: str, cfg, on_page=None, checkpoint=None) -> list:
    """Return PageText for every page of the book.

    on_page(done, total, source) is called after each page; checkpoint() is called between
    pages and may block (pause) or raise (cancel)."""
    checkpoint = checkpoint or (lambda: None)
    cache_file = _cache_path(pdf_path, cfg)
    workers = max(1, int(cfg["ocr_workers"]))
    force_ocr = cfg.get("force_ocr", False)

    with pymupdf.open(pdf_path) as doc:
        total = doc.page_count
        done = _read_cache(cache_file, total)
        if on_page and done:
            on_page(len(done), total, "cache")
        todo = [i for i in range(total) if i + 1 not in done]
        if not todo:
            return [done[i] for i in sorted(done)]

        pool = ThreadPoolExecutor(max_workers=workers)
        pending = deque()
        try:
            with open(cache_file, "a", encoding="utf-8") as cache:
                def record(pt):
                    done[pt.page] = pt
                    cache.write(json.dumps(asdict(pt), ensure_ascii=False) + "\n")
                    cache.flush()
                    if on_page:
                        on_page(len(done), total, pt.source)

                for i in todo:
                    checkpoint()
                    page = doc[i]
                    text = "" if force_ocr else page.get_text()
                    if not force_ocr and _text_layer_is_usable(text, cfg):
                        record(PageText(i + 1, "text", 100.0, text))
                    elif not text.strip() and not page.get_images() and not page.get_drawings():
                        record(PageText(i + 1, "text", 100.0, ""))   # truly blank page
                    else:
                        png = page.get_pixmap(dpi=cfg["ocr_dpi"]).tobytes("png")
                        pending.append(pool.submit(_ocr_png, png, i + 1, cfg))
                    # keep only a few rendered pages in memory
                    while pending and (pending[0].done() or len(pending) >= workers * 2):
                        record(pending.popleft().result())
                while pending:
                    checkpoint()
                    record(pending.popleft().result())
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
    return [done[i] for i in sorted(done)]
