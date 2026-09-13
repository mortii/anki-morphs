from __future__ import annotations

import hashlib
import io
import os
import platform
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from anki.utils import is_win

from ankimorphs.morphemizers import uv_bootstrap


def _tarball_with_uv(binary: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar_file:
        member = tarfile.TarInfo(name="uv-x86_64-unknown-linux-gnu/uv")
        member.size = len(binary)
        tar_file.addfile(member, io.BytesIO(binary))
    return buffer.getvalue()


def _zip_with_uv(binary: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as zip_file:
        zip_file.writestr("uv.exe", binary)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "platform_name, machine, expected_asset",
    [
        ("darwin", "arm64", "uv-aarch64-apple-darwin.tar.gz"),
        ("darwin", "x86_64", "uv-x86_64-apple-darwin.tar.gz"),
        # windows reports AMD64/ARM64, which ensure_uv() lowercases before
        # the lookup, so the map keys must be lowercase
        ("win32", "amd64", "uv-x86_64-pc-windows-msvc.zip"),
        ("win32", "arm64", "uv-aarch64-pc-windows-msvc.zip"),
        ("linux", "x86_64", "uv-x86_64-unknown-linux-gnu.tar.gz"),
        ("linux", "aarch64", "uv-aarch64-unknown-linux-gnu.tar.gz"),
    ],
)
def test_uv_asset_selection(
    platform_name: str, machine: str, expected_asset: str
) -> None:
    asset_name, digest = uv_bootstrap._uv_asset(platform_name, machine)
    assert asset_name == expected_asset
    assert len(digest) == 64


def test_unsupported_platform_raises() -> None:
    with pytest.raises(RuntimeError, match="does not have a Python download"):
        uv_bootstrap._uv_asset("linux", "riscv64")


def test_checksum_mismatch_aborts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(uv_bootstrap, "_bootstrap_dir", lambda: tmp_path)
    monkeypatch.setattr(
        uv_bootstrap,
        "_uv_asset",
        lambda platform_name, machine: (
            "uv-x86_64-unknown-linux-gnu.tar.gz",
            hashlib.sha256(b"expected content").hexdigest(),
        ),
    )
    monkeypatch.setattr(uv_bootstrap, "_download", lambda url: b"evil")

    with pytest.raises(RuntimeError, match="checksum"):
        uv_bootstrap.ensure_uv()

    # nothing may be written when verification fails
    assert not list(tmp_path.rglob("*"))


def test_extracts_uv_from_tarball(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    binary = b"fake uv binary"
    archive = _tarball_with_uv(binary)

    monkeypatch.setattr(uv_bootstrap, "_bootstrap_dir", lambda: tmp_path)
    monkeypatch.setattr(
        uv_bootstrap,
        "_uv_asset",
        lambda platform_name, machine: (
            "uv-x86_64-unknown-linux-gnu.tar.gz",
            hashlib.sha256(archive).hexdigest(),
        ),
    )
    monkeypatch.setattr(uv_bootstrap, "_download", lambda url: archive)

    uv_path = Path(uv_bootstrap.ensure_uv())

    assert uv_path.parent == tmp_path / "uv"
    assert uv_path.read_bytes() == binary
    if not is_win:
        assert os.access(uv_path, os.X_OK)


def test_extracts_uv_from_zip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    binary = b"fake uv binary"
    archive = _zip_with_uv(binary)

    monkeypatch.setattr(uv_bootstrap, "_bootstrap_dir", lambda: tmp_path)
    monkeypatch.setattr(
        uv_bootstrap,
        "_uv_asset",
        lambda platform_name, machine: (
            "uv-x86_64-pc-windows-msvc.zip",
            hashlib.sha256(archive).hexdigest(),
        ),
    )
    monkeypatch.setattr(uv_bootstrap, "_download", lambda url: archive)

    uv_path = Path(uv_bootstrap.ensure_uv())

    assert uv_path.parent == tmp_path / "uv"
    assert uv_path.read_bytes() == binary
    if not is_win:
        assert os.access(uv_path, os.X_OK)


def test_create_managed_venv_downloads_uv_when_nothing_is_native(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    def _fake_run(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(uv_bootstrap, "_bootstrap_dir", lambda: tmp_path)
    monkeypatch.setattr(uv_bootstrap, "_find_native_python", lambda: None)
    monkeypatch.setattr(uv_bootstrap, "_find_native_uv", lambda: None)
    monkeypatch.setattr(uv_bootstrap, "ensure_uv", lambda: "/fake/uv")
    monkeypatch.setattr(subprocess, "run", _fake_run)

    venv_path = str(tmp_path / "spacy-venv-python-3_13")
    uv_bootstrap.create_managed_venv(venv_path)

    assert captured["command"] == [
        "/fake/uv",
        "venv",
        "--seed",
        "--managed-python",
        "--no-config",
        "--python",
        uv_bootstrap._uv_python_request(),
        venv_path,
    ]
    assert captured["env"]["UV_PYTHON_INSTALL_DIR"] == str(tmp_path / "python")
    assert captured["env"]["UV_CACHE_DIR"] == str(tmp_path / "cache")


def test_create_managed_venv_prefers_native_python(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    def _fake_run(
        command: list[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    def _no_download() -> str:
        raise AssertionError("must not download uv when a native python exists")

    monkeypatch.setattr(uv_bootstrap, "_bootstrap_dir", lambda: tmp_path)
    monkeypatch.setattr(
        uv_bootstrap, "_find_native_python", lambda: "/usr/bin/python3.13"
    )
    monkeypatch.setattr(uv_bootstrap, "ensure_uv", _no_download)
    monkeypatch.setattr(subprocess, "run", _fake_run)

    venv_path = str(tmp_path / "spacy-venv-python-3_13")
    uv_bootstrap.create_managed_venv(venv_path)

    assert captured["command"] == ["/usr/bin/python3.13", "-m", "venv", venv_path]


def test_create_managed_venv_falls_back_to_uv_when_native_venv_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    commands: list[list[str]] = []

    def _fake_run(
        command: list[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[0] == "/usr/bin/python3.13":
            # e.g. debian without the python3-venv package
            raise subprocess.CalledProcessError(1, command, stderr="no ensurepip")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(uv_bootstrap, "_bootstrap_dir", lambda: tmp_path)
    monkeypatch.setattr(
        uv_bootstrap, "_find_native_python", lambda: "/usr/bin/python3.13"
    )
    monkeypatch.setattr(uv_bootstrap, "_find_native_uv", lambda: None)
    monkeypatch.setattr(uv_bootstrap, "ensure_uv", lambda: "/fake/uv")
    monkeypatch.setattr(subprocess, "run", _fake_run)

    venv_path = str(tmp_path / "spacy-venv-python-3_13")
    (tmp_path / "spacy-venv-python-3_13").mkdir()  # half-created venv
    uv_bootstrap.create_managed_venv(venv_path)

    assert commands[0] == ["/usr/bin/python3.13", "-m", "venv", venv_path]
    assert commands[1][:2] == ["/fake/uv", "venv"]
    # the half-created venv must have been discarded before the uv attempt
    assert not (tmp_path / "spacy-venv-python-3_13").exists()


def test_create_managed_venv_uses_native_uv_with_its_own_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    def _fake_run(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0)

    def _no_download() -> str:
        raise AssertionError("must not download uv when a native uv exists")

    monkeypatch.delenv("UV_PYTHON_INSTALL_DIR", raising=False)
    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    monkeypatch.setattr(uv_bootstrap, "_bootstrap_dir", lambda: tmp_path)
    monkeypatch.setattr(uv_bootstrap, "_find_native_python", lambda: None)
    monkeypatch.setattr(uv_bootstrap, "_find_native_uv", lambda: "/native/uv")
    monkeypatch.setattr(uv_bootstrap, "ensure_uv", _no_download)
    monkeypatch.setattr(subprocess, "run", _fake_run)

    venv_path = str(tmp_path / "spacy-venv-python-3_13")
    uv_bootstrap.create_managed_venv(venv_path)

    assert captured["command"][0] == "/native/uv"
    # a native uv keeps its default install/cache dirs so that pythons it
    # has already installed get reused instead of re-downloaded
    assert "UV_PYTHON_INSTALL_DIR" not in captured["env"]
    assert "UV_CACHE_DIR" not in captured["env"]


@pytest.mark.parametrize(
    "version_output, expected",
    [
        ("uv 0.12.7 (0a1b2c3d4 2026-08-01)", (0, 12, 7)),
        ("uv 0.6.8", (0, 6, 8)),
        ("garbage", None),
        ("", None),
    ],
)
def test_uv_version_parsing(
    version_output: str, expected: tuple[int, int, int] | None
) -> None:
    assert uv_bootstrap._uv_version(version_output) == expected


@pytest.mark.parametrize(
    "version_output, expected_path",
    [
        ("uv 0.12.7 (0a1b2c3d4 2026-08-01)", "/native/uv"),
        ("uv 0.6.7", None),  # predates --managed-python
        ("not a version", None),
    ],
)
def test_find_native_uv_version_gate(
    monkeypatch: pytest.MonkeyPatch, version_output: str, expected_path: str | None
) -> None:
    def _fake_run(
        command: list[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["/native/uv", "--version"]
        return subprocess.CompletedProcess(command, 0, stdout=version_output)

    monkeypatch.setattr(uv_bootstrap, "_which", lambda command: "/native/uv")
    monkeypatch.setattr(subprocess, "run", _fake_run)

    assert uv_bootstrap._find_native_uv() == expected_path


def test_find_native_uv_without_uv_on_the_system(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(uv_bootstrap, "_which", lambda command: None)
    assert uv_bootstrap._find_native_uv() is None


# what a regular CPython matching the running process prints when probed
_MATCHING_PROBE = (
    str(sys.version_info.major),
    str(sys.version_info.minor),
    platform.machine(),
    "cpython",
    "0",
)


@pytest.mark.parametrize(
    "probe_lines, expected_match",
    [
        (_MATCHING_PROBE, True),
        # wrong minor version
        (
            (_MATCHING_PROBE[0], str(sys.version_info.minor + 1)) + _MATCHING_PROBE[2:],
            False,
        ),
        # wrong major version
        ((str(sys.version_info.major + 1),) + _MATCHING_PROBE[1:], False),
        # e.g. an arm64 python while anki runs as x86_64 under rosetta
        (_MATCHING_PROBE[:2] + ("mismatched-arch",) + _MATCHING_PROBE[3:], False),
        # pypy venvs would select incompatible wheels
        (_MATCHING_PROBE[:3] + ("pypy", "0"), False),
        # free-threaded builds use incompatible cp3XXt wheels
        (_MATCHING_PROBE[:4] + ("1",), False),
    ],
)
def test_find_native_python_verifies_version_arch_and_implementation(
    monkeypatch: pytest.MonkeyPatch,
    probe_lines: tuple[str, ...],
    expected_match: bool,
) -> None:
    probe_output = "\n".join([*probe_lines, "/usr/bin/python-resolved"]) + "\n"

    def _fake_run(
        command: list[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout=probe_output)

    monkeypatch.setattr(
        uv_bootstrap, "_which", lambda command: "/usr/bin/python-candidate"
    )
    monkeypatch.setattr(subprocess, "run", _fake_run)

    expected = "/usr/bin/python-resolved" if expected_match else None
    assert uv_bootstrap._find_native_python() == expected


def test_find_native_python_without_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(uv_bootstrap, "_which", lambda command: None)
    assert uv_bootstrap._find_native_python() is None


@pytest.mark.parametrize(
    "platform_name, machine, expected_request",
    [
        ("darwin", "arm64", "cpython-3.13-macos-aarch64-none"),
        ("darwin", "x86_64", "cpython-3.13-macos-x86_64-none"),
        ("win32", "AMD64", "cpython-3.13-windows-x86_64-none"),
        ("win32", "ARM64", "cpython-3.13-windows-aarch64-none"),
        ("linux", "x86_64", "cpython-3.13-linux-x86_64-gnu"),
        ("linux", "aarch64", "cpython-3.13-linux-aarch64-gnu"),
    ],
)
def test_uv_python_request_is_arch_qualified(
    monkeypatch: pytest.MonkeyPatch,
    platform_name: str,
    machine: str,
    expected_request: str,
) -> None:
    monkeypatch.setattr(sys, "platform", platform_name)
    monkeypatch.setattr(sys, "version_info", SimpleNamespace(major=3, minor=13))
    monkeypatch.setattr(platform, "machine", lambda: machine)

    assert uv_bootstrap._uv_python_request() == expected_request


def test_archive_without_uv_member_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar_file:
        member = tarfile.TarInfo(name="uv-x86_64-unknown-linux-gnu/README.md")
        member.size = 0
        tar_file.addfile(member, io.BytesIO(b""))
    archive = buffer.getvalue()

    monkeypatch.setattr(uv_bootstrap, "_bootstrap_dir", lambda: tmp_path)
    monkeypatch.setattr(
        uv_bootstrap,
        "_uv_asset",
        lambda platform_name, machine: (
            "uv-x86_64-unknown-linux-gnu.tar.gz",
            hashlib.sha256(archive).hexdigest(),
        ),
    )
    monkeypatch.setattr(uv_bootstrap, "_download", lambda url: archive)

    with pytest.raises(RuntimeError, match="did not contain a uv binary"):
        uv_bootstrap.ensure_uv()

    # no binary and no leftover temp file may exist anywhere
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
