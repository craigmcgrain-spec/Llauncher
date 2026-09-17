"""Build argv + bash from a ServerProfile + option catalog."""
from __future__ import annotations

import shlex

from llauncher.presets import (
    BINARY_SUBCOMMANDS,
    DEFAULT_BINARY,
    is_llama_family,
)
from llauncher.server_options import BY_FLAG
from llauncher.server_profile import ServerProfile


# Legacy CLI spellings normalized before catalog lookup.
FLAG_ALIASES = {"--n-gpu-layers": "--gpu-layers"}


def parse_command(cmd: str) -> ServerProfile:
    """Parse a shell command string into a ServerProfile."""
    try:
        args = shlex.split(cmd, posix=True)
    except ValueError:
        args = cmd.split()

    if not args:
        return ServerProfile()

    first = args[0]
    binary = first.split("/")[-1]
    model = ""
    options: dict[str, str] = {}
    extra: list[str] = []  # unknown flags kept verbatim (no catalog entry)
    i = 1
    sub = BINARY_SUBCOMMANDS.get(binary)
    if sub and len(args) > 1 and args[1] == sub:
        binary = f"{first} {sub}"
        i = 2
    family = is_llama_family(binary)

    while i < len(args):
        arg = args[i]
        if arg.startswith("--no-") and arg not in ("--no-kv-offload", "--no-reasoning-preserve", "--no-op-offload", "--no-repack", "--no-cache-prompt", "--no-cont-batching", "--no-kv-unified", "--no-context-shift", "--no-warmup", "--no-jinja", "--no-slots", "--no-perf", "--no-escape", "--no-mmproj", "--no-mmproj-offload", "--no-cors-credentials"):
            key = f"--{arg[5:]}"  # strip the 5-char "--no-" prefix
            spec = BY_FLAG.get(key)
            if spec is not None and spec.kind == "bool" and spec.neg == arg:
                options[key] = "false"
            elif arg in BY_FLAG:
                options[arg] = "true"
            i += 1
            continue

        if arg == "--model":
            if i + 1 < len(args):
                model = args[i + 1]
                i += 2
                continue
        elif arg == "--alias":
            if i + 1 < len(args):
                options[arg] = args[i + 1]
                i += 2
                continue
        elif arg == "--reasoning":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                options[arg] = args[i + 1]
                i += 2
                continue
            else:
                options[arg] = "on"
                i += 1
                continue
        elif arg == "--flash-attn":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                options[arg] = args[i + 1]
                i += 2
                continue
        elif arg == "--cache-type-k":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                options[arg] = args[i + 1]
                i += 2
                continue
        elif arg == "--cache-type-v":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                options[arg] = args[i + 1]
                i += 2
                continue
        elif arg == "--reasoning-effort":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                options[arg] = args[i + 1]
                i += 2
                continue
        elif arg == "--reasoning-budget":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                options[arg] = args[i + 1]
                i += 2
                continue
        elif arg in ("--no-kv-offload", "--no-reasoning-preserve", "--no-op-offload", "--no-repack",
                     "--no-cache-prompt", "--no-cont-batching", "--no-kv-unified",
                     "--no-context-shift", "--no-warmup", "--no-jinja", "--no-slots",
                     "--no-perf", "--no-escape", "--no-mmproj", "--no-mmproj-offload",
                     "--no-cors-credentials"):
            key = f"--{arg[5:]}"  # strip the 5-char "--no-" prefix
            spec = BY_FLAG.get(key)
            if spec is not None and spec.kind == "bool" and spec.neg == arg:
                options[key] = "false"
            elif arg in BY_FLAG:
                options[arg] = "true"
            i += 1
            continue

        if family:
            arg = FLAG_ALIASES.get(arg, arg)
        if arg in BY_FLAG:
            spec = BY_FLAG[arg]
            if spec.kind == "bool":
                options[arg] = "true"
                i += 1
            elif i + 1 < len(args) and not args[i + 1].startswith("-"):
                options[arg] = args[i + 1]
                i += 2
            else:
                i += 1
        else:
            # Unknown flag (or stray positional): keep verbatim so imports
            # never silently drop flags other binaries accept.
            extra.append(arg)
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                extra.append(args[i + 1])
                i += 2
            else:
                i += 1

    return ServerProfile(
        server_binary=binary,
        model=model,
        options=options,
        extra_args=" ".join(extra),
    )


def build_argv(profile: ServerProfile) -> list[str]:
    binary = profile.server_binary.strip() or DEFAULT_BINARY
    parts = shlex.split(binary)
    if parts:
        sub = BINARY_SUBCOMMANDS.get(parts[0].split("/")[-1])
        if sub and sub not in parts:
            parts.append(sub)
    argv: list[str] = parts
    options = profile.options
    if profile.model.strip():
        argv += ["--model", profile.model.strip()]
    for flag in sorted(options):
        raw = options[flag]
        value = raw.strip() if isinstance(raw, str) else raw
        spec = BY_FLAG.get(flag)
        if spec is not None and spec.kind == "bool":
            # stored as "true"/"false"/""/"1"/"0"
            on = str(value).lower() in ("1", "true", "yes", "on")
            if on and not spec.default_on:
                argv.append(flag)
            elif not on and spec.default_on:
                argv.append(spec.neg or flag)
            # on == default -> emit nothing
            continue
        if value in ("", None):
            continue
        argv += [flag, str(value)]
    if profile.extra_args.strip():
        try:
            argv += shlex.split(profile.extra_args, posix=True)
        except ValueError:
            argv += profile.extra_args.split()
    return argv


def to_bash(profile: ServerProfile) -> str:
    """Single-line bash command, unquoted."""
    argv = build_argv(profile)
    return " ".join(argv)


def to_script(profile: ServerProfile) -> str:
    return f"#!/usr/bin/env bash\n# Llauncher profile: {profile.name}\nset -euo pipefail\n\n{to_bash(profile)}\n"
