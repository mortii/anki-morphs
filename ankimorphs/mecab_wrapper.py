import functools
import importlib
import importlib.util
import os
import re
import subprocess
import sys
from typing import Optional

from .morpheme import Morpheme

####################################################################################################
# Mecab Morphemizer
####################################################################################################


MECAB_NODE_UNIDIC_BOS = "BOS/EOS,*,*,*,*,*,*,*,*,*,*,*,*,*"
MECAB_NODE_UNIDIC_PARTS = ["%f[7]", "%f[12]", "%m", "%f[6]", "%f[0]", "%f[1]"]
MECAB_NODE_LENGTH_UNIDIC = len(MECAB_NODE_UNIDIC_PARTS)
MECAB_NODE_UNIDIC_22_BOS = "BOS/EOS,*,*,*,*,*,*,*,*,*,*,*,*,*,*,*,*"
MECAB_NODE_UNIDIC_22_PARTS = ["%f[7]", "%f[10]", "%m", "%f[6]", "%f[0]", "%f[1]"]
MECAB_NODE_IPADIC_BOS = "BOS/EOS,*,*,*,*,*,*,*,*"
MECAB_NODE_IPADIC_PARTS = ["%f[6]", "%m", "%f[7]", "%f[0]", "%f[1]"]
MECAB_NODE_LENGTH_IPADIC = len(MECAB_NODE_IPADIC_PARTS)
MECAB_NODE_READING_INDEX = 2

mecab_encoding = None  # pylint:disable=invalid-name
MECAB_POS_BLACKLIST = [
    "記号",  # "symbol", generally punctuation
    "補助記号",  # "symbol", generally punctuation
    "空白",  # Empty space
]
MECAB_SUBPOS_BLACKLIST = [
    "数詞",  # Numbers
]

is_unidic = True  # pylint:disable=invalid-name

wide_alpha_num_rx = re.compile(r"[０-９Ａ-Ｚａ-ｚ]")

mecab_source = ""  # pylint:disable=invalid-name


def get_mecab_identity():
    # Initialize mecab before we get the identity
    _mecab = mecab()

    # identify the mecab being used
    return mecab_source


def get_morpheme(  # pylint:disable=too-many-return-statements
    parts,
) -> Optional[Morpheme]:
    if is_unidic:
        if len(parts) != MECAB_NODE_LENGTH_UNIDIC:
            return None

        pos = parts[4] if parts[4] != "" else "*"
        sub_pos = parts[5] if parts[5] != "" else "*"

        # Drop blacklisted parts of speech
        if (pos in MECAB_POS_BLACKLIST) or (sub_pos in MECAB_SUBPOS_BLACKLIST):
            return None

        # Drop wide alpha-numeric morphemes
        if wide_alpha_num_rx.search(parts[1]):
            return None

        norm = parts[0].strip()
        base = parts[1].strip()
        inflected = parts[2].strip()
        reading = parts[3].strip()

        return Morpheme(norm, base, inflected, reading, pos, sub_pos)

    if len(parts) != MECAB_NODE_LENGTH_IPADIC:
        return None

    pos = parts[3] if parts[3] != "" else "*"
    sub_pos = parts[4] if parts[4] != "" else "*"

    if (pos in MECAB_POS_BLACKLIST) or (sub_pos in MECAB_SUBPOS_BLACKLIST):
        return None

    norm = parts[0].strip()
    base = norm
    inflected = parts[1].strip()
    reading = parts[2].strip()

    _morph = fix_reading(Morpheme(norm, base, inflected, reading, pos, sub_pos))
    return _morph


control_chars_re = re.compile("[\x00-\x1f\x7f-\x9f]")


def get_morphemes_mecab(expression):
    # HACK: mecab sometimes does not produce the right morphs if there are no extra characters in the expression,
    # so we just add a whitespace and a japanese punctuation mark "。" the end to prevent the problem.
    expression += " 。"

    # Remove Unicode control codes before sending to MeCab.
    expression = control_chars_re.sub("", expression)

    _morphs = [get_morpheme(m.split("\t")) for m in interact(expression).split("\r")]

    _morphs = [_morph for _morph in _morphs if _morph is not None]
    return _morphs


# [Str] -> subprocess.STARTUPINFO -> IO MecabProc
def spawn_mecab(base_cmd, startupinfo):
    """Try to start a MeCab subprocess in the given way, or fail.

    Raises OSError if the given base_cmd and startupinfo don't work
    for starting up MeCab, or the MeCab they produce has a dictionary
    incompatible with our assumptions.
    """
    global mecab_encoding  # pylint: disable=global-statement
    global is_unidic  # pylint: disable=global-statement

    # [Str] -> subprocess.STARTUPINFO -> IO subprocess.Popen
    def spawn_cmd(cmd, _startupinfo):
        return subprocess.Popen(
            cmd,
            startupinfo=_startupinfo,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    config_dump = spawn_cmd(base_cmd + ["-P"], startupinfo).stdout.read()
    bos_feature_match = re.search(
        "^bos-feature: (.*)$", str(config_dump, "utf-8"), flags=re.M
    )

    if (
        bos_feature_match is not None
        and bos_feature_match.group(1).strip() == MECAB_NODE_UNIDIC_BOS
    ):
        node_parts = MECAB_NODE_UNIDIC_PARTS
        is_unidic = True
    elif (
        bos_feature_match is not None
        and bos_feature_match.group(1).strip() == MECAB_NODE_UNIDIC_22_BOS
    ):
        node_parts = MECAB_NODE_UNIDIC_22_PARTS
        is_unidic = True
    elif (
        bos_feature_match is not None
        and bos_feature_match.group(1).strip() == MECAB_NODE_IPADIC_BOS
    ):
        node_parts = MECAB_NODE_IPADIC_PARTS
        is_unidic = False
    else:
        raise OSError(
            "Unexpected MeCab dictionary format; unidic or ipadic required.\n"
            "Try installing the 'Mecab Unidic' or 'Japanese Support' addons,\n"
            "or if using your system's `mecab` try installing a package\n"
            "like `mecab-ipadic`\n"
        )

    dicinfo_dump = spawn_cmd(base_cmd + ["-D"], startupinfo).stdout.read()
    charset_match = re.search(
        "^charset:\t(.*)$", str(dicinfo_dump, "utf-8"), flags=re.M
    )
    if charset_match is None:
        raise OSError(
            "Can't find charset in MeCab dictionary info (`$MECAB -D`):\n\n"
            + dicinfo_dump
        )
    mecab_encoding = charset_match.group(1)

    args = [
        "--node-format={}\r".format("\t".join(node_parts)),
        "--eos-format=\n",
        "--unk-format=",
    ]
    return spawn_cmd(base_cmd + args, startupinfo)


@functools.cache
def mecab():  # pylint: disable=too-many-branches,too-many-statements
    """Start a MeCab subprocess and return it.
    `mecab` reads expressions from stdin at runtime, so only one
    instance is needed.  That's why this function is memoized.
    """

    global mecab_source  # make it global so we can query it later  # pylint: disable=global-statement

    if sys.platform.startswith("win"):
        startup_info = subprocess.STARTUPINFO()
        try:
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        except subprocess.TimeoutExpired:
            # pylint: disable=no-member
            startup_info.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    else:
        startup_info = None

    # Search for mecab
    reading = None

    # 1st priority - MecabUnidic
    if importlib.util.find_spec("MecabUnidic"):
        try:
            reading = importlib.import_module("MecabUnidic.reading")
            mecab_source = "MecabUnidic from addon MecabUnidic"
        except ModuleNotFoundError:
            pass

    if importlib.util.find_spec("13462835"):
        try:
            reading = importlib.import_module("13462835.reading")
            mecab_source = "MecabUnidic from addon 13462835"
        except ModuleNotFoundError:
            pass

    # 2nd priority - Japanese Support
    if (not reading) and importlib.util.find_spec("3918629684"):
        try:
            reading = importlib.import_module("3918629684.reading")
            mecab_source = "Japanese Support from addon 3918629684"
        except ModuleNotFoundError:
            pass

    # 3nd priority - MIAJapaneseSupport
    if (not reading) and importlib.util.find_spec("MIAJapaneseSupport"):
        try:
            reading = importlib.import_module("MIAJapaneseSupport.reading")
            mecab_source = "MIAJapaneseSupport from addon MIAJapaneseSupport"
        except ModuleNotFoundError:
            pass
    # 4nd priority - MigakuJapaneseSupport via Anki code (278530045)
    if (not reading) and importlib.util.find_spec("278530045"):
        try:
            reading = importlib.import_module("278530045.reading")
            mecab_source = "Migaku Japanese support from addon 278530045"
        except ModuleNotFoundError:
            pass

    # 5th priority - From Morphman
    if not reading:
        file_path = os.path.realpath(__file__)
        am_dir = file_path.split(os.sep)[-2]
        mecab_dir = am_dir + ".deps.mecab.reading"
        reading = importlib.import_module(mecab_dir)
        mecab_source = "ankimorphs"

    # 6th priority - system mecab
    # if not reading:
    #     try:
    #         return spawn_mecab(["mecab"], startup_info), "System"
    #     except Exception as error:
    #         raise OSError(
    #             """
    #         Mecab Japanese analyzer could not be found.
    #         Please install one of the following Anki add-ons:
    #              https://ankiweb.net/shared/info/3918629684
    #              https://ankiweb.net/shared/info/13462835
    #              https://ankiweb.net/shared/info/278530045"""
    #         ) from error

    _mecab = reading.MecabController()
    _mecab.setup()
    # m.mecabCmd[1:4] are assumed to be the format arguments.
    print(f"Using ankimorphs: {mecab_source} with command line {_mecab.mecabCmd}")

    return (
        spawn_mecab(_mecab.mecabCmd[:1] + _mecab.mecabCmd[4:], startup_info),
        mecab_source,
    )


def interact(expr):  # Str -> IO Str
    """ "interacts" with 'mecab' command: writes expression to stdin of 'mecab' process and gets all the morpheme
    info from its stdout."""
    mecab_process, _ = mecab()
    expr = expr.encode(mecab_encoding, "ignore")

    # The line terminator is always b'\n' for binary files: https://docs.python.org/3/library/io.html#io.IOBase
    mecab_process.stdin.write(expr + b"\n")
    # The buffer will be written out to the underlying RawIOBase object when flush() is called
    mecab_process.stdin.flush()
    mecab_process.stdout.flush()

    entire_output = ""
    lines_to_read = len(expr.split(b"\n"))

    for line in mecab_process.stdout.readlines(lines_to_read):
        entire_output += str(line.rstrip(b"\r\n"), mecab_encoding)

    return entire_output


def fix_reading(_morph):  # Morpheme -> IO Morpheme
    """
    'mecab' prints the reading of the kanji in inflected forms (and strangely in katakana). So 歩い[て] will have アルイ as
    reading. This function sets the reading to the reading of the base form (in the example it will be 'アルク').
    """
    if _morph.pos in ["動詞", "助動詞", "形容詞"]:  # verb, aux verb, i-adj
        line = interact(_morph.base).split("\t")
        if len(line) == MECAB_NODE_LENGTH_IPADIC:
            _morph.read = line[MECAB_NODE_READING_INDEX].strip()
    return _morph
