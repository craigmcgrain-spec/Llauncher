"""Matcher unit tests (no Qt needed)."""
from llauncher.matcher import filter_entries, score
from llauncher.launcher import build_argv, clean_exec
from llauncher.models import AppEntry


def test_score_prefix_beats_subsequence():
    assert score("fir", "Firefox") is not None
    assert score("fir", "Firefox") > score("fir", "LibreOffice Writer")


def test_score_none_when_not_subsequence():
    assert score("zzz", "Firefox") is None


def test_filter_returns_limited_ranked():
    entries = [
        AppEntry(name="Firefox", exec_cmd="firefox"),
        AppEntry(name="Files", exec_cmd="nautilus"),
        AppEntry(name="Terminal", exec_cmd="konsole"),
    ]
    out = filter_entries("fir", entries, limit=9)
    assert out[0].name == "Firefox"


def test_empty_query_returns_first_n():
    entries = [AppEntry(name=f"App{i}", exec_cmd=f"app{i}") for i in range(5)]
    assert len(filter_entries("", entries, limit=3)) == 3


def test_clean_exec_strips_field_codes():
    assert clean_exec("firefox %u --new-window") == ["firefox", "--new-window"]
    assert clean_exec("flatpak run org.foo.Bar @@ %F") == ["flatpak", "run", "org.foo.Bar", "@@"]


def test_build_argv_terminal_prefix():
    e = AppEntry(name="Htop", exec_cmd="htop", terminal=True)
    assert build_argv(e, terminal="konsole -e") == ["konsole", "-e", "htop"]
