#!/usr/bin/env bash
# Install the .deb on a clean distro and check the app works there:
# apt must resolve every dependency, the OCR self-test must pass, and the window must open.
#
#   docker run --rm --platform linux/amd64 -v "$PWD:/src" -w /src ubuntu:20.04 \
#       packaging/linux/test_deb.sh dist/installers/kruti-finder_1.0.0_amd64.deb
set -euo pipefail
DEB=$(realpath "$1")
export DEBIAN_FRONTEND=noninteractive
. /etc/os-release && echo "== $PRETTY_NAME"

apt-get update -qq
apt-get install -y -qq "$DEB" xvfb xauth >/dev/null
dpkg -s kruti-finder | grep -E "^(Status|Version)"

kruti-finder --selftest /tmp/selftest.json "$(dirname "$0")/../selftest_devanagari.png" \
  || { cat /tmp/selftest.json; exit 1; }
python3 -c "import json;r=json.load(open('/tmp/selftest.json'));print('selftest ok:',r['ok'],'-',r['ocr']['message'],'-',r['ocr']['tessdata'])" \
  2>/dev/null || cat /tmp/selftest.json
# Tesseract 4.x runs the best models ~2.5x slower: the app must pick the fast ones there
if tesseract --version 2>&1 | grep -qE "^tesseract v?4\." && ! grep -q tessdata_fast /tmp/selftest.json; then
  echo "Tesseract 4 but not using the fast models"; exit 1; fi

# The real window, on the real xcb platform plugin. Still running after 10 s = it started.
xvfb-run -a -s "-screen 0 1280x800x24" bash -c '
  kruti-finder > /tmp/gui.log 2>&1 & pid=$!
  sleep 10
  if kill -0 $pid 2>/dev/null; then kill $pid; echo "window: started"; else
    echo "window: FAILED"; cat /tmp/gui.log; exit 1; fi'
