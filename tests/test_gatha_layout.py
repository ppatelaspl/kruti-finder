"""Gatha Lines: reading pages as positioned lines.   Run:  python -m pytest tests"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kruti.layout import (Line, _read_cache, lines_from_tesseract,  # noqa: E402
                          lines_from_text_dict, order_lines)


def _tess(words):
    """words: (text, left, top, width, height, conf, block, par, line)"""
    keys = ("text", "left", "top", "width", "height", "conf", "block_num", "par_num", "line_num")
    return {k: [w[i] for w in words] for i, k in enumerate(keys)}


def test_tesseract_words_grouped_into_lines():
    data = _tess([("शांति", 100, 100, 80, 30, 90, 1, 1, 1),
                  ("जिनेसर", 200, 102, 100, 30, 80, 1, 1, 1),
                  ("", 0, 0, 0, 0, -1, 1, 1, 1),
                  ("सोलमा", 100, 160, 90, 30, 70, 1, 1, 2)])
    lines = lines_from_tesseract(data, scale=2.0)
    assert [ln.text for ln in lines] == ["शांति जिनेसर", "सोलमा"]
    first = lines[0]
    assert (first.x0, first.y0, first.x1, first.y1) == (50, 50, 150, 66)
    assert first.conf == 85
    assert (first.block, first.par) == (1, 1)


def test_text_dict_spans_joined_per_line():
    d = {"blocks": [{"type": 0, "lines": [
        {"bbox": (10, 20, 200, 35), "spans": [{"text": "ऋषभ "}, {"text": "जिनेसर"}]},
        {"bbox": (10, 40, 150, 55), "spans": [{"text": "प्रीतम"}]}]},
        {"type": 1}]}
    lines = lines_from_text_dict(d)
    assert [ln.text for ln in lines] == ["ऋषभ जिनेसर", "प्रीतम"]
    assert all(ln.conf == 100 for ln in lines)
    assert (lines[0].x0, lines[0].y1) == (10, 35)


def test_same_row_fragments_merged():
    a = Line("पहलो भाग,", 50, 100, 250, 120, 90)
    b = Line("बीजो भाग ॥1॥", 300, 102, 500, 121, 80)
    c = Line("आगली ओळ", 50, 140, 250, 160, 90)
    out = order_lines([b, c, a], width=600)
    assert [ln.text for ln in out] == ["पहलो भाग, बीजो भाग ॥1॥", "आगली ओळ"]
    assert (out[0].x0, out[0].x1, out[0].conf) == (50, 500, 85)


def test_two_columns_read_in_column_order():
    """Separate text blocks on each side of an empty gutter, and gathas ending (॥) in
    the left column: two columns, not the halves of each row."""
    left = [f"डावी {i}" + (" ॥" if i % 2 else ",") for i in range(4)]
    right = [f"जमणी {i}" + (" ॥" if i % 2 else ",") for i in range(4)]
    lines = []
    for i in range(4):
        y = 100 + 40 * i
        lines.append(Line(left[i], 50, y, 250, y + 20, 90, block=1))
        lines.append(Line(right[i], 360, y + 5, 560, y + 25, 90, block=2))
    out = order_lines(lines, width=600)
    assert [ln.text for ln in out] == left + right


def test_side_by_side_halves_are_rows():
    """Every row: "first half," on the left, "second half ॥n॥" on the right."""
    lines = []
    for i in range(4):
        y = 100 + 40 * i
        lines.append(Line(f"पहलो {i},", 50, y, 250, y + 20, 90, block=1))
        lines.append(Line(f"बीजो {i} ॥{i + 1}॥", 360, y, 560, y + 20, 90, block=2))
    out = order_lines(lines, width=600)
    assert [ln.text for ln in out] == [f"पहलो {i}, बीजो {i} ॥{i + 1}॥" for i in range(4)]


def test_full_width_line_keeps_single_column():
    lines = [Line("शीर्षक आखी पहोळाईमां छापेलुं छे", 50, 60, 560, 80, 90),
             Line("डावी", 50, 100, 250, 120, 90), Line("जमणी", 360, 140, 560, 160, 90)]
    out = order_lines(lines, width=600)
    assert [ln.text for ln in out] == ["शीर्षक आखी पहोळाईमां छापेलुं छे", "डावी", "जमणी"]


def test_cache_ignores_torn_last_line(tmp_path):
    p = tmp_path / "c.jsonl"
    rows = [{"page": n, "source": "text", "confidence": 100.0, "width": 600, "height": 800,
             "lines": [{"text": "क", "x0": 1, "y0": 2, "x1": 3, "y1": 4, "conf": 100,
                        "block": 0, "par": 0}]} for n in (1, 2)]
    p.write_text("\n".join(json.dumps(r) for r in rows) + '\n{"page": 3, "sou', encoding="utf-8")
    done = _read_cache(str(p), page_count=5)
    assert sorted(done) == [1, 2]
    assert done[1].lines[0].text == "क"


def test_read_layout_only_some_pages(tmp_path):
    import pymupdf
    from kruti.gatha_lines import gatha_config
    from kruti.layout import read_layout
    pdf = tmp_path / "b.pdf"
    doc = pymupdf.open()
    for i in range(5):
        doc.new_page().insert_text((72, 72), f"page {i + 1}")
    doc.save(pdf)
    cfg = gatha_config({"layout_cache_dir": str(tmp_path / "cache"), "min_indic_ratio": 0.0, "min_text_chars": 1})
    got = read_layout(str(pdf), cfg, only={2, 4})
    assert [p.page for p in got] == [2, 4]
    assert [ln.text for ln in got[0].lines] == ["page 2"]
    assert [p.page for p in read_layout(str(pdf), cfg)] == [1, 2, 3, 4, 5]


def test_failed_ocr_page_is_not_cached(tmp_path, monkeypatch):
    import pymupdf
    import pytesseract
    from kruti.gatha_lines import gatha_config
    from kruti.layout import read_layout
    pdf = tmp_path / "scan.pdf"
    doc = pymupdf.open()
    doc.new_page().draw_rect(pymupdf.Rect(50, 50, 200, 200))     # no text: goes to OCR
    doc.save(pdf)
    cfg = gatha_config({"layout_cache_dir": str(tmp_path / "cache"), "force_ocr": True})

    def broken(*a, **k):
        raise pytesseract.TesseractNotFoundError()
    monkeypatch.setattr(pytesseract, "image_to_data", broken)
    assert read_layout(str(pdf), cfg)[0].lines == []

    calls = []

    def works(*a, **k):
        calls.append(1)
        return {"text": ["नमो"], "conf": [90], "left": [10], "top": [10], "width": [50],
                "height": [20], "block_num": [1], "par_num": [1], "line_num": [1]}
    monkeypatch.setattr(pytesseract, "image_to_data", works)
    assert [ln.text for ln in read_layout(str(pdf), cfg)[0].lines] == ["नमो"]
    assert calls                     # the page was OCR'd again, not read empty from the cache


# --- two book pages printed side by side on one PDF page (round 4) ---
def _spread_pdf(path):
    import pymupdf
    doc = pymupdf.open()
    pg = doc.new_page(width=792, height=612)
    for i in range(6):
        pg.insert_text((60, 80 + 30 * i), f"left line {i + 1}")
        pg.insert_text((460, 80 + 30 * i), f"right line {i + 1}")
    doc.save(path)


def test_text_layer_spread_reads_left_page_then_right_page(tmp_path):
    from kruti.gatha_lines import gatha_config
    from kruti.layout import read_layout
    pdf = tmp_path / "spread.pdf"
    _spread_pdf(pdf)
    cfg = gatha_config({"layout_cache_dir": str(tmp_path / "c"), "min_indic_ratio": 0.0, "min_text_chars": 1})
    p = read_layout(str(pdf), cfg)[0]
    assert [ln.text for ln in p.lines] == [f"left line {i}" for i in range(1, 7)] + \
        [f"right line {i}" for i in range(1, 7)]
    assert p.width < 450 and all(ln.x1 <= p.width for ln in p.lines)   # one book page wide


def test_ocr_spread_is_read_as_two_halves(monkeypatch):
    """Tesseract joins the two pages' rows; each half is OCR'd on its own instead."""
    import io
    import pytesseract
    from PIL import Image, ImageDraw
    from kruti.gatha_lines import gatha_config
    from kruti.layout import _ocr
    img = Image.new("L", (1100, 850), 255)
    d = ImageDraw.Draw(img)
    for i in range(6):
        d.rectangle((80, 100 + 60 * i, 480, 130 + 60 * i), fill=0)
        d.rectangle((620, 100 + 60 * i, 1020, 130 + 60 * i), fill=0)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    widths = []

    def fake(im, **k):
        widths.append(im.size[0])
        return {"text": ["नमो"], "conf": [90], "left": [40], "top": [100], "width": [300],
                "height": [30], "block_num": [1], "par_num": [1], "line_num": [1]}
    monkeypatch.setattr(pytesseract, "image_to_data", fake)
    cfg = gatha_config({"ocr_dpi": 100})
    p = _ocr(buf.getvalue(), 1, 792, 612, cfg)
    assert len(widths) == 2 and max(widths) < 700
    assert len(p.lines) == 2 and p.width < 450


def test_landscape_page_with_text_across_the_middle_is_not_split(tmp_path):
    import pymupdf
    from kruti.gatha_lines import gatha_config
    from kruti.layout import read_layout
    pdf = tmp_path / "wide.pdf"
    doc = pymupdf.open()
    pg = doc.new_page(width=792, height=612)
    for i in range(6):
        pg.insert_text((60, 80 + 30 * i), f"one long line across the whole landscape page number {i + 1} end")
    doc.save(pdf)
    cfg = gatha_config({"layout_cache_dir": str(tmp_path / "c"), "min_indic_ratio": 0.0, "min_text_chars": 1})
    p = read_layout(str(pdf), cfg)[0]
    assert p.width == 792 and len(p.lines) == 6
