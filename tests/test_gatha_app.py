"""Gatha Lines: the app's second tab.   Run:  QT_QPA_PLATFORM=offscreen python -m pytest tests"""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

QtWidgets = pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def window():
    from PySide6.QtCore import QCoreApplication

    QCoreApplication.setOrganizationName("Aspire Softserv Test")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from app.window import MainWindow
    w = MainWindow()
    yield w
    w.close()


def test_tabs_and_lock(window):
    tabs = window.tabs
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Find Kruti (Excel match)", "Gatha Lines"]
    assert window.excel_edit is not None and window.start_btn is not None   # feature 1 intact
    gt = window.gatha_tab
    gt.set_locked(True)
    assert not gt.start_btn.isEnabled()
    gt.set_locked(False)
    assert gt.start_btn.isEnabled()


def test_gatha_tab_has_the_run_controls(window):
    gt = window.gatha_tab
    for name in ("books", "out_edit", "start_btn", "pause_btn", "cancel_btn", "overall_bar",
                 "book_bar", "log_view", "open_results_btn"):
        assert getattr(gt, name) is not None, name
    assert set(gt.stats) == {"elapsed", "eta", "ocr", "found", "gathas"}


def test_feature_one_run_locks_the_gatha_tab(window):
    window._set_running(True)
    assert not window.gatha_tab.start_btn.isEnabled()
    window._set_running(False)
    assert window.gatha_tab.start_btn.isEnabled()


def test_gatha_workers_setting_is_its_own(window):
    gt = window.gatha_tab
    gt.settings.setValue("workers", 3)
    gt.workers_spin.setValue(5)
    gt.save_settings()
    assert int(gt.settings.value("workers")) == 3          # feature 1's value is untouched
    assert int(gt.settings.value("gatha/workers")) == 5
