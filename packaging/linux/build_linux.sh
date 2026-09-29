#!/usr/bin/env bash
# Build the Linux app and .deb inside a Debian 11 container (glibc 2.31).
#
# PyInstaller copies the build machine's system libraries into the app, so the app only
# runs where glibc is at least as new as the build machine's. Debian 11 is older than every
# supported target: Ubuntu 20.04+, Linux Mint 20+, LMDE 6+, Debian 11+.
#
#   docker run --rm --platform linux/amd64 -v "$PWD:/src" -w /src python:3.12-slim-bullseye \
#       packaging/linux/build_linux.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

# Debian 11 security updates were withdrawn when its LTS ended (Aug 2026); the main
# archive is still served. Only the build machine uses this repo list.
rm -f /etc/apt/sources.list.d/debian.sources
echo "deb http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
  binutils tesseract-ocr libgl1 libegl1 libglib2.0-0 libfontconfig1 libdbus-1-3 \
  libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 >/dev/null

python -m pip install -q --upgrade pip
pip install -q -r requirements.txt -r packaging/requirements-build.txt
python packaging/fetch_tessdata.py
pyinstaller packaging/kruti_finder.spec --noconfirm

QT_QPA_PLATFORM=offscreen dist/KrutiFinder/KrutiFinder \
  --selftest selftest.json packaging/selftest_devanagari.png || { cat selftest.json; exit 1; }
cat selftest.json

./packaging/linux/build_deb.sh
