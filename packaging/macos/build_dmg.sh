#!/usr/bin/env bash
# Ad-hoc sign the app bundle (required on Apple silicon) and wrap it in a .dmg.
set -euo pipefail
cd "$(dirname "$0")/../.."
VERSION=$(python3 -c "import re;print(re.search(r'\"(.+)\"',open('app/version.py').read()).group(1))")
APP="dist/Kruti Finder.app"
codesign --force --deep -s - "$APP"
mkdir -p dist/dmg dist/installers
rm -rf dist/dmg/*
cp -R "$APP" dist/dmg/
ln -s /Applications dist/dmg/Applications
hdiutil create -volname "Kruti Finder" -srcfolder dist/dmg -ov -format UDZO \
  "dist/installers/KrutiFinder-${VERSION}-mac-apple-silicon.dmg"
