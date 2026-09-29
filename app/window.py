"""Kruti Finder main window."""
import os
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from kruti.config import merged
from kruti.ocr_setup import configure_ocr, resource_dir
from kruti.pipeline import collect_pdfs

from .version import __version__
from .worker import MergeWorker, RunWorker


def _fmt_time(sec):
    if sec is None:
        return "estimating…"
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def _open(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def data_dir() -> Path:
    d = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    d.mkdir(parents=True, exist_ok=True)
    return d


class BooksList(QListWidget):
    """List of selected PDF files/folders; accepts drag and drop."""

    def __init__(self, on_change):
        super().__init__()
        self.on_change = on_change
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def paths(self):
        return [self.item(i).data(Qt.UserRole) for i in range(self.count())]

    def add_paths(self, paths):
        existing = set(self.paths())
        for p in paths:
            p = str(Path(p))
            if p in existing:
                continue
            is_dir = Path(p).is_dir()
            item = QListWidgetItem(("📁  " if is_dir else "📄  ") + p)
            item.setData(Qt.UserRole, p)
            self.addItem(item)
        self.on_change()

    def dragEnterEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else e.ignore()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, e):
        self.add_paths(u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Kruti Finder {__version__}")
        self.setWindowIcon(QIcon(str(resource_dir() / "app" / "assets" / "icon.png")))
        self.settings = QSettings("Aspire Softserv", "Kruti Finder")
        self.thread = self.worker = None
        self.result = None
        self.pdf_count = 0

        root = QWidget(objectName="page")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._header())
        tabs = QTabWidget()
        tabs.addTab(self._find_tab(), "Find Kruti")
        tabs.addTab(self._merge_tab(), "Merge Reviewed File")
        layout.addWidget(tabs)
        self.setCentralWidget(root)
        self.resize(980, 860)
        self._load_settings()
        self._check_ocr()

    # ------------------------------------------------------------------ layout
    def _header(self):
        w = QWidget(objectName="header")
        h = QHBoxLayout(w)
        h.setContentsMargins(20, 12, 20, 12)
        col = QVBoxLayout()
        col.addWidget(QLabel("Kruti Finder", objectName="title"))
        col.addWidget(QLabel("Map Kruti to books · find Kruti not yet in the Excel",
                             objectName="subtitle"))
        h.addLayout(col)
        h.addStretch()
        self.ocr_label = QLabel("Checking OCR…")
        self.ocr_label.setStyleSheet("color: white;")
        h.addWidget(self.ocr_label)
        return w

    def _file_row(self, placeholder, browse):
        edit = QLineEdit(placeholderText=placeholder)
        btn = QPushButton("Browse…")
        btn.clicked.connect(browse)
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        row.addWidget(btn)
        return edit, row

    def _find_tab(self):
        page = QWidget(objectName="page")
        v = QVBoxLayout(page)

        g1 = QGroupBox("1.  Kruti Excel (team's manual work)")
        self.excel_edit, row = self._file_row("Select the .xlsx file…", self._pick_excel)
        g1.setLayout(row)
        v.addWidget(g1)

        g2 = QGroupBox("2.  PDF books: pick files, a folder, or drag them here")
        g2v = QVBoxLayout(g2)
        self.books = BooksList(self._books_changed)
        self.books.setMinimumHeight(90)
        g2v.addWidget(self.books)
        btns = QHBoxLayout()
        for text, slot in (("Add PDF files…", self._add_files), ("Add folder…", self._add_folder),
                           ("Remove selected", self._remove_selected), ("Clear", self._clear_books)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch()
        self.books_summary = QLabel("No books selected")
        btns.addWidget(self.books_summary)
        g2v.addLayout(btns)
        v.addWidget(g2)

        g3 = QGroupBox("3.  Save results to")
        self.out_edit, row = self._file_row("Output folder…", self._pick_out)
        g3.setLayout(row)
        v.addWidget(g3)

        v.addWidget(self._advanced())

        ctl = QHBoxLayout()
        self.start_btn = QPushButton("Start", objectName="primary")
        self.pause_btn = QPushButton("Pause")
        self.cancel_btn = QPushButton("Cancel", objectName="danger")
        self.start_btn.clicked.connect(self._start)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.cancel_btn.clicked.connect(self._cancel)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        for b in (self.start_btn, self.pause_btn, self.cancel_btn):
            ctl.addWidget(b)
        ctl.addStretch()
        v.addLayout(ctl)

        v.addWidget(self._progress_box())

        self.log_view = QPlainTextEdit(readOnly=True)
        self.log_view.setMaximumBlockCount(3000)
        self.log_view.setMinimumHeight(110)
        v.addWidget(self.log_view, 1)

        self.results_bar = QWidget()
        rb = QHBoxLayout(self.results_bar)
        rb.setContentsMargins(0, 0, 0, 0)
        self.open_missing_btn = QPushButton("Open Missing Kruti file", objectName="primary")
        self.open_report_btn = QPushButton("Open Report")
        self.open_folder_btn = QPushButton("Open output folder")
        self.open_missing_btn.clicked.connect(lambda: _open(self.result.missing_path))
        self.open_report_btn.clicked.connect(lambda: _open(self.result.report_path))
        self.open_folder_btn.clicked.connect(
            lambda: _open(Path(self.result.missing_path).parent))
        for b in (self.open_missing_btn, self.open_report_btn, self.open_folder_btn):
            rb.addWidget(b)
        rb.addStretch()
        self.results_bar.hide()
        v.addWidget(self.results_bar)
        return page

    def _advanced(self):
        box = QGroupBox("Advanced settings")
        box.setCheckable(True)
        box.setChecked(False)
        inner = QWidget()
        form = QFormLayout(inner)
        self.workers_spin = QSpinBox(minimum=1, maximum=max(1, os.cpu_count() or 1))
        self.threshold_spin = QSpinBox(minimum=70, maximum=98)
        self.author_edit = QLineEdit()
        self.author_only = QCheckBox("List only new Kruti carrying the author's signature")
        self.force_ocr = QCheckBox("OCR every page (ignore PDF text layers)")
        clear = QPushButton("Clear saved OCR results")
        clear.clicked.connect(self._clear_cache)
        form.addRow("Parallel OCR jobs", self.workers_spin)
        form.addRow("Match threshold (%)", self.threshold_spin)
        form.addRow("Author signature(s)", self.author_edit)
        form.addRow("", self.author_only)
        form.addRow("", self.force_ocr)
        form.addRow("", clear)
        lay = QVBoxLayout(box)
        lay.addWidget(inner)
        inner.setVisible(False)
        box.toggled.connect(inner.setVisible)
        return box

    def _progress_box(self):
        box = QGroupBox("Progress")
        g = QGridLayout(box)
        self.stage_label = QLabel("Ready")
        self.overall_bar = QProgressBar()
        self.book_label = QLabel("")
        self.book_bar = QProgressBar(objectName="book")
        g.addWidget(self.stage_label, 0, 0, 1, 5)
        g.addWidget(QLabel("All books"), 1, 0)
        g.addWidget(self.overall_bar, 1, 1, 1, 4)
        g.addWidget(QLabel("This book"), 2, 0)
        g.addWidget(self.book_bar, 2, 1, 1, 4)
        g.addWidget(self.book_label, 3, 0, 1, 5)
        self.stats = {}
        for col, (key, cap) in enumerate((("elapsed", "Elapsed"), ("eta", "Time left"),
                                          ("ocr", "Pages OCR'd"), ("found", "Excel Kruti found"),
                                          ("new", "New Kruti (so far)"))):
            val = QLabel("–", objectName="stat")
            c = QVBoxLayout()
            c.addWidget(val)
            c.addWidget(QLabel(cap, objectName="statcap"))
            g.addLayout(c, 4, col)
            self.stats[key] = val
        return box

    def _merge_tab(self):
        page = QWidget(objectName="page")
        v = QVBoxLayout(page)
        info = QLabel("After the team has reviewed <b>Missing_Kruti.xlsx</b> (Approve = Y, real "
                      "Kruti No. filled in), merge the approved rows into a new master Excel.")
        info.setWordWrap(True)
        v.addWidget(info)
        form = QFormLayout()
        self.m_report, r1 = self._file_row("Kruti_Report.xlsx", lambda: self._pick_into(
            self.m_report, "Kruti_Report.xlsx"))
        self.m_missing, r2 = self._file_row("Reviewed Missing_Kruti.xlsx", lambda: self._pick_into(
            self.m_missing, "Missing_Kruti.xlsx"))
        self.m_out, r3 = self._file_row("New master file to create", self._pick_merge_out)
        form.addRow("Report", r1)
        form.addRow("Reviewed file", r2)
        form.addRow("Save new master as", r3)
        v.addLayout(form)
        self.merge_btn = QPushButton("Merge approved Kruti", objectName="primary")
        self.merge_btn.clicked.connect(self._merge)
        row = QHBoxLayout()
        row.addWidget(self.merge_btn)
        row.addStretch()
        v.addLayout(row)
        self.merge_status = QLabel("")
        self.merge_status.setWordWrap(True)
        v.addWidget(self.merge_status)
        v.addStretch()
        return page

    # ------------------------------------------------------------------ settings
    def _load_settings(self):
        s, d = self.settings, merged(None)
        self.excel_edit.setText(s.value("excel", ""))
        default_out = Path(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)) \
            / "Kruti Finder"
        self.out_edit.setText(s.value("out", str(default_out)))
        saved = s.value("books", [])
        saved = [saved] if isinstance(saved, str) else list(saved or [])  # Qt returns 1 item as str
        self.books.add_paths([p for p in saved if p and Path(p).exists()])
        self.workers_spin.setValue(int(s.value("workers", d["ocr_workers"])))
        self.threshold_spin.setValue(int(s.value("threshold", d["found_threshold"])))
        self.author_edit.setText(s.value("authors", ", ".join(d["author_keywords"])))
        self.author_only.setChecked(s.value("author_only", "false") == "true")
        self.force_ocr.setChecked(s.value("force_ocr", "false") == "true")

    def _save_settings(self):
        s = self.settings
        s.setValue("excel", self.excel_edit.text())
        s.setValue("out", self.out_edit.text())
        s.setValue("books", self.books.paths())
        s.setValue("workers", self.workers_spin.value())
        s.setValue("threshold", self.threshold_spin.value())
        s.setValue("authors", self.author_edit.text())
        s.setValue("author_only", "true" if self.author_only.isChecked() else "false")
        s.setValue("force_ocr", "true" if self.force_ocr.isChecked() else "false")

    def _config(self):
        authors = [a.strip() for a in self.author_edit.text().replace("،", ",").split(",") if a.strip()]
        return merged({
            "ocr_workers": self.workers_spin.value(),
            "found_threshold": self.threshold_spin.value(),
            "author_keywords": authors,
            "gaps_author_only": self.author_only.isChecked(),
            "force_ocr": self.force_ocr.isChecked(),
            "cache_dir": str(data_dir() / "ocr_cache"),
        })

    def _check_ocr(self):
        status = configure_ocr(merged(None))
        self.ocr_ok = status["ok"]
        self.ocr_label.setText(("✓ " if status["ok"] else "⚠ ") + status["message"])
        self.ocr_label.setToolTip(f"Tesseract: {status['tesseract']}\nModels: {status['tessdata']}")
        if not status["ok"]:
            self.ocr_label.setStyleSheet("color: #f8bb13; font-weight: 700;")

    # ------------------------------------------------------------------ pickers
    def _pick_excel(self):
        f, _ = QFileDialog.getOpenFileName(self, "Kruti Excel", self.excel_edit.text(),
                                           "Excel files (*.xlsx *.xlsm)")
        if f:
            self.excel_edit.setText(f)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDF books", "", "PDF files (*.pdf)")
        self.books.add_paths(files)

    def _add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Folder with PDF books")
        if d:
            self.books.add_paths([d])

    def _remove_selected(self):
        for item in self.books.selectedItems():
            self.books.takeItem(self.books.row(item))
        self._books_changed()

    def _clear_books(self):
        self.books.clear()
        self._books_changed()

    def _books_changed(self):
        self.pdf_count = len(collect_pdfs(self.books.paths()))
        self.books_summary.setText(f"{self.pdf_count} PDF book(s) found" if self.books.count()
                                   else "No books selected")

    def _pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "Save results to", self.out_edit.text())
        if d:
            self.out_edit.setText(d)

    def _pick_into(self, edit, name):
        start = str(Path(self.out_edit.text()))
        f, _ = QFileDialog.getOpenFileName(self, name, start, "Excel files (*.xlsx)")
        if f:
            edit.setText(f)

    def _pick_merge_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save new master as",
                                           str(Path(self.out_edit.text()) / "Kruti_Master_v2.xlsx"),
                                           "Excel files (*.xlsx)")
        if f:
            self.m_out.setText(f if f.lower().endswith(".xlsx") else f + ".xlsx")

    def _clear_cache(self):
        cache = data_dir() / "ocr_cache"
        size = sum(f.stat().st_size for f in cache.glob("*")) / 1e6 if cache.exists() else 0
        if QMessageBox.question(self, "Clear saved OCR results",
                                f"Delete {size:.1f} MB of saved page text? Books will be read "
                                "again from scratch next time.") == QMessageBox.Yes:
            shutil.rmtree(cache, ignore_errors=True)

    # ------------------------------------------------------------------ run
    def _start(self):
        excel, out = self.excel_edit.text().strip(), self.out_edit.text().strip()
        problems = []
        if not excel or not Path(excel).is_file():
            problems.append("Select the Kruti Excel file.")
        if not self.pdf_count:
            problems.append("Add at least one PDF book or a folder containing PDFs.")
        if not out:
            problems.append("Choose where to save the results.")
        if problems:
            QMessageBox.warning(self, "Kruti Finder", "\n".join(problems))
            return
        if not self.ocr_ok and QMessageBox.question(
                self, "OCR not available",
                "OCR is not available, so scanned pages will be skipped. Continue anyway?"
        ) != QMessageBox.Yes:
            return
        self._save_settings()
        run_dir = Path(out) / time.strftime("Run %Y-%m-%d %H-%M")
        self.results_bar.hide()
        self.log_view.clear()
        self._set_running(True)
        self._log(f"Output: {run_dir}")

        self.thread = QThread(self)
        self.worker = RunWorker(excel, self.books.paths(), str(run_dir), self._config())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._log)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.cancelled.connect(self._on_cancelled)
        for sig in (self.worker.finished, self.worker.failed, self.worker.cancelled):
            sig.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_thread)
        self.thread.start()

    def _set_running(self, running):
        for w in (self.start_btn, self.books, self.excel_edit, self.out_edit):
            w.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.cancel_btn.setEnabled(running)
        self.pause_btn.setText("Pause")

    def _toggle_pause(self):
        ctl = self.worker.ctl
        if ctl.paused:
            ctl.resume()
            self.pause_btn.setText("Pause")
            self._log("Resumed.")
        else:
            ctl.pause()
            self.pause_btn.setText("Resume")
            self._log("Paused. Pages in progress will finish first.")
            self.stage_label.setText("Paused")

    def _cancel(self):
        if self.worker and QMessageBox.question(
                self, "Cancel", "Stop processing? Pages already read are saved, so the next "
                                "run continues quickly.") == QMessageBox.Yes:
            self.cancel_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.stage_label.setText("Stopping after the current page…")
            self.worker.ctl.cancel()

    def _on_progress(self, p):
        if self.worker and self.worker.ctl.paused:
            return
        self.stage_label.setText(p.stage)
        self.overall_bar.setMaximum(max(1, p.pages_total))
        self.overall_bar.setValue(p.pages_done)
        self.overall_bar.setFormat(f"%p%   ·   {p.pages_done:,} / {p.pages_total:,} pages")
        self.book_bar.setMaximum(max(1, p.book_pages_total))
        self.book_bar.setValue(p.book_pages_done)
        self.book_bar.setFormat(f"%p%   ·   page {p.book_pages_done} / {p.book_pages_total}")
        if p.book_total:
            self.book_label.setText(f"Book {p.book_index} of {p.book_total}:  {p.book_name}")
        self.stats["elapsed"].setText(_fmt_time(p.elapsed))
        self.stats["eta"].setText(_fmt_time(p.eta) if p.stage != "Done" else "0m 00s")
        self.stats["ocr"].setText(f"{p.ocr_pages:,}")
        self.stats["found"].setText(f"{p.kruti_found:,}")
        self.stats["new"].setText(f"{p.new_kruti_blocks:,}")

    def _log(self, text):
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def _on_finished(self, res):
        self.result = res
        self._set_running(False)
        self.results_bar.show()
        s = res.status_counts
        msg = (f"Finished {res.books} books.\n\nExcel Kruti: {s.get('Found', 0)} found, "
               f"{s.get('Partially Found', 0)} partial, {s.get('Not Found', 0)} not found.\n"
               f"New Kruti not in the Excel: {res.new_kruti}.")
        if res.skipped:
            msg += f"\n\n{len(res.skipped)} file(s) could not be read - see the log."
        self.stats["new"].setText(f"{res.new_kruti:,}")   # after grouping copies across books
        self.m_report.setText(res.report_path)
        self.m_missing.setText(res.missing_path)
        QMessageBox.information(self, "Kruti Finder", msg)

    def _on_failed(self, err):
        self._set_running(False)
        self.stage_label.setText("Stopped with an error")
        self._log(err)
        QMessageBox.critical(self, "Kruti Finder", err.strip().splitlines()[-1] if err else "Error")

    def _on_cancelled(self):
        self._set_running(False)
        self.stage_label.setText("Cancelled - pages read so far are saved")
        self._log("Cancelled. Start again to continue; finished pages are not re-read.")

    def _cleanup_thread(self):
        if self.worker:
            self.worker.deleteLater()
        if self.thread:
            self.thread.deleteLater()
        self.worker = self.thread = None

    # ------------------------------------------------------------------ merge
    def _merge(self):
        rep, miss, out = (e.text().strip() for e in (self.m_report, self.m_missing, self.m_out))
        if not (Path(rep).is_file() and Path(miss).is_file() and out):
            QMessageBox.warning(self, "Merge", "Select the report, the reviewed file and where "
                                               "to save the new master.")
            return
        self.merge_btn.setEnabled(False)
        self.merge_status.setText("Merging…")
        self._m_thread = QThread(self)
        self._m_worker = MergeWorker(rep, miss, out)
        self._m_worker.moveToThread(self._m_thread)
        self._m_thread.started.connect(self._m_worker.run)
        self._m_worker.finished.connect(self._merge_done)
        self._m_worker.failed.connect(self._merge_failed)
        self._m_worker.finished.connect(self._m_thread.quit)
        self._m_worker.failed.connect(self._m_thread.quit)
        self._m_thread.start()

    def _merge_done(self, added, total):
        self.merge_btn.setEnabled(True)
        self.merge_status.setText(f"Added {added} approved Kruti. The new master has {total} "
                                  f"rows:\n{self.m_out.text()}")
        _open(Path(self.m_out.text()).parent)

    def _merge_failed(self, err):
        self.merge_btn.setEnabled(True)
        self.merge_status.setText("Merge failed.")
        QMessageBox.critical(self, "Merge", err)

    # ------------------------------------------------------------------ close
    def closeEvent(self, e):
        if self.worker:
            if QMessageBox.question(self, "Kruti Finder", "Processing is running. Stop and "
                                                          "quit?") != QMessageBox.Yes:
                e.ignore()
                return
            self.worker.ctl.cancel()
            self.thread.quit()
            self.thread.wait(15000)
        self._save_settings()
        e.accept()
