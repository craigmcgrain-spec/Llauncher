#!/usr/bin/env bash
# Build a portable Llauncher AppImage (bundled CPython + PySide6).
#
# Usage:
#   ./build-appimage.sh
# Output:
#   dist/Llauncher-x86_64.AppImage
#
# Requirements: uv, curl, appimagetool (auto-downloaded to $TOOLS_DIR).
# The result runs on any modern x86_64 Linux with libGL/libxcb present
# (standard on Fedora/KDE/GNOME desktops).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD="${BUILD_DIR:-$ROOT/.appimage-build}"
APPDIR="$BUILD/Llauncher.AppDir"
TOOLS_DIR="${TOOLS_DIR:-/tmp/opencode}"
APPIMAGETOOL="$TOOLS_DIR/appimagetool-x86_64.AppImage"
OUT="$ROOT/dist/Llauncher-x86_64.AppImage"

echo "==> clean prod venv (no dev deps)"
rm -rf "$BUILD/prod-venv"
uv venv "$BUILD/prod-venv" --python 3.13 -q
uv pip install --python "$BUILD/prod-venv/bin/python" -q "$ROOT"
BASE_PY="$(readlink -f "$BUILD/prod-venv/bin/python")"
BASE_DIR="$(dirname "$(dirname "$BASE_PY")")"
PYVER="$("$BASE_PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "    base python: $BASE_DIR ($PYVER)"

echo "==> assemble AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/python/bin" "$APPDIR/usr/python/lib" \
         "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/512x512/apps"

# interpreter + stdlib (uv standalone python is relocatable via PYTHONHOME)
cp -a "$BASE_DIR/bin/python3" "$BASE_DIR/bin/python3.13" "$BASE_DIR/bin/python${PYVER}" "$APPDIR/usr/python/bin/" 2>/dev/null || \
cp -a "$BASE_DIR/bin/python3.13" "$APPDIR/usr/python/bin/"
ln -sf python3.13 "$APPDIR/usr/python/bin/python3" 2>/dev/null || true
ln -sf python3 "$APPDIR/usr/python/bin/python" 2>/dev/null || true
cp -a "$BASE_DIR/lib/python${PYVER}" "$APPDIR/usr/python/lib/"

# app + third-party packages (lllauncher, PySide6, shiboken6)
cp -a "$BUILD/prod-venv/lib/python${PYVER}/site-packages/." "$APPDIR/usr/python/lib/python${PYVER}/site-packages/"

# entry point, desktop file, icons
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
# Llauncher AppRun: bundled CPython + PySide6, no host python required.
HERE="$(dirname "$(readlink -f "$0")")"
PYDIR="$HERE/usr/python"
SP="$PYDIR/lib/python3.13/site-packages"
# allow other 3.13.x layouts just in case
[ -d "$SP" ] || SP="$(echo "$PYDIR"/lib/python3*/site-packages)"
export PYTHONHOME="$PYDIR"
export PYTHONPATH="$SP"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PATH="$PYDIR/bin:$PATH"
export QT_QPA_PLATFORM_PLUGIN_PATH="$SP/PySide6/Qt/plugins"
export QT_PLUGIN_PATH="$SP/PySide6/Qt/plugins"
export QML2_IMPORT_PATH="$SP/PySide6/Qt/qml"
# debug escape hatch: ./Llauncher*.AppImage --llauncher-python -c "..."
if [ "${1:-}" = "--llauncher-python" ]; then
  shift
  exec "$PYDIR/bin/python3" "$@"
fi
exec "$PYDIR/bin/python3" -m llauncher "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/llauncher.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Llauncher
Comment=llama-server configurator and runner
Exec=llauncher
Icon=llauncher
Categories=Utility;
Terminal=false
StartupNotify=true
EOF
cp -f "$APPDIR/llauncher.desktop" "$APPDIR/usr/share/applications/"
cp -f "$ROOT/assets/icon.png" "$APPDIR/llauncher.png"
cp -f "$ROOT/assets/icon.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/llauncher.png"
ln -sf llauncher.png "$APPDIR/.DirIcon"

echo "==> sanity: bundled interpreter imports the app stack"
PYTHONHOME="$APPDIR/usr/python" \
PYTHONPATH="$APPDIR/usr/python/lib/python${PYVER}/site-packages" \
PYTHONNOUSERSITE=1 \
"$APPDIR/usr/python/bin/python3" -c "import llauncher.app, PySide6.QtWidgets; print('import ok')"

echo "==> download appimagetool if missing"
if [ ! -x "$APPIMAGETOOL" ]; then
  mkdir -p "$TOOLS_DIR"
  curl -sSL -o "$APPIMAGETOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$APPIMAGETOOL"
fi

echo "==> build AppImage"
mkdir -p "$ROOT/dist"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUT"
ls -la "$OUT"
echo "done: $OUT"
