from __future__ import annotations

import functools
import importlib
import importlib.util
import re
import subprocess
import sys
import threading
from types import ModuleType
from typing import IO, Any

from ..morpheme import Morpheme

# Serializes all access to the single shared MeCab subprocess. get_morphemes_mecab
# is decorated with lru_cache, which does NOT serialize concurrent calls to the
# wrapped function on a cache miss -- if this code is ever called from more than
# one thread, unsynchronized writes/reads to the same stdin/stdout pipe could
# interleave and silently swap results between calls. The lock costs nothing
# in the current single-threaded (QueryOp) call pattern and protects against
# this landmine if that ever changes.
_mecab_lock = threading.Lock()


_MECAB_NODE_IPADIC_PARTS = ["%f[6]", "%m", "%f[7]", "%f[0]", "%f[1]"]
_MECAB_NODE_LENGTH_IPADIC = len(_MECAB_NODE_IPADIC_PARTS)
_MECAB_POS_BLACKLIST = [
    "記号",  # "symbol", generally punctuation
    "補助記号",  # "symbol", generally punctuation
    "空白",  # Empty space
]
_MECAB_SUB_POS_BLACKLIST = [
    "数詞",  # Numbers
]

_control_chars_re = re.compile("[\x00-\x1f\x7f-\x9f]")
_wide_alpha_num_rx = re.compile(r"[０-９Ａ-Ｚａ-ｚ]")

# Any of these are line-terminator-like characters. If they appear inside a
# single "expression", MeCab (which reads stdin line-by-line) will treat the
# input as multiple sentences and emit multiple eos-terminated output lines
# for what we intend to be a single request/response pair. Since _interact
# reads back exactly one line per call, extra output lines would be left
# sitting unread in the pipe and misread as the response to a *later* call --
# corrupting the key<->morphs mapping for whatever expression comes next.
_newline_like_re = re.compile(r"[\r\n\u2028\u2029]")

_mecab_encoding: str | None = None
_mecab_complete_cmd: str | None = None  # pylint: disable=invalid-name
_mecab_base_cmd: list[str] | None = None
_mecab_windows_startupinfo: Any | None = None
_mecab_args = [
    "--node-format={}\r".format("\t".join(_MECAB_NODE_IPADIC_PARTS)),
    "--eos-format=\n",
    "--unk-format=",
]

successful_import: bool = False


def setup_mecab() -> None:
    global successful_import
    global _mecab_windows_startupinfo
    global _mecab_encoding
    global _mecab_base_cmd

    # startup_info has the type: subprocess.STARTUPINFO, but that type
    # is only available on Windows, so we can't use type annotations here
    _mecab_windows_startupinfo = get_windows_startup_info()
    reading: ModuleType

    if importlib.util.find_spec("1974309724"):
        reading = importlib.import_module("1974309724.reading")
    elif importlib.util.find_spec("ankimorphs_japanese_mecab"):
        reading = importlib.import_module("ankimorphs_japanese_mecab.reading")
    else:
        return

    _mecab = reading.MecabController()
    _mecab.setup()

    # _mecab.mecabCmd[1:4] are assumed to be the format arguments.
    _mecab_base_cmd = _mecab.mecabCmd[:1] + _mecab.mecabCmd[4:]

    dict_info_dump: bytes = _get_subprocess_dump(sub_cmd=["-D"])
    charset_match = re.search(
        "^charset:\t(.*)$", str(dict_info_dump, "utf-8"), flags=re.M
    )
    assert charset_match is not None
    _mecab_encoding = charset_match.group(1)  # example: utf8, type: <class 'str'>

    successful_import = True


def get_windows_startup_info() -> Any:
    if not sys.platform.startswith("win"):
        return None

    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startup_info


@functools.cache
def _spawn_mecab() -> subprocess.Popen[bytes]:
    """
    MeCab reads expressions from stdin at runtime, so only one instance is needed, hence the functools.cache.
    """
    assert _mecab_base_cmd is not None
    return _spawn_cmd(_mecab_base_cmd + _mecab_args, _mecab_windows_startupinfo)


def _get_subprocess_dump(sub_cmd: list[str]) -> bytes:
    assert _mecab_base_cmd is not None

    subprocess_stdout: IO[bytes] | None = _spawn_cmd(
        _mecab_base_cmd + sub_cmd,
        _mecab_windows_startupinfo,
    ).stdout

    assert subprocess_stdout is not None
    return subprocess_stdout.read()


def _spawn_cmd(cmd: list[str], _startupinfo: Any) -> subprocess.Popen[bytes]:
    # The 'startupinfo' parameter has the type: subprocess.STARTUPINFO,
    # that type is only available (and applicable) in Windows.
    return subprocess.Popen(
        cmd,
        startupinfo=_startupinfo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


@functools.lru_cache(maxsize=131072)
def get_morphemes_mecab(expression: str) -> list[Morpheme]:
    # Remove Unicode control codes before sending to MeCab.
    expression = _control_chars_re.sub("", expression)

    # Collapse to a single logical line. See _newline_like_re docstring above --
    # this is required for _interact's one-write/one-read-line contract to hold.
    expression = _newline_like_re.sub("", expression)

    # HACK: mecab sometimes does not produce the right morphs if there are no extra
    # characters in the expression, so we add a whitespace and a Japanese
    # punctuation mark "。" at the end to prevent the problem.
    expression += " 。"

    mecab_morphs: list[str] = _interact(expression).split("\r")
    actual_morphs: list[Morpheme] = []

    for morph_string in mecab_morphs:
        morph: Morpheme | None = _get_morpheme(morph_string.split("\t"))
        if morph is not None:
            actual_morphs.append(morph)

    return actual_morphs


def _get_morpheme(morph_string_parts: list[str]) -> Morpheme | None:
    if len(morph_string_parts) != _MECAB_NODE_LENGTH_IPADIC:
        return None

    pos = morph_string_parts[3] if morph_string_parts[3] != "" else "*"
    sub_pos = morph_string_parts[4] if morph_string_parts[4] != "" else "*"

    if (pos in _MECAB_POS_BLACKLIST) or (sub_pos in _MECAB_SUB_POS_BLACKLIST):
        return None

    lemma = morph_string_parts[0].strip()
    inflection = morph_string_parts[1].strip()

    return Morpheme(lemma, inflection)


def _interact(string_expression: str) -> str:  # Str -> IO Str
    """
    "Interacts" with the 'mecab' command: writes expression to stdin of the mecab
    process and reads back the morpheme info from its stdout.

    Precondition: string_expression must not contain any line-terminator-like
    characters (\\r, \\n, etc.) -- see get_morphemes_mecab, which enforces this
    before calling here. A single write must correspond to exactly one \\n-
    terminated line of output (per --eos-format=\\n), which is what readline()
    below assumes.
    """
    assert _mecab_encoding is not None

    bytes_expression = string_expression.encode(_mecab_encoding, errors="ignore")

    # Defensive: this should be impossible given get_morphemes_mecab's
    # preprocessing, but if it ever isn't, fail loudly instead of silently
    # desyncing the pipe.
    assert b"\n" not in bytes_expression, (
        f"expression contains embedded newline, would desync mecab pipe: "
        f"{string_expression!r}"
    )

    with _mecab_lock:
        mecab_process: subprocess.Popen[bytes] = _spawn_mecab()

        assert mecab_process.stdin is not None
        assert mecab_process.stdout is not None

        # The line terminator is always b'\n' for binary files:
        # https://docs.python.org/3/library/io.html#io.IOBase
        mecab_process.stdin.write(bytes_expression + b"\n")
        mecab_process.stdin.flush()

        # Read exactly one output line. --eos-format=\n guarantees mecab emits
        # one \n-terminated line per \n-terminated input line, and we've
        # guaranteed above that our input is exactly one line. readline() reads
        # until the next \n regardless of byte length, unlike readlines(hint)
        # (which takes a byte-size hint, not a line count, and was previously
        # being misused here as if it were the latter).
        line: bytes = mecab_process.stdout.readline()

    return str(line.rstrip(b"\r\n"), _mecab_encoding)
