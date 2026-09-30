"""The full run - read Excel, scan books one by one, write the two Excel outputs.

Used by both the command line and the desktop app. Progress is reported through a
callback; a Controller lets the caller pause, resume or cancel between pages.
"""
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook

from .extract import extract_book, page_count
from .gaps import find_gaps, group_duplicates
from .matcher import FOUND, PARTIAL, Book, BookIndex, locate
from .config import merged
from .report import RESULTS_FILE, merge_approved, write_results


class Cancelled(Exception):
    pass


class Controller:
    """Thread-safe pause / cancel switch checked between pages."""

    def __init__(self):
        self._run = threading.Event()
        self._run.set()
        self._cancel = threading.Event()

    def pause(self):
        self._run.clear()

    def resume(self):
        self._run.set()

    def cancel(self):
        self._cancel.set()
        self._run.set()

    @property
    def paused(self):
        return not self._run.is_set()

    def checkpoint(self):
        self._run.wait()
        if self._cancel.is_set():
            raise Cancelled()


@dataclass
class Progress:
    stage: str = ""
    book_index: int = 0
    book_total: int = 0
    book_name: str = ""
    book_pages_done: int = 0
    book_pages_total: int = 0
    pages_done: int = 0
    pages_total: int = 0
    ocr_pages: int = 0
    kruti_found: int = 0
    new_kruti_blocks: int = 0
    elapsed: float = 0.0
    eta: float | None = None


@dataclass
class RunResult:
    results_path: str
    status_counts: dict
    new_kruti: int
    books: int
    skipped: list = field(default_factory=list)


# ---------------------------------------------------------------- inputs
def _pdfs_in_folder(folder: Path) -> list:
    found = []
    for dirpath, _dirs, files in os.walk(folder, onerror=lambda e: None):  # skip unreadable
        found += [Path(dirpath) / f for f in files
                  if f.lower().endswith(".pdf") and not f.startswith("._")]
    return sorted(found)


def collect_pdfs(inputs) -> list:
    """Accept PDF files and/or folders (searched recursively). Duplicates removed."""
    seen, pdfs = set(), []
    if isinstance(inputs, (str, Path)):
        inputs = [inputs]
    for item in inputs:
        p = Path(item)
        found = _pdfs_in_folder(p) if p.is_dir() \
            else ([p] if p.suffix.lower() == ".pdf" and p.exists() else [])
        for x in found:
            key = str(x.resolve())
            if key not in seen:
                seen.add(key)
                pdfs.append(x)
    return pdfs


def load_krutis(excel_path, cfg):
    wb = load_workbook(excel_path, read_only=True, data_only=True)
    sheet = cfg.get("excel_sheet", 0)
    ws = wb.worksheets[sheet] if isinstance(sheet, int) else wb[sheet]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()
    if not rows:
        raise ValueError("The Excel sheet is empty.")
    header = [str(h).strip() if h is not None else f"Column {i + 1}" for i, h in enumerate(rows[0])]
    wanted = [(cfg.get("excel_columns") or {}).get(k) for k in ("kruti_no", "name", "aadi", "ant")]
    idx = [header.index(w) if w in header else None for w in wanted]
    if None in idx:
        idx = [0, 1, 2, 3]            # fall back to the first four columns
    krutis = []
    for r in rows[1:]:
        r = (r + [None] * len(header))[:len(header)]
        aadi, ant = r[idx[2]], r[idx[3]]
        if not (aadi or ant):
            continue
        krutis.append({"id": r[idx[0]], "name": str(r[idx[1]] or "").strip(),
                       "aadi": str(aadi or ""), "ant": str(ant or ""),
                       "raw": ["" if v is None else v for v in r]})
    if not krutis:
        raise ValueError("No Kruti rows with Aadi/Ant Vakya found in the Excel.")
    return krutis, header


# ---------------------------------------------------------------- run
def run(excel, inputs, out_dir, cfg, on_progress=None, log=print, ctl=None) -> RunResult:
    ctl = ctl or Controller()
    start = time.time()
    prog = Progress(stage="Reading Excel")
    last_emit = [0.0]
    sec_per_page = [None]      # moving average, for the ETA

    def emit(force=False):
        now = time.time()
        if on_progress and (force or now - last_emit[0] >= 0.15):
            prog.elapsed = now - start
            remaining = prog.pages_total - prog.pages_done
            prog.eta = remaining * sec_per_page[0] if sec_per_page[0] else None
            on_progress(prog)
            last_emit[0] = now

    emit(True)
    krutis, columns = load_krutis(excel, cfg)
    log(f"{len(krutis)} Kruti read from {Path(excel).name}")

    pdfs = collect_pdfs(inputs)
    if not pdfs:
        raise ValueError("No PDF files found in the selected files/folders.")
    prog.stage = "Counting pages"
    emit(True)
    counts = []
    for p in pdfs:
        ctl.checkpoint()
        counts.append(page_count(str(p)))
    prog.book_total, prog.pages_total = len(pdfs), sum(counts)
    log(f"{len(pdfs)} books, {prog.pages_total} pages to scan")
    os.makedirs(out_dir, exist_ok=True)

    results = {k["id"]: [] for k in krutis}
    all_gaps, skipped = [], []
    pages_before = 0
    for n, (pdf, npages) in enumerate(zip(pdfs, counts), 1):
        ctl.checkpoint()
        name = pdf.stem
        prog.stage, prog.book_index, prog.book_name = "Reading pages", n, name
        prog.book_pages_done, prog.book_pages_total = 0, npages
        emit(True)
        t_last = [time.time()]

        def on_page(done, total, source, base=pages_before):
            now = time.time()
            if source != "cache":
                dt = now - t_last[0]
                sec_per_page[0] = dt if sec_per_page[0] is None else 0.9 * sec_per_page[0] + 0.1 * dt
            t_last[0] = now
            if source == "ocr":
                prog.ocr_pages += 1
            prog.book_pages_done, prog.book_pages_total = done, total
            prog.pages_done = base + done
            emit()

        try:
            pages = extract_book(str(pdf), cfg, on_page=on_page, checkpoint=ctl.checkpoint)
        except Cancelled:
            raise
        except Exception as e:  # noqa: BLE001 - a broken PDF must not stop a 200-book run
            log(f"[{n}/{len(pdfs)}] {name}: SKIPPED - could not read ({e})")
            skipped.append(name)
            pages_before += npages
            prog.pages_done = pages_before
            continue
        pages_before += npages
        prog.pages_done = pages_before

        prog.stage = "Matching Kruti"
        emit(True)
        book = Book.from_pages(pdf.name, pages)      # the file name is what the report shows
        index = BookIndex(book.key)
        spans, found_here = [], 0
        for k in krutis:
            occ = locate(k, book, index, cfg)
            results[k["id"]].extend(occ)
            spans += [o.span_light for o in occ if o.span_light]
            found_here += any(o.status == FOUND for o in occ)
        book_gaps = find_gaps(book, spans, {p.page: p.confidence for p in pages}, cfg)
        all_gaps += book_gaps
        prog.kruti_found = sum(1 for occ in results.values() if any(o.status == FOUND for o in occ))
        prog.new_kruti_blocks = len(all_gaps)
        log(f"[{n}/{len(pdfs)}] {name}: {len(pages)} pages, {found_here} Excel Kruti, "
            f"{len(book_gaps)} new Kruti blocks")
        emit(True)

    prog.stage = "Writing Excel files"
    emit(True)
    all_gaps.sort(key=lambda g: (g.book, g.start_page))
    missing = group_duplicates(all_gaps, cfg["duplicate_threshold"])

    results_path = os.path.join(out_dir, RESULTS_FILE)
    write_results(results_path, missing, krutis, results, columns)

    status = {FOUND: 0, PARTIAL: 0, "Not Found": 0}
    for k in krutis:
        occ = results[k["id"]]
        status[FOUND if any(o.status == FOUND for o in occ) else (PARTIAL if occ else "Not Found")] += 1
    prog.stage = "Done"
    prog.pages_done = prog.pages_total
    emit(True)
    log(f"Done. Excel Kruti: {status}. New Kruti: {len(missing)}")
    return RunResult(results_path, status, len(missing), len(pdfs), skipped)


def merge(excel_path, results_path, out_path, cfg=None):
    """New master = the team's Excel + the new Kruti approved in the reviewed results."""
    cfg = cfg or merged(None)
    krutis, columns = load_krutis(excel_path, cfg)
    return merge_approved([k["raw"] for k in krutis], columns, results_path, out_path)
