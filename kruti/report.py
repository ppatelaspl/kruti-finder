"""Write Kruti_Results.xlsx: every Kruti found in the books, one row each, flagged as in
the input Excel (same or other script) or new. Rows of the same Kruti - across books,
places and scripts - share a group ID and are kept together."""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

RESULTS_FILE = "Kruti_Results.xlsx"
SHEET = "Kruti Found"

# Aspire brand palette only
GOLD, ORANGE, RED, PINK, PLUM, NAVY, GREY = (
    "F8BB13", "EE7532", "F04735", "D6175C", "B81A58", "011D45", "B2BBC7")
BAND = "EEF1F5"          # light shade marking every other Kruti group
FONT = "Outfit"

_HEADER_FILL = PatternFill("solid", fgColor=NAVY)
_INPUT_FILL = PatternFill("solid", fgColor=GREY)
_BAND_FILL = PatternFill("solid", fgColor=BAND)
MATCH_SAME, MATCH_OTHER, NEW = "Matched - same script", "Matched - other script", "New"
_STATUS_STYLE = {
    MATCH_SAME: (GOLD, NAVY),
    MATCH_OTHER: (ORANGE, "FFFFFF"),
    NEW: (PINK, "FFFFFF"),
}
_THIN = Side(style="thin", color=GREY)
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_WRAP = Alignment(wrap_text=True, vertical="top")


def _table(ws, headers, rows, widths, wrap_cols=(), status_col=None, input_cols=(), group_col=None):
    """group_col: rows sharing a value in this column are one group; groups alternate shade."""
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(name=FONT, bold=True, color="FFFFFF")
        c.fill = _HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = _BORDER
    for row in rows:
        ws.append([ILLEGAL_CHARACTERS_RE.sub(" ", v) if isinstance(v, str) else v for v in row])
    band, prev = False, object()
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row):
        if group_col:
            key = r[group_col - 1].value
            if key != prev:
                band, prev = not band, key
        for c in r:
            c.font = Font(name=FONT, color=NAVY)
            c.border = _BORDER
            c.alignment = _WRAP if c.column in wrap_cols else Alignment(vertical="top")
            if c.column in input_cols:
                c.fill = _INPUT_FILL
            elif group_col and band:
                c.fill = _BAND_FILL
        if status_col:
            cell = r[status_col - 1]
            if cell.value in _STATUS_STYLE:
                fill, color = _STATUS_STYLE[cell.value]
                cell.fill = PatternFill("solid", fgColor=fill)
                cell.font = Font(name=FONT, bold=True, color=color)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    ws.freeze_panes = "A2"
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.print_title_rows = "1:1"
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions


def _page(v):
    return "-" if v is None else v


# ------------------------------------------------------------------ results
COLUMNS = ["Group No.", "Copy", "File Name", "Book Name", "Kruti क्रमांक", "Kruti Name",
           "Aadi Vakya (आदिवाक्य)", "Ant Vakya (अंत वाक्य)", "PDF Start Page", "PDF End Page",
           "Book Start Page", "Book End Page", "No. of Verses", "Script", "In Excel?", "Match %",
           "Check", "Remarks"]


def write_results(path, krutis):
    """One row per Kruti found. Rows of a group (the same Kruti in several books, places or
    scripts) sit together; Copy says which of how many."""
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    size = {}
    for k in krutis:
        size[k.group_no] = size.get(k.group_no, 0) + 1
    rows, nth = [], {}
    for k in sorted(krutis, key=lambda k: (k.group_no, k.book, k.start_page or 0)):
        nth[k.group_no] = nth.get(k.group_no, 0) + 1
        rows.append([k.group_no, f"{nth[k.group_no]} of {size[k.group_no]}", k.book, k.book_name,
                     "" if k.kruti_no is None else k.kruti_no, k.kruti_name or k.title,
                     k.aadi, k.ant, _page(k.start_page), _page(k.end_page),
                     "" if k.book_start is None else k.book_start,
                     "" if k.book_end is None else k.book_end,
                     "" if k.verses is None else k.verses, k.script, k.match,
                     "" if k.match_score is None else k.match_score,
                     "; ".join(k.checks) or "OK", ""])
    col = {c: i + 1 for i, c in enumerate(COLUMNS)}
    _table(ws, COLUMNS, rows, [8, 8, 36, 26, 11, 26, 48, 48, 8, 8, 8, 8, 8, 11, 21, 8, 30, 28],
           wrap_cols=(3, 4, 6, 7, 8, col["Check"], col["Remarks"]), group_col=1,
           status_col=col["In Excel?"], input_cols=(col["Remarks"],))
    for r in ws.iter_rows(min_row=2):
        cell = r[col["Check"] - 1]
        if cell.value != "OK":
            cell.font = Font(name=FONT, bold=True, color=RED)
    wb.save(path)
