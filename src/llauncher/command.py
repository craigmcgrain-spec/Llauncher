"""Build argv + bash from a ServerProfile + option catalog."""
from __future__ import annotations

import shlex

from llauncher.server_options import BY_FLAG
from llauncher.server_profile import ServerProfile


def build_argv(profile: ServerProfile) -> list[str]:
    argv: list[str] = [profile.server_binary or "llama-server"]
    if profile.model.strip():
        argv += ["--model", profile.model.strip()]
    for flag in sorted(profile.options):
        raw = profile.options[flag]
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
    """Single bash command with line continuations, shell-quoted."""
    argv = build_argv(profile)
    if len(argv) <= 1:
        return shlex.quote(argv[0]) if argv else ""
    quoted = [shlex.quote(a) for a in argv]
    # join: break line before each new flag
    out: list[str] = [quoted[0]]
    for tok_q, tok_raw in zip(quoted[1:], argv[1:]):
        if tok_raw.startswith("-") and not tok_raw.lstrip("-").replace(".", "").replace("_", "").isdigit():
            out.append("  " + tok_q)
        else:
            out[-1] += " " + tok_q
    return " \\\n".join(out)


def to_script(profile: ServerProfile) -> str:
    return "#!/usr/bin/env bash\n# Llauncher profile: {}\nset -euo pipefail\n\n{}\n".format(
        profile.name, to_bash(profile)
    )
