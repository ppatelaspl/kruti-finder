"""Gatha Lines: the Excel file.   Run:  python -m pytest tests"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook                                       # noqa: E402

from kruti.gatha import GKruti, Gatha                                    # noqa: E402
from kruti.gatha_report import GATHA_COLUMNS, GATHA_SHEET, write_gatha_results  # noqa: E402
from kruti.report import GOLD, ORANGE, PINK                              # noqa: E402

EXPECTED = ["File Name", "Book Name", "Kruti No.", "Kruti Name", "Part", "Gatha No.",
            "Total Gathas", "First Line", "Last Line", "PDF Page", "Book Page", "Script",
            "Text Source", "OCR Confidence %", "How found", "Confidence", "Check", "Remarks"]


def g(no, pages=(4, 4), how="Numbered verse", conf=95.0, checks=(), first="क ख,", last="ग घ"):
    return Gatha("", no, first, f"{last} ॥{no}॥", pages, how, conf, "OCR", list(checks))


def test_columns_rows_and_pages(tmp_path):
    k1 = GKruti(1, "शांतिनाथ स्तवन", [g("1"), g("2", (4, 5), checks=["crosses pages"])])
    k2 = GKruti(2, "", [g("(1)", (5, 5), "No number - gap"), g("(2)", (5, 5), "No number - line count"),
                        g("(3)", (5, 5), "No number - line count", first="કખ,", last="ગઘ")], ["no heading"])
    path = tmp_path / "Gatha_Results.xlsx"
    n = write_gatha_results(str(path), [("b.pdf", "Book B", {4: 12, 5: 13}, [k1, k2])])
    assert n == 5 and GATHA_COLUMNS == EXPECTED
    ws = load_workbook(path)[GATHA_SHEET]
    rows = list(ws.iter_rows(values_only=True))
    assert list(rows[0]) == EXPECTED and len(rows) == 6
    col = {c: i for i, c in enumerate(EXPECTED)}
    r1, r2, r3, r5 = rows[1], rows[2], rows[3], rows[5]
    assert (r1[col["PDF Page"]], r1[col["Book Page"]]) == (4, 12)
    assert (r2[col["PDF Page"]], r2[col["Book Page"]]) == ("4-5", "12-13")
    assert r1[col["Total Gathas"]] == 2 and r3[col["Total Gathas"]] == 3
    assert r1[col["Check"]] == "OK" and r2[col["Check"]] == "crosses pages"
    assert r1[col["Confidence"]] == "High" and r2[col["Confidence"]] == "Medium"
    assert r5[col["Confidence"]] == "Low" and r5[col["Script"]] == "Gujarati"
    assert r1[col["Script"]] == "Devanagari" and r1[col["Text Source"]] == "OCR"
    assert r1[col["Kruti Name"]] == "शांतिनाथ स्तवन" and r3[col["Kruti No."]] == 2
    assert r1[col["First Line"]] == "क ख," and r1[col["Last Line"]] == "ग घ ॥1॥"
    fills = {ws.cell(i, col["Confidence"] + 1).value: ws.cell(i, col["Confidence"] + 1).fill.fgColor.rgb
             for i in range(2, 7)}
    assert fills["High"].endswith(GOLD) and fills["Medium"].endswith(ORANGE)
    assert fills["Low"].endswith(PINK)


def test_header_only_when_nothing_found(tmp_path):
    path = tmp_path / "Gatha_Results.xlsx"
    assert write_gatha_results(str(path), [("b.pdf", "Book B", {}, [])]) == 0
    rows = list(load_workbook(path)[GATHA_SHEET].iter_rows(values_only=True))
    assert rows == [tuple(EXPECTED)]
