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
