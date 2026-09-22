"""Server profiles: named, saved llama-server configurations."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
import os
from pathlib import Path

from llauncher.presets import DEFAULT_BINARY


PROFILES_DIR = Path.home() / ".config" / "llauncher" / "profiles"


def _slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-")
    return slug or "default"


@dataclass
class ServerProfile:
    """Everything needed to build + run one llama-server command."""

    name: str = "default"
    server_binary: str = DEFAULT_BINARY
    model: str = ""  # .gguf path or "" when using --hf-repo
    models_dir: str = ""  # user-defined models library
    options: dict[str, str] = field(default_factory=dict)  # flag -> value ("true"/"" for bool)
    extra_args: str = ""  # raw extra shell args appended verbatim (parsed with shlex)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ServerProfile:
        return cls(
            name=str(data.get("name", "default")),
            server_binary=str(data.get("server_binary", DEFAULT_BINARY)),
            model=str(data.get("model", "")),
            models_dir=str(data.get("models_dir", "")),
            options=dict(data.get("options", {})),
            extra_args=str(data.get("extra_args", "")),
        )


def profile_path(name: str) -> Path:
    return PROFILES_DIR / f"{_slug(name)}.json"


def save_profile(profile: ServerProfile) -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    p = profile_path(profile.name)
    p.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
    return p


def load_profile(name: str) -> ServerProfile:
    return ServerProfile.from_dict(json.loads(profile_path(name).read_text(encoding="utf-8")))


def delete_profile(name: str) -> bool:
    try:
        profile_path(name).unlink()
        return True
    except OSError:
        return False


def list_profiles() -> list[str]:
    if not PROFILES_DIR.is_dir():
        return []
    names = sorted(p.stem for p in PROFILES_DIR.glob("*.json"))
    return names


# Cache keyed by the resolved models-dir path. Scanning a large .gguf library
# is the most expensive operation in the app and only needs to happen once
# until the directory path changes (rescan is user-initiated), so results are
# memoized. A single process never mutates its own cache.
_MODEL_CACHE: dict[str, list[Path]] = {}


def invalidate_models_cache() -> None:
    """Drop cached scans (used only in tests / hot-reload scenarios)."""
    _MODEL_CACHE.clear()


def scan_models(models_dir: str, recursive: bool = True) -> list[Path]:
    """List .gguf files under the user-defined models directory."""
    base = Path(models_dir).expanduser()
    if not models_dir.strip() or not base.is_dir():
        return []
    key = str(base)
    cached = _MODEL_CACHE.get(key)
    if cached is not None:
        return cached
    # os.walk yields entries incrementally and matches the ".gguf" suffix
    # case-insensitively (rglob is case-sensitive and lists every file first).
    try:
        files = []
        for root, _dirs, names in os.walk(base):
            for name in names:
                if name.lower().endswith(".gguf"):
                    files.append(Path(root) / name)
        result = sorted(files, key=lambda p: str(p).lower())
    except OSError:
        return []
    _MODEL_CACHE[key] = result
    return result
