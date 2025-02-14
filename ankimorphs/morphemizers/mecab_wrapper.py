from __future__ import annotations

import functools
import importlib
import importlib.util
import re
import subprocess
import sys
from types import ModuleType
from typing import IO, Any

from ..morpheme import Morpheme

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

_mecab_encoding: str | None = None
_mecab_complete_cmd: str | None = None
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


# the cache needs to have a max size to maintain garbage collection
@functools.lru_cache(maxsize=131072)
def get_morphemes_mecab(expression: str) -> list[Morpheme]:
    # HACK: mecab sometimes does not produce the right morphs if there are no extra characters in the expression,
    # so we just add a whitespace and a japanese punctuation mark "。" at the end to prevent the problem.
    expression += " 。"

    # Remove Unicode control codes before sending to MeCab.
    expression = _control_chars_re.sub("", expression)

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
    "interacts" with 'mecab' command: writes expression to stdin of 'mecab' process and gets all the morpheme
    info from its stdout.
    """
    mecab_process: subprocess.Popen[bytes] = _spawn_mecab()

    assert mecab_process.stdin is not None
    assert mecab_process.stdout is not None
    assert _mecab_encoding is not None

    bytes_expression = string_expression.encode(_mecab_encoding, errors="ignore")

    # The line terminator is always b'\n' for binary files: https://docs.python.org/3/library/io.html#io.IOBase
    mecab_process.stdin.write(bytes_expression + b"\n")

    # The buffer will be written out to the underlying RawIOBase object when flush() is called
    mecab_process.stdin.flush()
    mecab_process.stdout.flush()

    entire_output: str = ""
    lines_to_read = len(bytes_expression.split(b"\n"))

    for line in mecab_process.stdout.readlines(lines_to_read):
        entire_output += str(line.rstrip(b"\r\n"), _mecab_encoding)

    return entire_output
