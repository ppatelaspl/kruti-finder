"""Gatha Lines: one run over PDF books - read each page with its layout, find every Kruti
of two or more gathas, write Gatha_Results.xlsx. Pause/resume/cancel and progress work as
in feature 1 (kruti/pipeline.py), whose helpers are reused unchanged."""
import os
import time
from dataclasses import dataclass, field

from .extract import page_count
from .gatha import split_gathas
from .gatha_lines import classify_book
from .gatha_report import GATHA_FILE, write_gatha_results
from .layout import read_layout
from .pipeline import Cancelled, Controller, Progress, book_name, collect_pdfs


@dataclass
class GathaResult:
    results_path: str
    books: int
    krutis: int
    gathas: int
    skipped: list = field(default_factory=list)


def run_gatha(inputs, out_dir, cfg, on_progress=None, log=print, ctl=None) -> GathaResult:
    ctl = ctl or Controller()
    start = time.time()
    prog = Progress(stage="Counting pages")
    prog.gathas_found = 0
    last_emit = [0.0]
    sec_per_page = [None]

    def emit(force=False):
        now = time.time()
        if on_progress and (force or now - last_emit[0] >= 0.15):
            prog.elapsed = now - start
            remaining = prog.pages_total - prog.pages_done
            prog.eta = remaining * sec_per_page[0] if sec_per_page[0] else None
            on_progress(prog)
            last_emit[0] = now

    pdfs = collect_pdfs(inputs)
    if not pdfs:
        raise ValueError("No PDF files found in the selected files/folders.")
    emit(True)
    counts = []
    for p in pdfs:
        ctl.checkpoint()
        counts.append(page_count(str(p)))
    prog.book_total, prog.pages_total = len(pdfs), sum(counts)
    log(f"{len(pdfs)} books, {prog.pages_total} pages to read")
    os.makedirs(out_dir, exist_ok=True)

    results, skipped, pages_before = [], [], 0
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
            pages = read_layout(str(pdf), cfg, on_page=on_page, checkpoint=ctl.checkpoint)
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

        prog.stage = "Finding gathas"
        emit(True)
        try:
            lines, printed = classify_book(pages, cfg)
            krutis = split_gathas(lines, cfg)
        except Exception as e:  # noqa: BLE001 - one odd book must not lose a 200-book run
            log(f"[{n}/{len(pdfs)}] {name}: SKIPPED - could not analyse ({type(e).__name__}: {e})")
            skipped.append(name)
            continue
        results.append((pdf.name, book_name(pdf), printed, krutis))
        gathas = sum(len(k.gathas) for k in krutis)
        prog.kruti_found += len(krutis)
        prog.gathas_found += gathas
        log(f"[{n}/{len(pdfs)}] {name}: {len(pages)} pages, {len(krutis)} Kruti, {gathas} gathas")
        emit(True)

    prog.stage = "Writing Excel file"
    emit(True)
    path = os.path.join(out_dir, GATHA_FILE)
    stem, ext = os.path.splitext(GATHA_FILE)
    for k in range(2, 10):
        try:
            write_gatha_results(path, results, cfg["low_ocr_confidence"])
            break
        except PermissionError:          # the file is open in Excel: keep the run, save beside it
            log(f"{os.path.basename(path)} is open in another program; saving as {stem} ({k}){ext}")
            path = os.path.join(out_dir, f"{stem} ({k}){ext}")
    else:
        write_gatha_results(path, results, cfg["low_ocr_confidence"])
    prog.stage = "Done"
    prog.pages_done = prog.pages_total
    emit(True)
    log(f"Done. {prog.kruti_found} Kruti found, {prog.gathas_found} gathas.")
    return GathaResult(path, len(pdfs), prog.kruti_found, prog.gathas_found, skipped)
