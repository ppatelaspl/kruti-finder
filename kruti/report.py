"""Write the review workbook and merge approved gaps into an updated Kruti master."""
from datetime import date

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.worksheet.datavalidation import DataValidation

# Aspire brand palette only
GOLD, ORANGE, RED, PINK, PLUM, NAVY, GREY = (
    "F8BB13", "EE7532", "F04735", "D6175C", "B81A58", "011D45", "B2BBC7")
FONT = "Outfit"

_HEADER_FILL = PatternFill("solid", fgColor=NAVY)
_INPUT_FILL = PatternFill("solid", fgColor=GREY)
_STATUS_STYLE = {
    "Found": (GOLD, NAVY),
    "Partially Found": (ORANGE, "FFFFFF"),
    "Not Found": (PINK, "FFFFFF"),
}
_THIN = Side(style="thin", color=GREY)
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_WRAP = Alignment(wrap_text=True, vertical="top")


def _table(ws, headers, rows, widths, wrap_cols=(), status_col=None, input_cols=()):
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(name=FONT, bold=True, color="FFFFFF")
        c.fill = _HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = _BORDER
    for row in rows:
        ws.append([ILLEGAL_CHARACTERS_RE.sub(" ", v) if isinstance(v, str) else v for v in row])
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for c in r:
            c.font = Font(name=FONT, color=NAVY)
            c.border = _BORDER
            c.alignment = _WRAP if c.column in wrap_cols else Alignment(vertical="top")
            if c.column in input_cols:
                c.fill = _INPUT_FILL
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


def _pages(o):
    return (o.start_page if o.start_page is not None else "-",
            o.end_page if o.end_page is not None else "-")


def write_report(path, krutis, results, missing_count, page_log, books_count, source_columns):
    wb = Workbook()
    dash = wb.active
    dash.title = "Dashboard"

    # ---- Kruti Summary: one row per Kruti in the Excel
    summary_rows = []
    for k in krutis:
        occ = results.get(k["id"], [])
        found = [o for o in occ if o.status == "Found"]
        best = (found or occ or [None])[0]
        status = "Found" if found else ("Partially Found" if occ else "Not Found")
        books = sorted({o.book for o in (found or occ)})
        sp, ep = _pages(best) if best else ("-", "-")
        summary_rows.append([k["id"], k["name"], status, len(books),
                             best.book if best else "-", sp, ep,
                             ", ".join(books[1:]) if len(books) > 1 else "",
                             best.note if best else "Not located in any book"])
    ws = wb.create_sheet("Kruti Summary")
    _table(ws, ["Kruti No.", "Kruti Name", "Status", "No. of Books", "Book (first match)",
                "Start Page", "End Page", "Also Found In", "Note"],
           summary_rows, [11, 34, 16, 10, 34, 10, 10, 40, 36], wrap_cols=(2, 8, 9), status_col=3)

    # ---- Kruti Locations: one row per occurrence
    loc_rows = []
    for k in krutis:
        for o in results.get(k["id"], []):
            sp, ep = _pages(o)
            loc_rows.append([k["id"], k["name"], o.book, sp, ep, o.status,
                             o.aadi_score if o.aadi_score is not None else "-",
                             o.ant_score if o.ant_score is not None else "-", o.note])
    ws = wb.create_sheet("Kruti Locations")
    _table(ws, ["Kruti No.", "Kruti Name", "Book", "Start Page", "End Page", "Status",
                "Aadi Match %", "Ant Match %", "Note"],
           loc_rows, [11, 34, 34, 10, 10, 16, 12, 12, 36], wrap_cols=(2, 9), status_col=6)

    # ---- Page log
    ws = wb.create_sheet("Page Log")
    _table(ws, ["Book", "Page", "Source", "OCR Confidence", "Characters", "Flag"],
           page_log, [34, 8, 10, 14, 12, 34])

    # ---- Updated master: original Excel + status columns
    by_id = {r[0]: r for r in summary_rows}
    master_rows = []
    for k in krutis:
        s = by_id[k["id"]]
        master_rows.append(list(k["raw"]) + [s[2], s[4], s[5], s[6], s[7], "Original"])
    ws = wb.create_sheet("Updated Master")
    _table(ws, list(source_columns) + ["Status", "Book", "Start Page", "End Page",
                                       "Also Found In", "Row Source"],
           master_rows, [11, 30, 55, 55, 16, 30, 10, 10, 30, 22],
           wrap_cols=(2, 3, 4, 9), status_col=len(source_columns) + 1)

    _write_dashboard(dash, books_count, missing_count)
    wb.save(path)


def _write_dashboard(ws, books_count, missing_count):
    ws["A1"] = "Kruti Finder - Run Summary"
    ws["A1"].font = Font(name=FONT, size=16, bold=True, color=NAVY)
    ws["A2"] = f"Generated {date.today():%d %b %Y}"
    ws["A2"].font = Font(name=FONT, italic=True, color=PLUM)
    rows = [
        ("Books processed", books_count, "Value from this run"),
        ("Kruti in Excel", "=COUNTA('Kruti Summary'!A:A)-1", ""),
        ("Found", "=COUNTIF('Kruti Summary'!C:C,\"Found\")", ""),
        ("Partially Found", "=COUNTIF('Kruti Summary'!C:C,\"Partially Found\")", ""),
        ("Not Found", "=COUNTIF('Kruti Summary'!C:C,\"Not Found\")", ""),
        ("Found %", "=IFERROR(B6/B5,0)", ""),
        ("Missing Kruti (not in Excel)", missing_count, "Value from this run - see Missing_Kruti.xlsx"),
        ("Pages read", "=COUNTA('Page Log'!A:A)-1", ""),
        ("Pages OCR'd", "=COUNTIF('Page Log'!C:C,\"ocr\")", ""),
        ("Pages flagged (low quality)", "=COUNTIF('Page Log'!F:F,\"?*\")-1", "Check these before trusting a Not Found"),
    ]
    for i, (label, val, note) in enumerate(rows, start=4):
        ws.cell(i, 1, label).font = Font(name=FONT, bold=True, color=NAVY)
        c = ws.cell(i, 2, val)
        c.font = Font(name=FONT, color=NAVY)
        c.border = _BORDER
        ws.cell(i, 3, note).font = Font(name=FONT, italic=True, color=PLUM)
    ws["B9"].number_format = "0.0%"  # Found % row
    for col, w in zip("ABC", (30, 14, 42)):
        ws.column_dimensions[col].width = w


# ------------------------------------------------------------------ Kruti in books
NEW_SHEET, KNOWN_SHEET = "New Kruti", "Excel Kruti - Books Found"
NEW_EXTRA = ["Temp ID", "Book", "Start Page", "End Page", "No. of Verses", "No. of Books",
             "Also Found In", "Author Signature", "OCR Quality", "Approve (Y/N)",
             "Reviewer Remarks"]
KNOWN_EXTRA = ["No. of Books", "Book", "Start Page", "End Page", "Status",
               "Also Found In", "Note", "Reviewer Remarks"]


def _page_range(s, e):
    s = "-" if s is None else s
    e = "-" if e is None else e
    return f"p. {s}" if s == e else f"p. {s}-{e}"


def write_missing(path, gaps, krutis, results, source_columns):
    """Kruti found in the books, in the team's own column layout:
    sheet 1 - Kruti that are not in the Excel at all (one row per Kruti),
    sheet 2 - Kruti already in the Excel, with every book they appear in."""
    wb = Workbook()
    cols = list(source_columns[:4])
    n = len(cols)

    # ---- sheet 1: new Kruti
    ws = wb.active
    ws.title = NEW_SHEET
    rows = []
    for g in gaps:
        also = "; ".join(f"{b} ({_page_range(s, e)})" for b, s, e in g.also_in)
        rows.append(["", g.title, g.aadi, g.ant, g.temp_id, g.book, g.start_page, g.end_page,
                     g.verses, 1 + len(g.also_in), also, g.author_signature, g.ocr_quality,
                     "", ""])
    _table(ws, cols + NEW_EXTRA, rows,
           [11, 28, 55, 55, 11, 30, 10, 10, 9, 9, 40, 11, 14, 11, 30],
           wrap_cols=(2, 3, 4, n + 7, n + 11), input_cols=(1, n + 10, n + 11))
    if rows:
        dv = DataValidation(type="list", formula1='"Y,N"', allow_blank=True)
        ws.add_data_validation(dv)
        letter = ws.cell(1, n + 10).column_letter
        dv.add(f"{letter}2:{letter}{ws.max_row}")
    for r in ws.iter_rows(min_row=2):
        if r[n + 8].value != "OK":
            r[n + 8].font = Font(name=FONT, bold=True, color=RED)
    ws["A1"].comment = Comment("Grey cells are for the team: assign the real Kruti No., set "
                               "Approve = Y, correct Aadi/Ant text if OCR garbled it. Then run "
                               "kruti_finder.py merge.", "Kruti Finder")

    # ---- sheet 2: Excel Kruti with all books they appear in
    ws = wb.create_sheet(KNOWN_SHEET)
    rows = []
    for k in krutis:
        occ = results.get(k["id"], [])
        if not occ:
            continue
        found = [o for o in occ if o.status == "Found"]
        ordered = found + [o for o in occ if o.status != "Found"]
        first = ordered[0]
        books = []
        for o in ordered:
            if o.book not in books:
                books.append(o.book)
        also = "; ".join(f"{o.book} ({_page_range(o.start_page, o.end_page)})"
                         + ("" if o.status == "Found" else " - partial")
                         for o in ordered[1:])
        rows.append(list(k["raw"][:4]) + [
            len(books), first.book,
            first.start_page if first.start_page is not None else "-",
            first.end_page if first.end_page is not None else "-",
            "Found" if found else "Partially Found", also, first.note, ""])
    _table(ws, cols + KNOWN_EXTRA, rows,
           [11, 28, 55, 55, 9, 30, 10, 10, 16, 45, 30, 30],
           wrap_cols=(2, 3, 4, n + 6, n + 7, n + 8), status_col=n + 5, input_cols=(n + 8,))

    # ---- guide
    guide = wb.create_sheet("How to Review")
    notes = [
        f"'{NEW_SHEET}' = Kruti found in the books that are NOT in the submitted Excel. "
        "One row per Kruti; copies in other books/editions are listed in 'Also Found In'.",
        "Rows with Author Signature = Yes are sorted first.",
        "Title comes from the heading above verse 1 - verify it; it may include raga/dhal lines.",
        "OCR Quality 'Low - check scan': open the page and correct the Aadi/Ant text before approving.",
        f"'{KNOWN_SHEET}' = Kruti already in the Excel, with every book and page range where "
        "they appear. The Excel does not record which book the team used, so all books are "
        "listed; mark in Reviewer Remarks which copies are new for the team.",
        "Kruti from the Excel not found in any book are listed in Kruti_Report.xlsx.",
        "After review: python kruti_finder.py merge --report Kruti_Report.xlsx "
        "--missing Missing_Kruti.xlsx --out Kruti_Master_v2.xlsx",
    ]
    guide["A1"] = "How to review this file"
    guide["A1"].font = Font(name=FONT, size=14, bold=True, color=NAVY)
    for i, t in enumerate(notes, 3):
        c = guide.cell(i, 1, f"{i - 2}. {t}")
        c.font = Font(name=FONT, color=NAVY)
        c.alignment = _WRAP
    guide.column_dimensions["A"].width = 110
    wb.save(path)


# ------------------------------------------------------------------ merge
def merge_approved(report_path, missing_path, out_path):
    master = load_workbook(report_path)["Updated Master"]
    headers = [c.value for c in master[1]]
    rows = [list(r) for r in master.iter_rows(min_row=2, values_only=True)]
    n_src = headers.index("Status")

    miss = load_workbook(missing_path)[NEW_SHEET]
    mh = [c.value for c in miss[1]]
    col = {h: i for i, h in enumerate(mh)}
    added = 0
    for r in miss.iter_rows(min_row=2, values_only=True):
        if str(r[col["Approve (Y/N)"]] or "").strip().upper() != "Y":
            continue
        added += 1
        base = [r[0] or r[col["Temp ID"]], r[1] or "", r[2], r[3]]
        base += [""] * (n_src - len(base))
        rows.append(base[:n_src] + ["Found", r[col["Book"]], r[col["Start Page"]],
                                    r[col["End Page"]], r[col["Also Found In"]] or "",
                                    "Added from missing-Kruti review"])

    out = Workbook()
    ws = out.active
    ws.title = "Kruti Master"
    _table(ws, headers, rows, [11, 30, 55, 55, 16, 30, 10, 10, 30, 22],
           wrap_cols=(2, 3, 4, 9), status_col=n_src + 1)
    out.save(out_path)
    return added, len(rows)
