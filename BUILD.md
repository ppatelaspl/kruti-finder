# Building the installers

Installers are built automatically by **GitHub Actions** on real Windows, macOS (Apple silicon) and Ubuntu machines (`.github/workflows/build.yml`).

## One-time setup

1. Create a **private** GitHub repository and push this folder to it (the `main` branch).
2. That's all: GitHub-hosted runners are free for private repos within the monthly minutes quota. One full build uses roughly 30–40 minutes, with macOS minutes counted at 10×.

## Every build

- **Every push to `main`** builds all three installers. Download them from *Actions* → the run → *Artifacts*.
- **Tagging a version** also publishes a Release with the three installers attached:

  ```bash
  # bump app/version.py first, e.g. __version__ = "1.0.1"
  git commit -am "v1.0.1" && git tag v1.0.1 && git push && git push --tags
  ```

Each build runs a **self-test** on its own platform. The packaged app must start, find Tesseract and the Hindi/Gujarati/Sanskrit models, and correctly OCR a Devanagari sample image. A build that fails the self-test produces no installer.

## What each platform bundles

| | Tesseract program | Language models | Installer |
|---|---|---|---|
| Windows | UB-Mannheim build (Chocolatey), copied into the app | bundled | Inno Setup `.exe` |
| macOS | built from source by `packaging/macos/build_tesseract.sh` (one static binary, macOS 11+) | bundled | `.dmg` |
| Linux | distro `tesseract-ocr` (declared dependency) | bundled | `.deb`, built on Debian 11 |

The Linux app is built inside a Debian 11 container (`packaging/linux/build_linux.sh`): PyInstaller copies the build machine's system libraries into the app, so an older build machine means the app runs on more distros (Ubuntu 20.04+, Mint 20+, LMDE 6+, Debian 11+). The `linux-test` job installs the `.deb` on each of those and opens the app. PySide6 is pinned in `packaging/requirements-build.txt` because newer Qt versions drop macOS 11/12 and Ubuntu 20.04.

The Linux package maintainer field can be set with the `DEB_MAINTAINER` environment variable.

## Running from source (developers)

```bash
pip install -r requirements.txt -r packaging/requirements-build.txt
python packaging/fetch_tessdata.py         # downloads models into vendor/tessdata
python app/main.py                          # desktop app
python kruti_finder.py run --excel X.xlsx --books ./books --out ./output   # command line
```

Local build on your own OS: `pyinstaller packaging/kruti_finder.spec --noconfirm`, then the matching script in `packaging/<os>/`.
