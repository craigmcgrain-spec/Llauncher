"""QApplication entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from llauncher.config import load_settings
from llauncher.main_window import MainWindow


def find_icon() -> Path | None:
    """Locate assets/icon.png in dev checkout, installed package, or hicolor theme."""
    candidates: list[Path] = []
    # 1. installed wheel data (importlib.resources): llauncher/data/icon.png
    try:
        from importlib.resources import files as _files

        res = _files("llauncher") / "data" / "icon.png"
        # files() may be a Traversable; stringify only if it exists on disk
        try:
            if res.is_file():  # type: ignore[attr-defined]
                candidates.append(Path(str(res)))
        except Exception:
            pass
    except Exception:
        pass
    # 2. dev checkout: <repo>/assets/icon.png (src/llauncher/app.py -> ../../..)
    try:
        repo_root = Path(__file__).resolve().parents[2]
        # src layout: parents[2] of src/llauncher/app.py is repo root
        candidates.append(repo_root / "assets" / "icon.png")
        # alt layout if package installed differently
        candidates.append(repo_root.parent / "assets" / "icon.png")
    except Exception:
        pass
    # XDG data dirs (after `install-icons.sh` / make install)
    import os

    for base in (
        os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")),
        "/usr/local/share",
        "/usr/share",
    ):
        candidates.append(Path(base) / "icons" / "hicolor" / "512x512" / "apps" / "llauncher.png")
    for p in candidates:
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(prog="llauncher", description="llama-server configurator and runner")
    p.add_argument("--profile", default="", help="Open with this saved profile selected")
    p.add_argument("--center", action="store_true", help="(legacy) center window on screen")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = load_settings()
    if args.profile:
        settings.last_profile = args.profile

    # High-DPI niceties
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv if argv is None else [sys.argv[0], *[]])
    app.setApplicationName("Llauncher")
    app.setQuitOnLastWindowClosed(True)
    icon_path = find_icon()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))

    win = MainWindow(settings)
    if icon_path is not None:
        win.setWindowIcon(QIcon(str(icon_path)))
    if args.center:
        screen = app.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            win.move(
                geo.center().x() - win.width() // 2,
                int(geo.y() + geo.height() * 0.25),
            )
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
