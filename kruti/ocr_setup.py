"""Find the Tesseract program and language models.

Installed app: both ship inside the app (Windows/Mac), or Tesseract comes from the system
package and the models ship inside the app (Linux .deb). From source: system Tesseract.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_LANGS = ("hin", "guj", "san")


def resource_dir() -> Path:
    """Folder holding bundled resources (PyInstaller) or the project root (source)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _bundled(name: str) -> Path | None:
    """A resource folder inside the app, or under vendor/ when running from source."""
    for base in (resource_dir(), resource_dir() / "vendor"):
        if (base / name).exists():
            return (base / name).resolve()   # real path: macOS resolves @executable_path from it
    return None


def _bundled_tesseract() -> str | None:
    folder = _bundled("tesseract")
    exe = folder / ("tesseract.exe" if sys.platform == "win32" else "tesseract") if folder else None
    return str(exe) if exe and exe.exists() else None


def configure_ocr(cfg: dict) -> dict:
    """Point pytesseract at the right program/models. Returns a status dict."""
    import pytesseract

    cmd = cfg.get("tesseract_cmd") or _bundled_tesseract() or shutil.which("tesseract")
    if not cmd and sys.platform == "win32":
        default = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        cmd = str(default) if default.exists() else None
    tessdata = _bundled("tessdata")
    if tessdata and (tessdata / "hin.traineddata").exists():
        os.environ["TESSDATA_PREFIX"] = str(tessdata)

    status = {"tesseract": cmd, "tessdata": os.environ.get("TESSDATA_PREFIX", "system"),
              "ok": False, "message": ""}
    if not cmd:
        status["message"] = "Tesseract OCR not found. Scanned pages cannot be read."
        return status
    pytesseract.pytesseract.tesseract_cmd = cmd
    try:
        kwargs = {"capture_output": True, "text": True, "timeout": 30}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        out = subprocess.run([cmd, "--list-langs"], **kwargs)
        langs = set((out.stdout + out.stderr).split())
        missing = [lang for lang in REQUIRED_LANGS if lang not in langs]
        if missing:
            status["message"] = "OCR language models missing: " + ", ".join(missing)
        else:
            status["ok"] = True
            status["message"] = "OCR ready (Hindi, Gujarati, Sanskrit)"
    except Exception as e:  # noqa: BLE001 - report any launch failure to the user
        status["message"] = f"Tesseract could not start: {e}"
    return status
