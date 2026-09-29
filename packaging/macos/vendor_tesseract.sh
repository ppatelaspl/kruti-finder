#!/usr/bin/env bash
# Copy Homebrew's Tesseract and every library it needs into vendor/tesseract, rewriting
# library paths so it runs from inside the app on Macs without Homebrew.
set -euo pipefail
cd "$(dirname "$0")/../.."
DST=vendor/tesseract
rm -rf "$DST" && mkdir -p "$DST/libs"
cp "$(brew --prefix tesseract)/bin/tesseract" "$DST/"
chmod u+w "$DST/tesseract"
dylibbundler -of -b -x "$DST/tesseract" -d "$DST/libs/" -p @executable_path/libs/
# Apple silicon refuses to run modified binaries without at least an ad-hoc signature
codesign --force -s - "$DST"/libs/*.dylib
codesign --force -s - "$DST/tesseract"
LEFT=$(otool -L "$DST/tesseract" "$DST"/libs/*.dylib | grep -E "^[[:space:]]+/(opt|usr/local)/" || true)
if [ -n "$LEFT" ]; then echo "Homebrew library references remain:"; echo "$LEFT"; exit 1; fi
"$DST/tesseract" --version
