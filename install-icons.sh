#!/usr/bin/env bash
# Install Llauncher icons into the hicolor theme (~/.local/share/icons by default).
# Follows freedesktop.org Icon Theme Specification.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${1:-$HOME/.local/share}"

for size in 16 32 48 64 128 256 512; do
  src="$REPO_DIR/assets/icons/hicolor/${size}x${size}/apps/llauncher.png"
  dst="$PREFIX/icons/hicolor/${size}x${size}/apps/llauncher.png"
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
  echo "installed $dst"
done

# legacy fallback absolute-path icon (used by llauncher.desktop in dev)
# (desktop file already points at assets/icon.png; no copy needed for dev)

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$PREFIX/icons/hicolor" || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" || true
fi
echo "done. Icon name: llauncher"
