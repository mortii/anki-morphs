from __future__ import annotations

import sys
from pathlib import Path


def get_python_binary() -> str | None:
    """
    Returns a python interpreter that can bootstrap the spaCy/CAMeL venvs,
    or None if the anki install does not have one.

    Anki 25.09 and earlier ran from a uv-managed venv and exposed its python
    through 'aqt.package.venv_binary'. Anki 26.05 replaced the launcher with
    briefcase packaging, and 26.08 removed that function, so we fall back to
    the interpreter anki itself is running on. The official 26.x builds are
    self-contained apps where sys.executable is the anki binary instead of a
    python interpreter. When this returns None, uv_bootstrap downloads a
    standalone interpreter instead.
    """
    try:
        # pylint:disable=import-outside-toplevel
        from aqt.package import venv_binary
    except ImportError:
        pass
    else:
        launcher_python: str | None = venv_binary("python")
        if launcher_python is not None:
            return launcher_python

    # we can't run sys.executable to determine whether it is a python
    # interpreter, because doing that on a self-contained build launches
    # another anki instance
    if Path(sys.executable).name.lower().startswith("python"):
        return sys.executable

    return None
