"""Gatha Lines: write Gatha_Results.xlsx - one row per gatha of every Kruti found, with
its first and last line and what a reviewer needs to decide whether to trust the row."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from .gatha import confidence
from .normalize import script_of
from .report import FONT, GOLD, NAVY, ORANGE, PINK, RED, _BAND_FILL, _INPUT_FILL, _table

GATHA_FILE = "Gatha_Results.xlsx"
GATHA_SHEET = "Gatha Lines"
GATHA_COLUMNS = ["File Name", "Book Name", "Kruti No.", "Kruti Name", "Part", "Gatha No.",
                 "Total Gathas", "First Line", "Last Line", "PDF Page", "Book Page", "Script",
                 "Text Source", "OCR Confidence %", "How found", "Confidence", "Check", "Remarks"]
_WIDTHS = [30, 24, 8, 26, 12, 8, 8, 48, 48, 9, 9, 11, 12, 11, 22, 11, 30, 24]
_CONF_STYLE = {"High": (GOLD, NAVY), "Medium": (ORANGE, "FFFFFF"), "Low": (PINK, "FFFFFF")}


def _pages(a, b):
    if a is None:
        return ""
    return a if b is None or a == b else f"{a}-{b}"


def write_gatha_results(path: str, books: list, low_ocr: float = 70) -> int:
    """books: [(file name, book name, {PDF page: printed page}, [GKruti])]. Returns rows."""
    rows, keys = [], []
    for file_name, book_name, printed, krutis in books:
        for k in krutis:
            for g in k.gathas:
                bp = [printed.get(p) for p in g.pages]
                rows.append([file_name, book_name, k.no, k.title, g.part, g.no, len(k.gathas),
                             g.first, g.last, _pages(*g.pages),
                             _pages(bp[0], bp[1]) if bp[0] is not None else "",
                             script_of(g.first + g.last) or "", g.source, g.conf, g.how,
                             confidence(g, low_ocr), "; ".join(g.checks) or "OK", ""])
                keys.append((file_name, k.no))
    wb = Workbook()
    ws = wb.active
    ws.title = GATHA_SHEET
    col = {c: i + 1 for i, c in enumerate(GATHA_COLUMNS)}
    _table(ws, GATHA_COLUMNS, rows, _WIDTHS,
           wrap_cols=(col["File Name"], col["Book Name"], col["Kruti Name"], col["First Line"],
                      col["Last Line"], col["Check"], col["Remarks"]),
           input_cols=(col["Remarks"],))
    band, prev = False, None
    for r, key in zip(ws.iter_rows(min_row=2), keys):
        if key != prev:                       # each Kruti's rows shaded as one block
            band, prev = not band, key
        for c in r:
            if band and c.column != col["Remarks"]:
                c.fill = _BAND_FILL
            elif c.column == col["Remarks"]:
                c.fill = _INPUT_FILL
        conf = r[col["Confidence"] - 1]
        fill, color = _CONF_STYLE[conf.value]
        conf.fill = PatternFill("solid", fgColor=fill)
        conf.font = Font(name=FONT, bold=True, color=color)
        check = r[col["Check"] - 1]
        if check.value != "OK":
            check.font = Font(name=FONT, bold=True, color=RED)
    wb.save(path)
    return len(rows)
