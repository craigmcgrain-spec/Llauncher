"""Non-Qt tests for profile store, gguf scan and bash builder."""
import json

from llauncher.command import build_argv, parse_command, to_bash, to_script
from llauncher.server_options import BY_FLAG, parse_help_flags, uncovered_flags
from llauncher.server_profile import ServerProfile, scan_models


def test_build_argv_model_and_sampling(tmp_path=None):
    p = ServerProfile(
        name="test",
        server_binary="unsloth run",
        model="/models/qwen.gguf",
        options={"--ctx-size": "8192", "--temperature": "0.7", "--embedding": "true"},
    )
    argv = build_argv(p)
    assert argv[:4] == ["unsloth", "run", "--model", "/models/qwen.gguf"]
    assert "--ctx-size" in argv and "8192" in argv
    assert "--temperature" in argv and "0.7" in argv
    assert "--embedding" in argv  # bool off->on emits flag
    # unsloth builds pass through verbatim: no llama-only CPU flags injected
    assert "--gpu-layers" not in argv
    assert "--device" not in argv
    assert "--no-kv-offload" not in argv


def test_bool_default_on_emits_neg_only_when_off():
    p = ServerProfile(name="t", options={"--cont-batching": "false"})
    argv = build_argv(p)
    assert "--no-cont-batching" in argv
    assert "--cont-batching" not in argv
    p2 = ServerProfile(name="t", options={"--cont-batching": "true"})
    argv2 = build_argv(p2)
    assert argv2 == ["unsloth", "run"]  # equals default -> omitted, nothing injected


def test_empty_options_omitted_and_extra_args_appended():
    p = ServerProfile(name="t", options={"--port": "", "--host": "  "}, extra_args="--verbose --port 9999")
    argv = build_argv(p)
    assert argv == ["unsloth", "run", "--verbose", "--port", "9999"]


def test_to_bash_single_line_unquoted():
    p = ServerProfile(name="t", model="/my models/qwen 7b.gguf", options={"--port": "8080"})
    bash = to_bash(p)
    assert "/my models/qwen 7b.gguf" in bash
    assert "--model" in bash and "--port 8080" in bash
    assert "\\\n" not in bash


def test_to_script_has_shebang_and_profile_name():
    s = to_script(ServerProfile(name="coder", options={"--port": "8081"}))
    assert s.startswith("#!/usr/bin/env bash")
    assert "coder" in s and "--port 8081" in s


def test_profile_roundtrip_json():
    p = ServerProfile(name="my prof!", model="m.gguf", options={"--ctx-size": "4096"}, extra_args="--verbose")
    d = p.to_dict()
    assert json.loads(json.dumps(d))["options"]["--ctx-size"] == "4096"
    p2 = ServerProfile.from_dict(d)
    assert p2 == p  # unsloth profiles migrate untouched


def test_scan_models_empty_for_missing_dir(tmp_path):
    assert scan_models(str(tmp_path / "nope")) == []


def test_scan_models_finds_gguf(tmp_path):
    (tmp_path / "a.gguf").write_bytes(b"GGUF")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.GGUF").write_bytes(b"GGUF")
    (sub / "notes.txt").write_text("x")
    found = scan_models(str(tmp_path))
    assert len(found) == 2
    assert all(f.suffix.lower() == ".gguf" for f in found)


def test_catalog_covers_core_flags():
    for flag in ("--model", "--ctx-size", "--port", "--host", "--gpu-layers",
                 "--temperature", "--parallel", "--embedding"):
        assert flag in BY_FLAG, f"missing {flag}"


def test_help_parser_extracts_flags():
    text = "usage: llama-server -m MODEL --ctx-size N --no-webui\n  -c, --ctx-size N  size"
    flags = parse_help_flags(text)
    assert "--ctx-size" in flags and "--no-webui" in flags
    missing = uncovered_flags("--brand-new-flag --port")
    assert "--brand-new-flag" in missing and "--port" not in missing


def test_parse_command_full_example():
    cmd = "unsloth run --model /home/mcgrain/Models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --alias Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --ctx-size 150000 --parallel 1 --n-gpu-layers 999 --n-cpu-moe 30 --flash-attn off --cache-type-k q4_0 --cache-type-v f16 --no-kv-offload --reasoning on --reasoning-effort medium --reasoning-budget 4096 --no-reasoning-preserve  --host 127.0.0.1 --port 8080"
    p = parse_command(cmd)
    assert p.server_binary == "unsloth run"
    assert p.model == "/home/mcgrain/Models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
    assert p.options["--alias"] == "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
    assert p.options["--ctx-size"] == "150000"
    assert p.options["--parallel"] == "1"
    assert "--n-gpu-layers 999" in p.extra_args  # kept verbatim, not normalized for unsloth
    assert p.options["--n-cpu-moe"] == "30"
    assert p.options["--flash-attn"] == "off"
    assert p.options["--cache-type-k"] == "q4_0"
    assert p.options["--cache-type-v"] == "f16"
    assert p.options["--kv-offload"] == "false"  # --no-kv-offload stored as positive=false
    assert p.options["--reasoning"] == "on"
    assert p.options["--reasoning-effort"] == "medium"
    assert p.options["--reasoning-budget"] == "4096"
    assert p.options["--reasoning-preserve"] == "false"  # --no-reasoning-preserve
    assert p.options["--host"] == "127.0.0.1"
    assert p.options["--port"] == "8080"


def test_parse_command_simple():
    p = parse_command("unsloth run --model /models/test.gguf --port 9999")
    assert p.server_binary == "unsloth run"
    assert p.model == "/models/test.gguf"
    assert p.options["--port"] == "9999"


def test_parse_command_empty():
    p = parse_command("")
    assert p.server_binary == "unsloth run"
    assert p.model == ""
    assert p.options == {}


def test_parse_command_bool_flags():
    p = parse_command("llama-server --embedding --verbose --temperature 0.7")
    assert p.options["--embedding"] == "true"
    assert p.options["--verbose"] == "true"
    assert p.options["--temperature"] == "0.7"


def test_parse_command_negation_flags():
    p = parse_command("llama-server --no-cont-batching --no-cache-prompt --no-jinja")
    assert p.options["--cont-batching"] == "false"
    assert p.options["--cache-prompt"] == "false"
    assert p.options["--jinja"] == "false"


def test_build_passes_profile_through_untouched():
    p = ServerProfile(name="t", server_binary="llama-server", model="m.gguf",
                      options={"--gpu-layers": "999", "--flash-attn": "on"})
    argv = build_argv(p)
    assert argv[:3] == ["llama-server", "--model", "m.gguf"]
    assert "--gpu-layers" in argv and "999" in argv
    assert "--flash-attn" in argv and "on" in argv
    # nothing injected
    assert "--device" not in argv
    assert "--no-kv-offload" not in argv
    # no stray "true" value emitted after a --no-* flag
    for i, tok in enumerate(argv):
        if tok.startswith("--no-"):
            assert i + 1 >= len(argv) or not argv[i + 1] == "true"


def test_negation_roundtrip_has_no_stray_true():
    p = parse_command("unsloth run --model m.gguf --no-kv-offload --no-op-offload")
    assert p.options["--kv-offload"] == "false"
    assert p.options["--op-offload"] == "false"
    argv = build_argv(p)
    assert "--no-kv-offload" in argv and "--no-op-offload" in argv
    assert "true" not in argv


def test_legacy_n_gpu_layers_alias_normalized():
    p = parse_command("llama-server --model m.gguf --n-gpu-layers 99")
    assert p.options["--gpu-layers"] == "99"  # normalized, value untouched
    assert "--n-gpu-layers" not in p.options


def test_unknown_flags_preserved_verbatim_in_extra_args():
    p = parse_command("unsloth run --model m.gguf --n-gpu-layers 99 --my-flag hello --bare-flag")
    assert "--n-gpu-layers" not in p.options
    assert "--n-gpu-layers 99" in p.extra_args
    assert "--my-flag hello" in p.extra_args
    assert "--bare-flag" in p.extra_args
    argv = build_argv(p)
    assert "--n-gpu-layers" in argv and "99" in argv
    assert "--my-flag" in argv and "hello" in argv
    assert "--bare-flag" in argv


def test_is_llama_family():
    from llauncher.presets import is_llama_family

    assert is_llama_family("llama-server")
    assert is_llama_family("llama serve")
    assert is_llama_family("/opt/llama.cpp/build/bin/llama-server")
    assert not is_llama_family("unsloth run")
    assert not is_llama_family("unsloth")
    assert not is_llama_family("")


def test_unsloth_import_is_verbatim():
    cmd = ("unsloth run --model /home/mcgrain/Models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf "
           "--cache-type-k q4_0 --cache-type-v f16 --ctx-size 150000 --flash-attn off "
           "--host 127.0.0.1 --n-cpu-moe 40 --parallel 1 --port 8080 --reasoning on "
           "--reasoning-budget 4096 --reasoning-effort medium")
    p = parse_command(cmd)
    assert p.server_binary == "unsloth run"
    assert p.extra_args == ""
    out = to_bash(p)
    assert out.startswith("unsloth run --model /home/mcgrain/Models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf")
    for bad in ("--device", "--gpu-layers", "--no-kv-offload", "--no-op-offload",
                "--no-mmproj-offload", "--spec-draft-ngl", "--batch-size", "--ubatch-size"):
        assert bad not in out.split(), f"injected {bad}"
    for good in ("--cache-type-k q4_0", "--cache-type-v f16", "--ctx-size 150000",
                 "--flash-attn off", "--host 127.0.0.1", "--n-cpu-moe 40",
                 "--parallel 1", "--port 8080", "--reasoning on",
                 "--reasoning-budget 4096", "--reasoning-effort medium"):
        assert good in out, f"missing {good}"


def test_legacy_llama_serve_still_parses():
    p = parse_command("llama serve --model /models/test.gguf --port 9999")
    assert p.server_binary == "llama serve"
    assert p.model == "/models/test.gguf"
    assert p.options["--port"] == "9999"
    assert build_argv(p)[:2] == ["llama", "serve"]


def test_bare_unsloth_binary_gains_run_subcommand():
    p = ServerProfile(name="t", server_binary="unsloth", model="m.gguf")
    argv = build_argv(p)
    assert argv[:3] == ["unsloth", "run", "--model"]
