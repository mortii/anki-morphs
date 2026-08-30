"""
Provisions a python interpreter for the spaCy/CAMeL venvs when the anki
install does not have one we can use.

Anki 25.09 and earlier ran from a uv-managed venv and exposed its python
through 'aqt.package.venv_binary', so get_python_binary() could return an
interpreter. The official Anki 26.x builds are self-contained apps without a
usable interpreter, so we have to provision one ourselves. To avoid
unnecessary downloads we first look for tools already installed on the
system: a CPython matching the version anki runs on (used directly with
'python -m venv'), then a usable uv binary. Only when neither exists do we
download a pinned uv release (sha256 verified) into a bootstrap folder next
to the venvs, and have uv install a standalone CPython.

Note: the available python versions are frozen per uv release, so if anki
ever adopts a CPython minor unknown to the pinned uv version below (0.12.7
knows 3.13 and 3.14), bump _UV_VERSION and the _UV_ASSETS digests.
"""

from __future__ import annotations

import hashlib
import io
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

from anki.httpclient import HttpClient
from anki.utils import is_mac, is_win
from aqt import mw

_UV_VERSION = "0.12.7"
_UV_RELEASE_URL = f"https://github.com/astral-sh/uv/releases/download/{_UV_VERSION}/"

# the oldest uv that supports every flag we pass to 'uv venv'
# (--managed-python was the last one added, in uv 0.6.8)
_MIN_NATIVE_UV_VERSION = (0, 6, 8)

# (sys.platform, platform.machine().lower()) -> (asset name, sha256 hex digest)
# digests taken from the github release api for uv 0.12.7
_UV_ASSETS: dict[tuple[str, str], tuple[str, str]] = {
    ("darwin", "arm64"): (
        "uv-aarch64-apple-darwin.tar.gz",
        "127ebdda7ad953cdf198e964b570ea5771b85467ea93eb7cb6d6f8e6f55408f3",
    ),
    ("darwin", "x86_64"): (
        "uv-x86_64-apple-darwin.tar.gz",
        "06b8ae1da8c2661c5434507a66f8c2b0b835933bf955b5958a9ac357a37d1959",
    ),
    ("win32", "amd64"): (
        "uv-x86_64-pc-windows-msvc.zip",
        "bf1518af459a3915511a11fdc6e2f43ef9a2afa138b9d498eeb9642fe9d85218",
    ),
    ("win32", "arm64"): (
        "uv-aarch64-pc-windows-msvc.zip",
        "1611d0f4be72b0a354ad9a6ae954093dd4c91e93e36b8b490326a05a039ffe14",
    ),
    ("linux", "x86_64"): (
        "uv-x86_64-unknown-linux-gnu.tar.gz",
        "788f18abea7c5f55d6216e4f5613fd89d4d59b631efeec117b2b07fe72f1da21",
    ),
    ("linux", "aarch64"): (
        "uv-aarch64-unknown-linux-gnu.tar.gz",
        "66393193038dd7eb108abd7a218d9cec04ac70ab98242b0720fa94de19223b7c",
    ),
}


def _bootstrap_dir() -> Path:
    # a sibling of the addon dir, just like the venvs, so it survives updates
    return Path(mw.pm.addonFolder(), "ankimorphs-python-bootstrap")


def _extra_search_dirs() -> list[str]:
    # anki inherits a minimal PATH when launched from the desktop, so
    # searching PATH alone would miss most user-installed tools
    home = Path.home()
    if is_win:
        return [str(home / ".local" / "bin")]
    dirs = [
        str(home / ".local" / "bin"),
        str(home / ".cargo" / "bin"),
        "/usr/local/bin",
        "/usr/bin",
    ]
    if is_mac:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        dirs += [
            "/opt/homebrew/bin",
            f"/Library/Frameworks/Python.framework/Versions/{python_version}/bin",
        ]
    return dirs


def _which(command: str) -> str | None:
    path_dirs = [
        directory
        for directory in os.environ.get("PATH", "").split(os.pathsep)
        if directory
    ]
    return shutil.which(command, path=os.pathsep.join(path_dirs + _extra_search_dirs()))


def _uv_version(version_output: str) -> tuple[int, int, int] | None:
    match = re.match(r"uv (\d+)\.(\d+)\.(\d+)", version_output)
    if match is None:
        return None
    return (int(match[1]), int(match[2]), int(match[3]))


def _find_native_uv() -> str | None:
    uv_path = _which("uv")
    if uv_path is None:
        return None
    try:
        result = subprocess.run(
            [uv_path, "--version"],
            check=True,
            text=True,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    version = _uv_version(result.stdout)
    if version is None or version < _MIN_NATIVE_UV_VERSION:
        return None
    return uv_path


def _probe_python(argv_prefix: list[str]) -> str | None:
    """
    Returns the interpreter's path if it is a regular CPython matching the
    python version and architecture of the anki process, otherwise None.
    """
    probe_code = (
        "import platform, sys, sysconfig\n"
        "print(sys.version_info.major)\n"
        "print(sys.version_info.minor)\n"
        "print(platform.machine())\n"
        "print(sys.implementation.name)\n"
        "print(sysconfig.get_config_var('Py_GIL_DISABLED') or 0)\n"
        "print(sys.executable)\n"
    )
    try:
        result = subprocess.run(
            [*argv_prefix, "-c", probe_code],
            check=True,
            text=True,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    lines = result.stdout.splitlines()
    if len(lines) < 6:
        return None

    expected = [
        str(sys.version_info.major),
        str(sys.version_info.minor),
        platform.machine(),
        "cpython",  # pypy venvs would select wheels anki cannot import
        "0",  # free-threaded builds use incompatible cp3XXt wheels
    ]
    if lines[:5] != expected:
        return None
    return lines[5].strip() or None


def _find_native_python() -> str | None:
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    argv_prefixes: list[list[str]] = []

    if is_win:
        # the py launcher is the canonical way to locate CPython on windows
        py_launcher = _which("py")
        if py_launcher is not None:
            argv_prefixes.append([py_launcher, f"-{python_version}"])

    versioned_binary = _which(f"python{python_version}")
    if versioned_binary is not None:
        argv_prefixes.append([versioned_binary])

    for argv_prefix in argv_prefixes:
        executable = _probe_python(argv_prefix)
        if executable is not None:
            return executable

    return None


def _uv_asset(platform_name: str, machine: str) -> tuple[str, str]:
    try:
        return _UV_ASSETS[(platform_name, machine)]
    except KeyError as error:
        raise RuntimeError(
            f"AnkiMorphs does not have a Python download for this platform"
            f" ({platform_name} {machine}). Please report this on the"
            f" AnkiMorphs github page."
        ) from error


def _download(url: str) -> bytes:
    try:
        client = HttpClient()
        response = client.get(url)
        # the annotation matters: mypy runs without anki installed in ci,
        # where stream_content would otherwise resolve to Any
        archive: bytes = client.stream_content(response)
        return archive
    except Exception as error:  # pylint:disable=broad-exception-caught
        raise RuntimeError(
            f"Downloading {url} failed. Check your internet connection and try again."
        ) from error


def _extract_uv_binary(archive: bytes, asset_name: str, destination: Path) -> None:
    # the zip has uv.exe at its root and the tarball nests uv inside a
    # uv-<target>/ directory, so we search by basename to tolerate layout
    # drift in future uv releases
    binary: bytes | None = None

    if asset_name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            for zip_name in zip_file.namelist():
                if os.path.basename(zip_name) == "uv.exe":
                    binary = zip_file.read(zip_name)
                    break
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar_file:
            for member in tar_file.getmembers():
                if os.path.basename(member.name) == "uv":
                    extracted = tar_file.extractfile(member)
                    if extracted is not None:
                        binary = extracted.read()
                    break

    if binary is None:
        raise RuntimeError(
            f"The downloaded archive {asset_name} did not contain a uv binary."
        )

    # write to a unique temp file and rename into place so interrupted or
    # concurrent installs never leave a half-written binary behind
    temp_fd, temp_name = tempfile.mkstemp(dir=destination.parent, suffix=".tmp")
    temp_destination = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "wb") as temp_file:
            temp_file.write(binary)
        if not is_win:
            temp_destination.chmod(0o755)
        os.replace(temp_destination, destination)
    finally:
        # gone already unless writing or renaming failed
        temp_destination.unlink(missing_ok=True)


def ensure_uv() -> str:
    uv_path = _bootstrap_dir() / "uv" / ("uv.exe" if is_win else "uv")

    if uv_path.exists():
        return str(uv_path)

    asset_name, expected_digest = _uv_asset(sys.platform, platform.machine().lower())
    archive = _download(_UV_RELEASE_URL + asset_name)

    if hashlib.sha256(archive).hexdigest() != expected_digest:
        raise RuntimeError(
            "The downloaded uv archive failed checksum verification."
            " Please try again."
        )

    uv_path.parent.mkdir(parents=True, exist_ok=True)
    _extract_uv_binary(archive, asset_name, uv_path)
    return str(uv_path)


def _uv_python_request() -> str:
    """
    An architecture-qualified python request (e.g. 'cpython-3.13-macos-
    aarch64-none') instead of a bare '3.13', so that uv provisions an
    interpreter matching the anki process even when the uv binary itself
    runs under a different architecture (e.g. a native arm64 uv while anki
    is an intel build running under rosetta).
    """
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    if sys.platform == "darwin":
        os_name, libc = "macos", "none"
    elif sys.platform == "win32":
        os_name, libc = "windows", "none"
    else:
        os_name, libc = "linux", "gnu"
    return f"cpython-{python_version}-{os_name}-{arch}-{libc}"


def create_managed_venv(venv_path: str) -> None:
    """
    Creates a venv with pip seeded into it, backed by a python interpreter of
    the same minor version as the one anki is running on. Interpreters and uv
    binaries already installed on the system are reused; downloading only
    happens when neither is available.
    """
    native_python = _find_native_python()
    if native_python is not None:
        try:
            subprocess.run(
                [native_python, "-m", "venv", venv_path],
                check=True,
                text=True,
                capture_output=True,
            )
            return
        except subprocess.CalledProcessError:
            # e.g. debian pythons without the python3-venv package; discard
            # the half-created venv and fall back to uv
            shutil.rmtree(venv_path, ignore_errors=True)

    env = os.environ.copy()
    uv_path = _find_native_uv()
    if uv_path is None:
        uv_path = ensure_uv()
        # keep the downloaded interpreter and cache inside the bootstrap dir
        # instead of ~/.local/share/uv etc. (a native uv keeps its own dirs,
        # so pythons it has already installed get reused)
        env["UV_PYTHON_INSTALL_DIR"] = str(_bootstrap_dir() / "python")
        env["UV_CACHE_DIR"] = str(_bootstrap_dir() / "cache")

    subprocess.run(
        [
            uv_path,
            "venv",
            "--seed",
            "--managed-python",
            "--no-config",
            "--python",
            _uv_python_request(),
            venv_path,
        ],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
