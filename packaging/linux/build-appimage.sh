#!/usr/bin/env bash
# PyInstaller の出力（dist/OtoType）から AppImage を作る。
#   bash packaging/linux/build-appimage.sh 0.1.0
set -euo pipefail

VERSION="$1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPDIR="$ROOT/build/AppDir"
TOOL="$ROOT/build/appimagetool"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib"
cp -a "$ROOT/dist/OtoType" "$APPDIR/usr/lib/"
python "$ROOT/scripts/make_icon.py" "$APPDIR/ototype.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/OtoType/OtoType" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/ototype.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=OtoType
Comment=ローカルで動く日本語音声入力
Exec=ototype
Icon=ototype
Categories=Utility;Accessibility;
Terminal=false
EOF

if [ ! -x "$TOOL" ]; then
  mkdir -p "$(dirname "$TOOL")"
  curl -fsSL -o "$TOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
# GitHub Actions のランナーには FUSE がないため、展開して実行する
ARCH=x86_64 "$TOOL" --appimage-extract-and-run "$APPDIR" \
  "$ROOT/dist/ototype-$VERSION-linux-x86_64.AppImage"
