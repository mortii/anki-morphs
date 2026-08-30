from __future__ import annotations

import sys

import aqt.package
import pytest

from ankimorphs.morphemizers.python_binary import get_python_binary


def test_launcher_build_uses_the_anki_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    # anki 25.09 and earlier ran from a uv-managed venv
    launcher_python = "/home/user/.local/share/AnkiProgramFiles/.venv/bin/python"
    monkeypatch.setattr(
        aqt.package, "venv_binary", lambda cmd: launcher_python, raising=False
    )
    assert get_python_binary() == launcher_python


@pytest.mark.parametrize(
    "executable",
    [
        "/Applications/Anki.app/Contents/MacOS/Anki",
        "/usr/local/anki",
    ],
)
def test_self_contained_build_has_no_interpreter(
    monkeypatch: pytest.MonkeyPatch, executable: str
) -> None:
    # anki 26.08 removed venv_binary, and the official builds run from a
    # frozen binary we cannot create a venv with
    monkeypatch.delattr(aqt.package, "venv_binary", raising=False)
    monkeypatch.setattr(sys, "executable", executable)
    assert get_python_binary() is None


@pytest.mark.parametrize(
    "executable",
    [
        "/app/bin/python3.13",
        "/usr/bin/python3",
    ],
)
def test_python_based_install_uses_the_running_interpreter(
    monkeypatch: pytest.MonkeyPatch, executable: str
) -> None:
    monkeypatch.delattr(aqt.package, "venv_binary", raising=False)
    monkeypatch.setattr(sys, "executable", executable)
    assert get_python_binary() == executable
