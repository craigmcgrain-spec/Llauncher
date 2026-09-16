"""Discover launchable apps: .desktop files + $PATH binaries."""
from __future__ import annotations

import configparser
import os
import shutil
from pathlib import Path

from llauncher.models import AppEntry


def default_desktop_dirs() -> list[Path]:
    dirs: list[Path] = [
        Path.home() / ".local" / "share" / "applications",
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
        Path("/var/lib/flatpak/exports/share/applications"),
        Path.home() / ".local" / "share" / "flatpak" / "exports" / "share" / "applications",
    ]
    xdg_data_home = os.environ.get("XDG_DATA_HOME", "")
    if xdg_data_home:
        dirs.insert(0, Path(xdg_data_home) / "applications")
    xdg_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    for d in xdg_dirs:
        if d.strip():
            p = Path(d.strip()) / "applications"
            if p not in dirs:
                dirs.append(p)
    extra = os.environ.get("LLAUNCHER_EXTRA_DIRS", "")
    for d in extra.split(":"):
        if d.strip():
            dirs.append(Path(d.strip()))
    # de-dup, keep existing only
    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        key = str(d)
        if key in seen:
            continue
        seen.add(key)
        if d.is_dir():
            out.append(d)
    return out


def _parse_desktop_file(path: Path) -> AppEntry | None:
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str  # keep case
    try:
        # .desktop files often lack proper encoding headers; utf-8 works ~always
        with path.open(encoding="utf-8", errors="ignore") as f:
            cp.read_file(f)
    except (OSError, configparser.Error):
        return None
    if "Desktop Entry" not in cp:
        return None
    de = cp["Desktop Entry"]
    if de.get("Type", "Application") != "Application":
        return None
    if de.get("NoDisplay", "false").lower() == "true":
        return None
    name = de.get("Name", path.stem).strip()
    exec_cmd = de.get("Exec", "").strip()
    if not name or not exec_cmd:
        return None
    comment = de.get("Comment", "").strip()
    icon = de.get("Icon", "").strip()
    cats = tuple(c.strip() for c in de.get("Categories", "").split(";") if c.strip())
    terminal = de.get("Terminal", "false").lower() == "true"
    return AppEntry(
        name=name,
        exec_cmd=exec_cmd,
        comment=comment,
        icon=icon,
        categories=cats,
        terminal=terminal,
        desktop_file=str(path),
        source="desktop",
    )


def discover_desktop_apps(dirs: list[Path] | None = None) -> list[AppEntry]:
    dirs = dirs if dirs is not None else default_desktop_dirs()
    by_name: dict[str, AppEntry] = {}
    for d in dirs:
        try:
            files = sorted(d.glob("*.desktop"))
        except OSError:
            continue
        for f in files:
            entry = _parse_desktop_file(f)
            if entry is None:
                continue
            # later dirs override earlier ones with same filename (user > system)
            # but prefer first-seen Name to avoid dups: key on desktop basename
            by_name[f.name] = entry
    entries = sorted(by_name.values(), key=lambda e: e.name.lower())
    return entries


def discover_path_binaries(limit: int = 2000) -> list[AppEntry]:
    """Fallback: every executable on $PATH as a runnable entry."""
    path_env = os.environ.get("PATH", "/usr/bin:/bin")
    seen: set[str] = set()
    out: list[AppEntry] = []
    for d in path_env.split(os.pathsep):
        if not d.strip():
            continue
        try:
            with os.scandir(d.strip()) as it:
                for e in it:
                    if len(out) >= limit:
                        return sorted(out, key=lambda x: x.name.lower())
                    name = e.name
                    if name in seen:
                        continue
                    try:
                        if e.is_file(follow_symlinks=True) and os.access(e.path, os.X_OK):
                            seen.add(name)
                            out.append(
                                AppEntry(
                                    name=name,
                                    exec_cmd=name,
                                    comment=f"Run {name}",
                                    source="path",
                                )
                            )
                    except OSError:
                        continue
        except OSError:
            continue
    return sorted(out, key=lambda x: x.name.lower())


def discover_all(show_path_binaries: bool = True) -> list[AppEntry]:
    apps = discover_desktop_apps()
    if not show_path_binaries:
        return apps
    # Avoid duplicating names already covered by .desktop entries
    names = {a.name.lower() for a in apps}
    binaries = [b for b in discover_path_binaries() if b.name.lower() not in names]
    return apps + binaries


def which(cmd: str) -> str | None:
    return shutil.which(cmd.split()[0] if cmd else "")
