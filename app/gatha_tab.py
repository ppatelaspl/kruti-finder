"""The "Gatha Lines" tab: list every multi-gatha Kruti in the books with the first and last
line of each gatha. Same controls as the Excel-match tab, no Excel needed."""
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from kruti.gatha_lines import gatha_config
from kruti.pipeline import collect_pdfs

from .worker import GathaWorker


class GathaTab(QWidget):
    busy_changed = Signal(bool)           # a run started / ended: lock the other tab

    def __init__(self, settings, data_dir, books_list_cls, open_path, fmt_time, ocr_ok):
        super().__init__(objectName="page")
        self.settings, self.data_dir = settings, data_dir
        self._open, self._fmt_time, self._ocr_ok = open_path, fmt_time, ocr_ok
        self.thread = self.worker = self.result = None
        self.pdf_count, self._locked = 0, False
        v = QVBoxLayout(self)

        intro = QLabel("Lists every Kruti of two or more gathas in the books, with the first and "
                       "last line of each gatha. Prefaces, explanations, indexes and notes are "
                       "left out. No Excel is needed.")
        intro.setWordWrap(True)
        v.addWidget(intro)

        g1 = QGroupBox("1.  PDF books: pick files, a folder, or drag them here")
        g1v = QVBoxLayout(g1)
        self.books = books_list_cls(self._books_changed)
        self.books.setMinimumHeight(90)
        g1v.addWidget(self.books)
        btns = QHBoxLayout()
        for text, slot in (("Add PDF files…", self._add_files), ("Add folder…", self._add_folder),
                           ("Remove selected", self._remove_selected), ("Clear", self._clear_books)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch()
        self.books_summary = QLabel("No books selected")
        btns.addWidget(self.books_summary)
        g1v.addLayout(btns)
        v.addWidget(g1)

        g2 = QGroupBox("2.  Save results to")
        row = QHBoxLayout(g2)
        self.out_edit = QLineEdit(placeholderText="Output folder…")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._pick_out)
        row.addWidget(self.out_edit, 1)
        row.addWidget(browse)
        v.addWidget(g2)

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
        self.open_results_btn.clicked.connect(lambda: self._open(self.result.results_path))
        self.open_folder_btn.clicked.connect(
            lambda: self._open(Path(self.result.results_path).parent))
        rb.addWidget(self.open_results_btn)
        rb.addWidget(self.open_folder_btn)
        rb.addStretch()
        self.results_bar.hide()
        v.addWidget(self.results_bar)
        self._load_settings()

    # ------------------------------------------------------------------ layout
    def _advanced(self):
        box = QGroupBox("Advanced settings")
        box.setCheckable(True)
        box.setChecked(False)
        inner = QWidget()
        form = QFormLayout(inner)
        import os
        self.workers_spin = QSpinBox(minimum=1, maximum=max(1, os.cpu_count() or 1))
        clear = QPushButton("Clear saved page layouts")
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
                                          ("ocr", "Pages OCR'd"), ("found", "Kruti found"),
                                          ("gathas", "Gathas found"))):
            val = QLabel("–", objectName="stat")
            c = QVBoxLayout()
            c.addWidget(val)
            c.addWidget(QLabel(cap, objectName="statcap"))
            g.addLayout(c, 4, col)
            self.stats[key] = val
        return box

    # ------------------------------------------------------------------ settings
    def _load_settings(self):
        s = self.settings
        default_out = Path(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)) \
            / "Kruti Finder"
        self.out_edit.setText(s.value("gatha/out", str(default_out)))
        saved = s.value("gatha/books", [])
        saved = [saved] if isinstance(saved, str) else list(saved or [])
        self.books.add_paths([p for p in saved if p and Path(p).exists()])
        self.workers_spin.setValue(int(s.value("workers", gatha_config(None)["ocr_workers"])))

    def save_settings(self):
        self.settings.setValue("gatha/out", self.out_edit.text())
        self.settings.setValue("gatha/books", self.books.paths())
        self.settings.setValue("workers", self.workers_spin.value())

    def _config(self):
        return gatha_config({"ocr_workers": self.workers_spin.value(),
                             "layout_cache_dir": str(self.data_dir() / "layout_cache")})

    # ------------------------------------------------------------------ pickers
    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PDF books", "", "PDF files (*.pdf)")
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
        self.books_summary.setText(f"{self.pdf_count} PDF book(s)" if self.pdf_count
                                   else "No books selected")

    def _pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "Save results to", self.out_edit.text())
        if d:
            self.out_edit.setText(d)

    def _clear_cache(self):
        cache = self.data_dir() / "layout_cache"
        size = sum(f.stat().st_size for f in cache.glob("*")) / 1e6 if cache.exists() else 0
        if QMessageBox.question(self, "Clear saved page layouts",
                                f"Delete {size:.1f} MB of saved page layouts? Books will be read "
                                "again from scratch next time.") == QMessageBox.Yes:
            shutil.rmtree(cache, ignore_errors=True)

    # ------------------------------------------------------------------ run
    @property
    def running(self):
        return self.worker is not None

    def set_locked(self, locked: bool):
        """The other tab is running: only one run at a time."""
        self._locked = locked
        self.start_btn.setEnabled(not locked and not self.running)

    def _start(self):
        out = self.out_edit.text().strip()
        problems = []
        if not self.pdf_count:
            problems.append("Add at least one PDF book or a folder containing PDFs.")
        if not out:
            problems.append("Choose where to save the results.")
        if problems:
            QMessageBox.warning(self, "Gatha Lines", "\n".join(problems))
            return
        if not self._ocr_ok() and QMessageBox.question(
                self, "OCR not available",
                "OCR is not available, so scanned pages will be skipped. Continue anyway?"
        ) != QMessageBox.Yes:
            return
        self.save_settings()
        run_dir = Path(out) / time.strftime("Gatha Run %Y-%m-%d %H-%M")
        self.results_bar.hide()
        self.log_view.clear()
        self._reset_progress()
        self.thread = QThread(self)
        self.worker = GathaWorker(self.books.paths(), str(run_dir), self._config())
        self._set_running(True)
        self._log(f"Output: {run_dir}")
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
        for w in (self.books, self.out_edit):
            w.setEnabled(not running)
        self.start_btn.setEnabled(not running and not self._locked)
        self.pause_btn.setEnabled(running)
        self.cancel_btn.setEnabled(running)
        self.pause_btn.setText("Pause")
        self.busy_changed.emit(running)

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

    def stop_for_exit(self):
        if self.worker:
            self.worker.ctl.cancel()
            self.thread.quit()
            self.thread.wait(15000)
        self.save_settings()

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
        self.stats["elapsed"].setText(self._fmt_time(p.elapsed))
        self.stats["eta"].setText(self._fmt_time(p.eta) if p.stage != "Done" else "0m 00s")
        self.stats["ocr"].setText(f"{p.ocr_pages:,}")
        self.stats["found"].setText(f"{p.kruti_found:,}")
        self.stats["gathas"].setText(f"{getattr(p, 'gathas_found', 0):,}")

    def _log(self, text):
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def _on_finished(self, res):
        self.result = res
        self.results_bar.show()
        msg = f"Finished {res.books} books.\n\n{res.krutis:,} Kruti found, {res.gathas:,} gathas."
        if res.skipped:
            msg += f"\n\n{len(res.skipped)} file(s) could not be read - see the log."
        QMessageBox.information(self, "Gatha Lines", msg)

    def _on_failed(self, err):
        self.stage_label.setText("Stopped with an error")
        self._log(err)
        QMessageBox.critical(self, "Gatha Lines", err.strip().splitlines()[-1] if err else "Error")

    def _on_cancelled(self):
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
        self._set_running(False)
