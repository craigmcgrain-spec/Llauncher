"""JSON config at ~/.config/llauncher/settings.json."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from llauncher.presets import DEFAULT_BINARY


CONFIG_DIR = Path.home() / ".config" / "llauncher"
CONFIG_FILE = CONFIG_DIR / "settings.json"


@dataclass
class Settings:
    width: int = 640
    max_results: int = 9
    show_path_binaries: bool = True
    terminal: str = "konsole -e"
    # extra .desktop dirs to scan (colon-separated env LLAUNCHER_EXTRA_DIRS also works)
    extra_dirs: tuple[str, ...] = ()
    # llama-server configurator
    server_binary: str = DEFAULT_BINARY
    models_dir: str = ""
    last_profile: str = "default"


def load_settings() -> Settings:
    s = Settings()
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return s
    except (json.JSONDecodeError, OSError):
        return s
    for key in asdict(s):
        if key in data:
            try:
                setattr(s, key, data[key])
            except Exception:
                continue
    # normalize
    if isinstance(s.extra_dirs, list):
        s.extra_dirs = tuple(s.extra_dirs)
    return s


def save_settings(settings: Settings) -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    return CONFIG_FILE
