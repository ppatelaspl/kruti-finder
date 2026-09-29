#!/usr/bin/env bash
# Build Tesseract from source into vendor/tesseract/tesseract as one self-contained arm64
# binary that runs on macOS 11 Big Sur and newer (every Apple-silicon Mac).
#
# Homebrew's bottles only run on the macOS version they were built for (the build runner's),
# so they cannot be shipped. Leptonica, libpng and libtesseract are linked statically; the
# binary depends only on libraries that are part of macOS itself.
# Needs: cmake, Xcode command line tools.
set -euo pipefail
cd "$(dirname "$0")/../.."

TESSERACT=5.5.3
LEPTONICA=1.87.0
LIBPNG=1.6.53
export MACOSX_DEPLOYMENT_TARGET=11.0

ROOT=$PWD
WORK=$ROOT/build/tesseract-src
PREFIX=$WORK/prefix
DST=$ROOT/vendor/tesseract
JOBS=$(sysctl -n hw.ncpu)
# Never pick up Homebrew's copies of zlib/libpng/etc.: they only run on newer macOS.
CMAKE_COMMON=(-DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64
              -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET
              -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_PREFIX_PATH="$PREFIX"
              -DCMAKE_IGNORE_PREFIX_PATH="/opt/homebrew;/usr/local;/opt/local"
              -DBUILD_SHARED_LIBS=OFF)
export PKG_CONFIG_PATH="" PKG_CONFIG_LIBDIR="$PREFIX/lib/pkgconfig"

fetch() {   # url dir
  [ -d "$WORK/$2" ] && return
  mkdir -p "$WORK/$2"
  curl -fsSL "$1" | tar xz -C "$WORK/$2" --strip-components 1
}
fetch "https://github.com/pnggroup/libpng/archive/refs/tags/v$LIBPNG.tar.gz" libpng
fetch "https://github.com/DanBloomberg/leptonica/releases/download/$LEPTONICA/leptonica-$LEPTONICA.tar.gz" leptonica
fetch "https://github.com/tesseract-ocr/tesseract/archive/refs/tags/$TESSERACT.tar.gz" tesseract

cmake -S "$WORK/libpng" -B "$WORK/libpng/build" "${CMAKE_COMMON[@]}" \
  -DPNG_SHARED=OFF -DPNG_TESTS=OFF -DPNG_TOOLS=OFF -DPNG_FRAMEWORK=OFF
cmake --build "$WORK/libpng/build" -j "$JOBS" --target install

# PNG (pytesseract's default) and PNM (what the app sends) are all Tesseract needs to read.
cmake -S "$WORK/leptonica" -B "$WORK/leptonica/build" "${CMAKE_COMMON[@]}" \
  -DENABLE_ZLIB=ON -DENABLE_PNG=ON -DENABLE_GIF=OFF -DENABLE_JPEG=OFF -DENABLE_TIFF=OFF \
  -DENABLE_WEBP=OFF -DENABLE_OPENJPEG=OFF -DBUILD_PROG=OFF -DSW_BUILD=OFF
cmake --build "$WORK/leptonica/build" -j "$JOBS" --target install

cmake -S "$WORK/tesseract" -B "$WORK/tesseract/build" "${CMAKE_COMMON[@]}" \
  -DBUILD_TRAINING_TOOLS=OFF -DBUILD_TESTS=OFF -DGRAPHICS_DISABLED=ON -DDISABLE_ARCHIVE=ON \
  -DDISABLE_CURL=ON -DOPENMP_BUILD=OFF -DSW_BUILD=OFF -DENABLE_NATIVE=OFF
cmake --build "$WORK/tesseract/build" -j "$JOBS" --target tesseract

rm -rf "$DST" && mkdir -p "$DST"
cp "$WORK/tesseract/build/bin/tesseract" "$DST/tesseract" 2>/dev/null \
  || cp "$WORK/tesseract/build/tesseract" "$DST/tesseract"
strip -x "$DST/tesseract"
codesign --force -s - "$DST/tesseract"   # Apple silicon only runs signed code (ad-hoc is enough)

# Guard: nothing may point outside macOS itself, and the minimum OS must be 11.0.
LEFT=$(otool -L "$DST/tesseract" | tail -n +2 | grep -vE "^[[:space:]]+(/usr/lib/|/System/)" || true)
if [ -n "$LEFT" ]; then echo "Non-system library references remain:"; echo "$LEFT"; exit 1; fi
MINOS=$(otool -l "$DST/tesseract" | awk '/LC_BUILD_VERSION/{f=1} f&&/minos/{print $2; exit}')
if [ "$MINOS" != "$MACOSX_DEPLOYMENT_TARGET" ]; then echo "minos is $MINOS"; exit 1; fi
"$DST/tesseract" --version
