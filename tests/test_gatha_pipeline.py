"""Gatha Lines: a whole run.   Run:  python -m pytest tests"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook                        # noqa: E402

import kruti.gatha_pipeline as gp                         # noqa: E402
from kruti.gatha_lines import gatha_config                # noqa: E402
from kruti.layout import Line, PageLayout                 # noqa: E402
from kruti.pipeline import Cancelled, Controller          # noqa: E402


def _page(no, rows):
    lines, y = [], 40
    for text, x0, x1 in rows:
        lines.append(Line(text, x0, y, x1, y + 14, 90))
        y += 18
    return PageLayout(no, "ocr", 90, 420, 600, lines)


def _kruti(title, n):
    rows = [(title, 150, 280)]
    for i in range(1, n + 1):
        rows += [(f"{title} गाथा {i} पहली पंक्ति,", 100, 260), (f"{title} गाथा {i} बीजी पंक्ति ॥{i}॥", 135, 330)]
    return rows


PROSE = [("यह स्तवन श्री जिनराजसूरि ने रचा है और इसमें प्रभु के गुणों का", 60, 360),
         ("वर्णन किया गया है। इस संग्रह में ऐसी अनेक रचनाएँ दी गई हैं जो", 60, 360),
         ("प्राचीन भंडारों से प्राप्त हुई थीं और पहले कभी छपी नहीं थीं।", 60, 360)]


@pytest.fixture
def books(tmp_path, monkeypatch):
    good, prose, broken = tmp_path / "good.pdf", tmp_path / "prose.pdf", tmp_path / "broken.pdf"
    for p in (good, prose, broken):
        p.write_bytes(b"%PDF")
    layouts = {str(good): [_page(1, PROSE), _page(2, _kruti("शांतिनाथ स्तवन", 3)),
                           _page(3, _kruti("नेमिनाथ स्तवन", 2))],
               str(prose): [_page(1, PROSE)]}

    def fake_read(path, cfg, on_page=None, checkpoint=None):
        if path not in layouts:
            raise RuntimeError("cannot open")
        for i, _ in enumerate(layouts[path], 1):
            (checkpoint or (lambda: None))()
            if on_page:
                on_page(i, len(layouts[path]), "ocr")
        return layouts[path]

    monkeypatch.setattr(gp, "read_layout", fake_read)
    monkeypatch.setattr(gp, "page_count", lambda p: len(layouts.get(str(p), [])))
    return good, prose, broken


def test_run_writes_excel_and_counts(books, tmp_path):
    good, _, _ = books
    seen = []
    res = gp.run_gatha([str(good)], str(tmp_path / "out"), gatha_config(None),
                       on_progress=lambda p: seen.append((p.stage, p.kruti_found,
                                                          getattr(p, "gathas_found", 0))),
                       log=lambda *_: None)
    assert (res.books, res.krutis, res.gathas, res.skipped) == (1, 2, 5, [])
    assert Path(res.results_path).name == "Gatha_Results.xlsx"
    rows = list(load_workbook(res.results_path).active.iter_rows(values_only=True))
    assert len(rows) == 6 and rows[1][3] == "शांतिनाथ स्तवन"
    assert seen[-1] == ("Done", 2, 5)


def test_run_with_no_kruti_writes_header_only(books, tmp_path):
    _, prose, broken = books
    logs = []
    res = gp.run_gatha([str(prose), str(broken)], str(tmp_path / "out"), gatha_config(None),
                       log=logs.append)
    assert res.krutis == 0 and res.skipped == ["broken"]
    rows = list(load_workbook(res.results_path).active.iter_rows(values_only=True))
    assert len(rows) == 1
    assert any("0 Kruti" in m for m in logs) and any("SKIPPED" in m for m in logs)


def test_cancel_raises(books, tmp_path):
    good, _, _ = books
    ctl = Controller()
    ctl.cancel()
    with pytest.raises(Cancelled):
        gp.run_gatha([str(good)], str(tmp_path / "out"), gatha_config(None), log=lambda *_: None,
                     ctl=ctl)
