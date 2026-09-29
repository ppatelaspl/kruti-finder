"""Kruti Finder desktop app - entry point."""
import os
import sys
from pathlib import Path

# Windowed builds have no console; some libraries still write to stdout/stderr.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

if not getattr(sys, "frozen", False):          # running from source
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QFontDatabase, QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication      # noqa: E402

from app.style import QSS                        # noqa: E402
from app.window import MainWindow                # noqa: E402
from kruti.ocr_setup import resource_dir        # noqa: E402


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        from kruti.selftest import run_selftest
        sys.exit(run_selftest(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    app = QApplication(sys.argv)
    app.setApplicationName("Kruti Finder")
    app.setOrganizationName("Aspire Softserv")
    assets = resource_dir() / "app" / "assets"
    for weight in ("Regular", "SemiBold", "Bold"):
        QFontDatabase.addApplicationFont(str(assets / f"Outfit-{weight}.ttf"))
    app.setWindowIcon(QIcon(str(assets / "icon.png")))
    app.setStyle("Fusion")                       # same look on Windows, Mac and Linux
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
