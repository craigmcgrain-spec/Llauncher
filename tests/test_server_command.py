"""Non-Qt tests for profile store, gguf scan and bash builder."""
import json

from llauncher.command import build_argv, to_bash, to_script
from llauncher.server_options import BY_FLAG, parse_help_flags, uncovered_flags
from llauncher.server_profile import ServerProfile, scan_models


def test_build_argv_model_and_sampling(tmp_path=None):
    p = ServerProfile(
        name="test",
        server_binary="llama-server",
        model="/models/qwen.gguf",
        options={"--ctx-size": "8192", "--temperature": "0.7", "--embedding": "true"},
    )
    argv = build_argv(p)
    assert argv[:3] == ["llama-server", "--model", "/models/qwen.gguf"]
    assert "--ctx-size" in argv and "8192" in argv
    assert "--temperature" in argv and "0.7" in argv
    assert "--embedding" in argv  # bool off->on emits flag


def test_bool_default_on_emits_neg_only_when_off():
    p = ServerProfile(name="t", options={"--cont-batching": "false"})
    argv = build_argv(p)
    assert "--no-cont-batching" in argv
    assert "--cont-batching" not in argv
    p2 = ServerProfile(name="t", options={"--cont-batching": "true"})
    assert build_argv(p2) == ["llama-server"]  # equals default -> omitted


def test_empty_options_omitted_and_extra_args_appended():
    p = ServerProfile(name="t", options={"--port": "", "--host": "  "}, extra_args="--verbose --port 9999")
    argv = build_argv(p)
    assert argv == ["llama-server", "--verbose", "--port", "9999"]


def test_to_bash_quotes_paths_with_spaces():
    p = ServerProfile(name="t", model="/my models/qwen 7b.gguf", options={"--port": "8080"})
    bash = to_bash(p)
    assert "'/my models/qwen 7b.gguf'" in bash
    assert "--model" in bash and "--port 8080" in bash
    assert "\\\n" in bash


def test_to_script_has_shebang_and_profile_name():
    s = to_script(ServerProfile(name="coder", options={"--port": "8081"}))
    assert s.startswith("#!/usr/bin/env bash")
    assert "coder" in s and "--port 8081" in s


def test_profile_roundtrip_json():
    p = ServerProfile(name="my prof!", model="m.gguf", options={"--ctx-size": "4096"}, extra_args="--verbose")
    d = p.to_dict()
    assert json.loads(json.dumps(d))["options"]["--ctx-size"] == "4096"
    p2 = ServerProfile.from_dict(d)
    assert p2 == p


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
