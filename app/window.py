"""Kruti Finder main window."""
import os
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QFrame, QProgressBar, QPushButton, QScrollArea, QSpinBox, QVBoxLayout,
    QWidget)

from kruti.config import merged
from kruti.ocr_setup import configure_ocr, resource_dir
from kruti.pipeline import collect_pdfs

from .version import __version__
from .worker import RunWorker


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


def _scrollable(page: QWidget) -> QScrollArea:
    area = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
    area.setWidget(page)
    return area


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
        layout.addWidget(_scrollable(self._find_tab()))
        self.setCentralWidget(root)
        # fit smaller laptop screens (e.g. 1366x768); the page scrolls when space runs out
        avail = self.screen().availableGeometry()
        self.resize(min(980, avail.width() - 40), min(860, avail.height() - 60))
        self._load_settings()
        self._check_ocr()

    # ------------------------------------------------------------------ layout
    def _header(self):
        w = QWidget(objectName="header")
        h = QHBoxLayout(w)
        h.setContentsMargins(20, 12, 20, 12)
        col = QVBoxLayout()
        col.addWidget(QLabel("Kruti Finder", objectName="title"))
        col.addWidget(QLabel("Read the books · list every Kruti · flag the ones in the Excel",
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
        self.open_results_btn = QPushButton("Open results (Excel)", objectName="primary")
        self.open_folder_btn = QPushButton("Open output folder")
        self.open_results_btn.clicked.connect(lambda: _open(self.result.results_path))
        self.open_folder_btn.clicked.connect(
            lambda: _open(Path(self.result.results_path).parent))
        for b in (self.open_results_btn, self.open_folder_btn):
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
        clear = QPushButton("Clear saved OCR results")
        clear.clicked.connect(self._clear_cache)
        form.addRow("Parallel OCR jobs", self.workers_spin)
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
                                          ("ocr", "Pages OCR'd"), ("found", "Kruti found"))):
            val = QLabel("–", objectName="stat")
            c = QVBoxLayout()
            c.addWidget(val)
            c.addWidget(QLabel(cap, objectName="statcap"))
            g.addLayout(c, 4, col)
            self.stats[key] = val
        return box

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

    def _save_settings(self):
        s = self.settings
        s.setValue("excel", self.excel_edit.text())
        s.setValue("out", self.out_edit.text())
        s.setValue("books", self.books.paths())
        s.setValue("workers", self.workers_spin.value())

    def _config(self):
        return merged({
            "ocr_workers": self.workers_spin.value(),
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
        self._reset_progress()
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

    def _log(self, text):
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def _on_finished(self, res):
        self.result = res
        self._set_running(False)
        self.results_bar.show()
        msg = (f"Finished {res.books} books.\n\n{res.places:,} Kruti found: "
               f"{res.in_excel:,} in the Excel, {res.places - res.in_excel:,} new.\n"
               f"{res.krutis:,} distinct Kruti (copies share a Group ID).")
        if res.skipped:
            msg += f"\n\n{len(res.skipped)} file(s) could not be read - see the log."
        QMessageBox.information(self, "Kruti Finder", msg)

    def _on_failed(self, err):
        self._set_running(False)
        self.stage_label.setText("Stopped with an error")
        self._log(err)
        QMessageBox.critical(self, "Kruti Finder", err.strip().splitlines()[-1] if err else "Error")

    def _on_cancelled(self):
        self._set_running(False)
        self._reset_progress()
        self._log("Cancelled. Start again to continue; finished pages are not re-read.")

    def _reset_progress(self):
        self.stage_label.setText("Ready")
        self.book_label.setText("")
        for bar in (self.overall_bar, self.book_bar):
            bar.reset()
            bar.setFormat("%p%")
        for val in self.stats.values():
            val.setText("–")

    def _cleanup_thread(self):
        if self.worker:
            self.worker.deleteLater()
        if self.thread:
            self.thread.deleteLater()
        self.worker = self.thread = None

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
