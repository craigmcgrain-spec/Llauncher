# Llauncher

`llama-server` (llama.cpp) configurator + runner for Linux, built with Python + PySide6 (Qt).

Pick a model from your models directory → tick server flags → live bash preview → **Run** in the embedded console. Save the setup as a named profile and recall it later.

> Note: older versions were a generic app launcher; the app is now focused on
> llama.cpp server workflows. The old launcher modules remain in `src/llauncher/`
> but the main window is the server configurator.

## Features

- 🦙 **All `llama-server` flags** as grouped form tabs (Model, Context & Batch, GPU & Offload, Sampling, Server Net/Behavior, Multimodal, Speculative, Tools & Agent, Chat Template, Logging, Misc)
- ⌨️ Every flag editable → instantly **converted to bash** (shell-quoted, line-continued)
- ▶️ **Run button** executes the command in an **embedded console** (QProcess) with Stop, Clear, and stdin input
- 💾 **Profiles** saved as JSON in `~/.config/llauncher/profiles/*.json` (New / Save / Delete)
- 📁 **User-defined models directory**: recursive `.gguf` scan + picker
- 📋 Copy bash / Export executable `.sh`
- 🔍 "Check --help coverage" runs `<binary> --help` and reports flags missing from the form (put those in Extra raw args)

## Requirements

- Fedora 44 / any modern Linux (KDE Plasma tested)
- Python 3.10+, `uv` — https://docs.astral.sh/uv/
- A `llama-server` binary (llama.cpp) for running; configuring works without one
- System Qt: `sudo dnf install -y libxcb-cursor libGL` if PySide6 fails to import

## Quickstart

```bash
cd /home/mcgrain/Projects/Llauncher

uv sync
uv run llauncher
# open with a profile: uv run llauncher --profile coder
# allow Qt GPU rendering (default is CPU/software rendering): uv run llauncher --high-gfx
```

> The generated command is never modified: no flags are injected, removed, or
> rewritten — what you see in Generated bash is exactly what runs (unknown
> flags on import are kept verbatim in Extra raw args). CPU-only applies to
> the Llauncher GUI itself, which defaults to Qt software rendering (pass
> `--high-gfx` to allow GPU rendering).

1. Set **Server binary** (`unsloth run` on PATH, or Browse to a full path).
2. Set **Models dir** (e.g. `~/models`) → Rescan → pick a **Model** (or set `--hf-repo`).
3. Tick flags across the tabs. Watch the **Generated bash** update.
4. Press **▶ Run**. Output streams into the embedded console. **■ Stop** to kill.

## Profiles & settings

- `~/.config/llauncher/settings.json` — window/binary/models-dir/last profile
- `~/.config/llauncher/profiles/<name>.json` — server_binary, model, models_dir, options, extra_args

## Icons

```bash
./install-icons.sh        # ~/.local/share/icons/hicolor/*/apps/llauncher.png
```

## Dev

```bash
uv run pytest -q
uv run python -m compileall src -q
QT_QPA_PLATFORM=offscreen uv run python -m llauncher --help
```

## "ollama.cpp" naming

The app generates **`unsloth run`** commands (old `llama serve` /
`llama-server` commands still import and run). Any binary-specific flags can
go in **Extra raw args**.
