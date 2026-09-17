"""Launch-binary helpers.

The generated terminal command is always built exactly as configured: no
flags are ever injected, removed, or rewritten (other than recognizing a
binary's subcommand, e.g. the `run` in `unsloth run ...`).

CPU-only applies to the Llauncher GUI process itself (Qt software rendering,
see `app.py --high-gfx` to opt out), never to the generated command.
"""
from __future__ import annotations

# Generated command prefix. Binaries below take a subcommand as their first
# arg (e.g. `unsloth run ...`); the parser and builder know how to split and
# re-attach it so it never gets lost or treated as a flag value.
DEFAULT_BINARY = "unsloth run"

BINARY_SUBCOMMANDS: dict[str, str] = {
    "unsloth": "run",
    "llama": "serve",  # legacy: old profiles / pasted commands still parse
}


def is_llama_family(binary: str) -> bool:
    """True for `llama-server` / `llama serve` (multi-word OK, paths OK).

    Only used to normalize legacy llama CLI spellings (e.g.
    `--n-gpu-layers` -> `--gpu-layers`) on import. Other binaries pass
    through verbatim.
    """
    import shlex

    text = (binary or "").strip()
    if not text:
        return False
    try:
        first = shlex.split(text)[0]
    except ValueError:
        first = text.split()[0]
    return first.split("/")[-1] in ("llama", "llama-server")
