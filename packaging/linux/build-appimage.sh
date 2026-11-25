#!/usr/bin/env bash
# PyInstaller の出力（dist/PrivDicta）から AppImage を作る。
#   bash packaging/linux/build-appimage.sh 0.1.0
set -euo pipefail

VERSION="$1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPDIR="$ROOT/build/AppDir"
TOOL="$ROOT/build/appimagetool"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib"
cp -a "$ROOT/dist/PrivDicta" "$APPDIR/usr/lib/"
python "$ROOT/scripts/make_icon.py" "$APPDIR/privdicta.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/PrivDicta/PrivDicta" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/privdicta.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=PrivDicta
Comment=ローカルで動く日本語音声入力
Exec=privdicta
Icon=privdicta
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
  "$ROOT/dist/privdicta-$VERSION-linux-x86_64.AppImage"
