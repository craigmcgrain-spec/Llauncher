"""Core data model for a launchable entry."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppEntry:
    """A single searchable / launchable item."""

    name: str
    exec_cmd: str
    comment: str = ""
    icon: str = ""
    categories: tuple[str, ...] = ()
    terminal: bool = False
    desktop_file: str = ""
    source: str = "desktop"  # "desktop" | "path"

    @property
    def display(self) -> str:
        return self.name

    @property
    def subtitle(self) -> str:
        if self.comment:
            return self.comment
        if self.source == "path":
            return self.exec_cmd
        return self.exec_cmd[:80]
