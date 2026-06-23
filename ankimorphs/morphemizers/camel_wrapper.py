from __future__ import annotations

import functools
import os.path
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from anki.utils import is_win
from aqt import mw
from aqt.package import venv_binary

# pylint: disable=invalid-name,duplicate-code

updated_python_path: bool = False
testing_environment: bool = False
successful_import: bool = False

_camel_MorphologyDB: Any = None
_camel_Analyzer: Any = None

# pylint: enable=invalid-name

available_databases: dict[str, str] = {
    "calima-msa-r13": "Modern Standard Arabic",
    "calima-egy-r13": "Egyptian Arabic",
    "calima-glf-01": "Gulf Arabic",
}

_DB_TO_PACKAGE: dict[str, str] = {
    "calima-msa-r13": "morphology-db-msa-r13",
    "calima-egy-r13": "morphology-db-egy-r13",
    "calima-glf-01": "morphology-db-glf-01",
}


def _camel_environment() -> dict[str, str]:
    env = os.environ.copy()

    env.setdefault(
        "CAMELTOOLS_DATA",
        str(_get_am_camel_venv_data_path()),
    )

    if platform.machine() == "arm64":
        env["CMAKE_OSX_ARCHITECTURES"] = "arm64"

    return env


def _configure_camel_environment() -> None:
    os.environ.update(_camel_environment())


def _get_am_camel_venv_python() -> Path:
    if is_win:
        return Path(_get_am_camel_venv_path(), "Scripts", "python.exe")
    return Path(_get_am_camel_venv_path(), "bin", "python")


def _get_am_camel_venv_path() -> Path:
    python_version = f"{sys.version_info.major}_{sys.version_info.minor}"
    return Path(mw.pm.addonFolder(), f"camel-venv-python-{python_version}")


def _get_am_camel_venv_data_path() -> Path:
    return Path(_get_am_camel_venv_path(), "camel_tools_data")


def load_camel_modules() -> None:
    global updated_python_path
    global successful_import
    global _camel_MorphologyDB
    global _camel_Analyzer

    if not updated_python_path and not testing_environment:
        assert mw is not None

        camel_venv_path = _get_am_camel_venv_path()
        if not camel_venv_path.exists():
            return

        _configure_camel_environment()

        if is_win is True:
            camel_site_packages_path = os.path.join(
                camel_venv_path, "Lib", "site-packages"
            )
        else:
            camel_site_packages_path = os.path.join(
                camel_venv_path,
                "lib",
                f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            )

        sys.path.append(camel_site_packages_path)
        updated_python_path = True

    try:
        # pylint:disable=import-outside-toplevel
        from camel_tools.morphology.analyzer import Analyzer
        from camel_tools.morphology.database import MorphologyDB

        # pylint:enable=import-outside-toplevel
        _camel_MorphologyDB = MorphologyDB
        _camel_Analyzer = Analyzer

        successful_import = True

    except ModuleNotFoundError:
        pass


def get_installed_databases() -> list[str]:
    installed: list[str] = []

    if not successful_import:
        return installed

    assert _camel_MorphologyDB is not None

    for db_name in available_databases:
        try:
            _camel_MorphologyDB.builtin_db(db_name, flags="a")
            installed.append(db_name)
        except FileNotFoundError:
            pass

    return installed


def create_camel_venv() -> None:
    camel_venv_path = _get_am_camel_venv_path()

    shutil.rmtree(camel_venv_path, ignore_errors=True)

    python_path: str | None = venv_binary("python")
    if python_path is None:
        raise ValueError(
            "Anki API error. Install Anki from the official website to avoid this issue."
        )

    subprocess.run([python_path, "-m", "venv", camel_venv_path], check=True)

    # create the data dir to prevent a crash (bug in camel tools)
    _get_am_camel_venv_data_path().mkdir()

    if is_win:
        camel_venv_python = os.path.join(camel_venv_path, "Scripts", "python.exe")
    else:
        camel_venv_python = os.path.join(camel_venv_path, "bin", "python")

    subprocess.run(
        [
            camel_venv_python,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        check=True,
    )

    _configure_camel_environment()
    env = os.environ.copy()

    subprocess.run(
        [
            camel_venv_python,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--upgrade",
            "camel-tools",
        ],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )


def delete_camel_venv() -> None:
    camel_venv_path = _get_am_camel_venv_path()
    try:
        shutil.rmtree(camel_venv_path)
    except PermissionError:
        (Path(camel_venv_path) / ".delete_me").touch()


def maybe_delete_camel_venv() -> None:
    camel_venv_path = _get_am_camel_venv_path()
    flag = Path(camel_venv_path, ".delete_me")
    if flag.exists():
        shutil.rmtree(camel_venv_path)


def install_database(db_name: str) -> None:
    package_name = _DB_TO_PACKAGE.get(db_name)
    if package_name is None:
        raise ValueError(f"Unknown database: {db_name}")

    camel_venv_python = _get_am_camel_venv_python()
    env = os.environ.copy()

    subprocess.run(
        [
            camel_venv_python,
            "-m",
            "camel_tools.cli.camel_data",
            "--install",
            package_name,
        ],
        check=True,
        env=env,
    )


# the cache needs to have a max size to maintain garbage collection
@functools.lru_cache(maxsize=8)
def get_analyzer(db_name: str) -> Any:
    if not successful_import:
        return None

    assert _camel_MorphologyDB is not None
    assert _camel_Analyzer is not None

    db = _camel_MorphologyDB.builtin_db(db_name, flags="a")
    # backoff="NONE": out-of-vocabulary words return no analysis and are skipped,
    # rather than CAMeL fabricating a guessed (noisy) lemma from the surface form.
    # This is both better data for frequency/priority files and avoids CAMeL's
    # NOAN backoff path, which crashes on Python 3.13 (re.sub arg-order bug in
    # camel-tools 1.6.0 trips the stricter 3.13 replacement-template parser).
    return _camel_Analyzer(db, backoff="NONE", cache_size=1000)
