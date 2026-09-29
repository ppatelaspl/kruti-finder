#!/usr/bin/env bash
# Build kruti-finder_<version>_amd64.deb from dist/KrutiFinder (PyInstaller output).
# Tesseract comes from the distribution (declared dependency, installed by apt);
# the Hindi/Gujarati/Sanskrit models are bundled inside the app.
set -euo pipefail
cd "$(dirname "$0")/../.."
VERSION=$(python3 -c "import re;print(re.search(r'\"(.+)\"',open('app/version.py').read()).group(1))")
PKG=build/deb/kruti-finder
rm -rf "$PKG" && mkdir -p "$PKG/DEBIAN" "$PKG/opt" "$PKG/usr/bin" \
  "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/512x512/apps"
cp -r dist/KrutiFinder "$PKG/opt/kruti-finder"
ln -s /opt/kruti-finder/KrutiFinder "$PKG/usr/bin/kruti-finder"
python3 -c "from PIL import Image; Image.open('app/assets/icon.png').resize((512,512)).save('$PKG/usr/share/icons/hicolor/512x512/apps/kruti-finder.png')"
cat > "$PKG/usr/share/applications/kruti-finder.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Kruti Finder
Comment=Map Kruti to books and find Kruti not yet in the Excel
Exec=/opt/kruti-finder/KrutiFinder
Icon=kruti-finder
Categories=Office;Education;
Terminal=false
DESK
SIZE=$(du -sk "$PKG" | cut -f1)
cat > "$PKG/DEBIAN/control" <<CTRL
Package: kruti-finder
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Installed-Size: $SIZE
Maintainer: ${DEB_MAINTAINER:-Aspire Softserv Pvt. Ltd. <support@aspiresoftserv.com>}
Depends: tesseract-ocr, libxcb-cursor0, libxkbcommon-x11-0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0, libxcb-xkb1, libegl1, libgl1, libfontconfig1, libdbus-1-3
Description: Kruti Finder
 Maps Kruti (Aadi/Ant Vakya) from an Excel to pages in PDF books and lists
 Kruti found in the books that are not yet in the Excel.
CTRL
mkdir -p dist/installers
dpkg-deb --build --root-owner-group "$PKG" "dist/installers/kruti-finder_${VERSION}_amd64.deb"
echo "Built dist/installers/kruti-finder_${VERSION}_amd64.deb"
