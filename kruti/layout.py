"""Gatha Lines: read each page as lines with their position on the page.

Feature 1 (kruti/extract.py) keeps only the text of a page. Telling a gatha from prose,
and finding where an unnumbered gatha ends, needs the layout too: how wide each line is,
where it starts, and the gap above it. Pages come from the PDF's text layer when it is
usable (same rule as feature 1), otherwise from Tesseract. Every finished page is appended
to this feature's own cache, so a cancelled run resumes where it stopped; feature 1's
cache is never touched.
"""
import hashlib
import io
import json
import logging
import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

import pymupdf

from .extract import _share_cores, _text_layer_is_usable

log = logging.getLogger(__name__)
LAYOUT_CACHE_VERSION = 1


@dataclass
class Line:
    text: str
    x0: float           # page units (PDF points), origin top-left
    y0: float
    x1: float
    y1: float
    conf: float         # 0-100; 100 for a text layer
    block: int = 0
    par: int = 0


@dataclass
class PageLayout:
    page: int           # 1-based PDF page
    source: str         # "text" or "ocr"
    confidence: float
    width: float
    height: float
    lines: list = field(default_factory=list)


# ---------------------------------------------------------------- line builders
def lines_from_tesseract(data: dict, scale: float) -> list:
    """Words from pytesseract.image_to_data(..., output_type=DICT), grouped by
    (block, paragraph, line). Pixel boxes are divided by scale (dpi / 72) into points."""
    groups = {}
    for i, word in enumerate(data["text"]):
        if not str(word).strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        groups.setdefault(key, []).append(i)
    lines = []
    for (block, par, _), idx in sorted(groups.items()):
        confs = [float(data["conf"][i]) for i in idx if float(data["conf"][i]) >= 0]
        lines.append(Line(
            " ".join(str(data["text"][i]).strip() for i in idx),
            min(data["left"][i] for i in idx) / scale,
            min(data["top"][i] for i in idx) / scale,
            max(data["left"][i] + data["width"][i] for i in idx) / scale,
            max(data["top"][i] + data["height"][i] for i in idx) / scale,
            round(sum(confs) / len(confs), 1) if confs else 0.0, block, par))
    return lines


def lines_from_text_dict(d: dict) -> list:
    """Lines of a PyMuPDF page.get_text("dict") structure."""
    lines = []
    for b, block in enumerate(d.get("blocks", [])):
        if block.get("type", 0) != 0:
            continue                                   # an image block
        for ln in block.get("lines", []):
            text = "".join(s.get("text", "") for s in ln.get("spans", []))
            text = " ".join(text.split())
            if text:
                x0, y0, x1, y1 = ln["bbox"]
                lines.append(Line(text, x0, y0, x1, y1, 100.0, b, 0))
    return lines


# ---------------------------------------------------------------- reading order
def _same_row(a: Line, b: Line) -> bool:
    overlap = min(a.y1, b.y1) - max(a.y0, b.y0)
    return overlap > 0.5 * min(a.y1 - a.y0, b.y1 - b.y0)


def _merge_row(parts: list) -> Line:
    parts = sorted(parts, key=lambda ln: ln.x0)
    confs = [p.conf for p in parts]
    return Line(" ".join(p.text for p in parts), min(p.x0 for p in parts),
                min(p.y0 for p in parts), max(p.x1 for p in parts), max(p.y1 for p in parts),
                round(sum(confs) / len(confs), 1), parts[0].block, parts[0].par)


def _merge_rows(lines: list) -> list:
    """Fragments of one printed row (two halves of a gatha, an OCR line broken in two)
    become one line: the spec counts one printed row as one line."""
    rows = []
    for ln in sorted(lines, key=lambda ln: (ln.y0, ln.x0)):
        for row in rows:
            if _same_row(row[-1], ln) and all(ln.x0 >= p.x1 - 2 or ln.x1 <= p.x0 + 2 for p in row):
                row.append(ln)
                break
        else:
            rows.append([ln])
    return sorted((_merge_row(r) for r in rows), key=lambda ln: ln.y0)


def _gutter(lines: list, width: float):
    """x of an empty vertical band in the middle of the page, or None."""
    lo, hi = 0.3 * width, 0.7 * width
    step = width / 200
    best, run, start = None, 0, None
    x = lo
    while x <= hi:
        free = not any(ln.x0 < x < ln.x1 for ln in lines)
        if free:
            start = x if start is None else start
            run += 1
            if run * step >= 0.03 * width and (best is None or run > best[1]):
                best = (start, run)
        else:
            run, start = 0, None
        x += step
    return None if best is None else best[0] + best[1] * step / 2


def _is_columns(lines: list, width: float):
    """Two columns of text, read one after the other - not the two halves of each gatha
    printed side by side, which are one row each."""
    narrow = [ln for ln in lines if ln.x1 - ln.x0 < 0.5 * width]
    if len(narrow) < 6:
        return None
    g = _gutter(narrow, width)
    if g is None:
        return None
    left = [ln for ln in narrow if ln.x1 <= g]
    right = [ln for ln in narrow if ln.x0 >= g]
    if len(left) < 3 or len(right) < 3:
        return None
    if {ln.block for ln in left} & {ln.block for ln in right}:
        return None                       # one text block across the gutter: halves of rows
    paired = sum(any(_same_row(r, lft) for lft in left) for r in right) / len(right)
    left_ends = sum(ln.text.rstrip().endswith("॥") for ln in left) / len(left)
    if paired >= 0.6 and left_ends < 0.2:
        return None                       # "first half, | second half ॥1॥" on every row
    return g


def order_lines(lines: list, width: float) -> list:
    """Lines in reading order. In a two-column stretch the left column is read before
    the right; a line crossing the gutter (a heading) separates such stretches."""
    if not lines:
        return []
    g = _is_columns(lines, width)
    if g is None:
        return _merge_rows(lines)
    out, band = [], []

    def flush():
        out.extend(_merge_rows([ln for ln in band if ln.x1 <= g]))
        out.extend(_merge_rows([ln for ln in band if ln.x0 >= g]))
        band.clear()

    for ln in sorted(lines, key=lambda ln: ln.y0):
        if ln.x0 < g < ln.x1:
            flush()
            out.append(ln)
        else:
            band.append(ln)
    flush()
    return out


# ---------------------------------------------------------------- cache
def _cache_path(pdf_path: str, cfg) -> str:
    st = os.stat(pdf_path)
    ident = f"{os.path.abspath(pdf_path)}|{st.st_size}|{int(st.st_mtime)}|" \
            f"{cfg['tesseract_langs']}|{cfg['ocr_dpi']}|{cfg['force_ocr']}|layout{LAYOUT_CACHE_VERSION}"
    digest = hashlib.sha1(ident.encode()).hexdigest()[:16]
    os.makedirs(cfg["layout_cache_dir"], exist_ok=True)
    return os.path.join(cfg["layout_cache_dir"], f"{digest}.jsonl")


def _from_json(row: dict) -> PageLayout:
    p = PageLayout(**{k: v for k, v in row.items() if k != "lines"})
    p.lines = [Line(**ln) for ln in row["lines"]]
    return p


def _read_cache(path: str, page_count: int) -> dict:
    done = {}
    if not os.path.exists(path):
        return done
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                p = _from_json(json.loads(line))
            except (ValueError, TypeError, KeyError):
                continue          # a half-written last line after a crash
            if 1 <= p.page <= page_count:
                done[p.page] = p
    return done


# ---------------------------------------------------------------- reading
def _ocr(png: bytes, page_no: int, width: float, height: float, cfg) -> PageLayout:
    import pytesseract
    from PIL import Image
    try:
        data = pytesseract.image_to_data(Image.open(io.BytesIO(png)), lang=cfg["tesseract_langs"],
                                         output_type=pytesseract.Output.DICT)
        lines = lines_from_tesseract(data, cfg["ocr_dpi"] / 72)
        confs = [float(c) for c, t in zip(data["conf"], data["text"])
                 if float(c) >= 0 and str(t).strip()]
        conf = sum(confs) / len(confs) if confs else 0.0
    except Exception as e:  # noqa: BLE001 - one bad page must not stop a book
        log.warning("OCR failed on page %d: %s", page_no, e)
        lines, conf = [], 0.0
    return PageLayout(page_no, "ocr", round(conf, 1), width, height,
                      order_lines(lines, width))


def read_layout(pdf_path: str, cfg, on_page=None, checkpoint=None, only=None) -> list:
    """PageLayout for every page (or only the PDF pages in `only`). on_page(done, total,
    source) after each page; checkpoint() between pages may block (pause) or raise
    (cancel)."""
    checkpoint = checkpoint or (lambda: None)
    cache_file = _cache_path(pdf_path, cfg)
    workers = max(1, int(cfg["ocr_workers"]))
    _share_cores(workers)
    force_ocr = cfg.get("force_ocr", False)

    with pymupdf.open(pdf_path) as doc:
        total = doc.page_count
        wanted = sorted(n for n in (only or range(1, total + 1)) if 1 <= n <= total)
        done = {n: p for n, p in _read_cache(cache_file, total).items() if n in set(wanted)}
        total = len(wanted)
        if on_page and done:
            on_page(len(done), total, "cache")
        todo = [n - 1 for n in wanted if n not in done]
        if not todo:
            return [done[i] for i in sorted(done)]
        pool = ThreadPoolExecutor(max_workers=workers)
        pending = deque()
        try:
            with open(cache_file, "a", encoding="utf-8") as cache:
                def record(p):
                    done[p.page] = p
                    cache.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")
                    cache.flush()
                    if on_page:
                        on_page(len(done), total, p.source)

                for i in todo:
                    checkpoint()
                    page = doc[i]
                    w, h = page.rect.width, page.rect.height
                    text = "" if force_ocr else page.get_text()
                    if not force_ocr and _text_layer_is_usable(text, cfg):
                        lines = lines_from_text_dict(page.get_text("dict"))
                        record(PageLayout(i + 1, "text", 100.0, w, h, order_lines(lines, w)))
                    elif not text.strip() and not page.get_images() and not page.get_drawings():
                        record(PageLayout(i + 1, "text", 100.0, w, h, []))
                    else:
                        png = page.get_pixmap(dpi=cfg["ocr_dpi"]).tobytes("png")
                        pending.append(pool.submit(_ocr, png, i + 1, w, h, cfg))
                    while pending and (pending[0].done() or len(pending) >= workers * 2):
                        record(pending.popleft().result())
                while pending:
                    checkpoint()
                    record(pending.popleft().result())
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
    return [done[i] for i in sorted(done)]
