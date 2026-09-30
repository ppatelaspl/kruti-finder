# PyInstaller build spec - run from the project root:
#     pyinstaller packaging/kruti_finder.spec --noconfirm
# Expects vendor/tessdata (packaging/fetch_tessdata.py) and, on Windows/macOS,
# vendor/tesseract (the Tesseract program + its libraries; see .github/workflows/build.yml).
import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
VERSION = re.search(r'"(.+)"', (ROOT / "app" / "version.py").read_text()).group(1)

datas = [(str(ROOT / "app" / "assets"), "app/assets"),
         (str(ROOT / "vendor" / "tessdata"), "tessdata")]
if (ROOT / "vendor" / "tessdata_fast").exists():          # Linux: for Tesseract 4.x
    datas.append((str(ROOT / "vendor" / "tessdata_fast"), "tessdata_fast"))
if (ROOT / "vendor" / "tesseract").exists():
    datas.append((str(ROOT / "vendor" / "tesseract"), "tesseract"))

a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=["kruti.selftest"],
    excludes=["tkinter", "pandas", "numpy", "matplotlib", "scipy", "IPython",
              "fontTools", "lxml", "chardet", "charset_normalizer", "yaml",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
              "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts",
              "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtNetwork"],
    noarchive=False,
)
# Qt pulls in modules the app never uses (QML/Quick, PDF, virtual keyboard) through
# plugins; bundled GTK libraries on Linux clash with the system's. Drop them.
_DROP = re.compile(r"(Qt6?(Quick|Qml|Pdf|VirtualKeyboard|Network|Svg)|qtvirtualkeyboard|"
                   r"platforminputcontexts|imageformats[/\\]libqpdf|imageformats[/\\]qpdf|"
                   r"platformthemes[/\\]libqgtk3|libgtk-3|libgdk-3|libatk|__mypyc)", re.I)
a.binaries = [b for b in a.binaries if not _DROP.search(b[0])]
a.datas = [d for d in a.datas if not _DROP.search(d[0])]

pyz = PYZ(a.pure)

icon = {"win32": "icon.ico", "darwin": "icon.icns"}.get(sys.platform, "icon.png")
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="KrutiFinder",
    console=False,
    icon=str(ROOT / "app" / "assets" / icon),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="KrutiFinder", upx=False)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Kruti Finder.app",
        icon=str(ROOT / "app" / "assets" / "icon.icns"),
        bundle_identifier="com.aspiresoftserv.krutifinder",
        info_plist={
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",   # every Apple-silicon Mac
        },
    )
