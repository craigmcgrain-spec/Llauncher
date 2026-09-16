"""Launch an AppEntry: clean Exec= line and spawn detached."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess

from llauncher.models import AppEntry

# .desktop field codes to strip (https://specifications.freedesktop.org/desktop-entry-spec/)
_FIELD_CODES = {"%f", "%F", "%u", "%U", "%d", "%D", "%n", "%N", "%i", "%c", "%k", "%v", "%m"}


def clean_exec(exec_cmd: str) -> list[str]:
    """Turn a .desktop Exec= string into argv, dropping %field codes."""
    try:
        parts = shlex.split(exec_cmd, posix=True)
    except ValueError:
        parts = exec_cmd.split()
    argv = [p for p in parts if p not in _FIELD_CODES]
    return argv


def build_argv(entry: AppEntry, terminal: str = "konsole -e") -> list[str]:
    if entry.source == "path":
        return shlex.split(entry.exec_cmd, posix=True)
    argv = clean_exec(entry.exec_cmd)
    if not argv:
        return []
    # Resolve bare binary via PATH (flatpak run, env, etc. keep as-is)
    if "/" not in argv[0] and shutil.which(argv[0]) is None:
        # e.g. Exec=foo --bar where foo isn't on PATH (snap/flatpak wrapper) — try anyway
        pass
    if entry.terminal:
        term_parts = shlex.split(terminal, posix=True) if terminal else []
        return term_parts + argv
    return argv


def launch(entry: AppEntry, terminal: str = "konsole -e") -> bool:
    argv = build_argv(entry, terminal=terminal)
    if not argv:
        return False
    try:
        subprocess.Popen(
            argv,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.path.expanduser("~"),
        )
        return True
    except (OSError, ValueError):
        return False
