# -*- coding: utf-8 -*-
import importlib
import importlib.util
import re
import subprocess
import sys

from .morphemes import Morpheme
from .util_external import Memoize

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

MECAB_ENCODING = None
MECAB_POS_BLACKLIST = [
    "記号",  # "symbol", generally punctuation
    "補助記号",  # "symbol", generally punctuation
    "空白",  # Empty space
]
MECAB_SUBPOS_BLACKLIST = [
    "数詞",  # Numbers
]

IS_UNIDIC = True

KANJI = r"[㐀-䶵一-鿋豈-頻]"
wide_alpha_num_rx = re.compile(r"[０-９Ａ-Ｚａ-ｚ]")

mecab_source = ""


def extract_unicode_block(unicode_block, string):
    """extracts and returns all texts from a unicode block from string argument.
    Note that you must use the unicode blocks defined above, or patterns of similar form
    """
    return re.findall(unicode_block, string)


def get_mecab_identity():
    # Initialize mecab before we get the identity
    _mecab = mecab()

    # identify the mecab being used
    return mecab_source


def get_morpheme(parts):
    if IS_UNIDIC:
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
    else:
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


def get_morphemes_mecab(e):
    # Remove Unicode control codes before sending to MeCab.
    e = control_chars_re.sub("", e)
    ms = [get_morpheme(m.split("\t")) for m in interact(e).split("\r")]
    ms = [m for m in ms if m is not None]
    return ms


# [Str] -> subprocess.STARTUPINFO -> IO MecabProc
def spawn_mecab(base_cmd, startupinfo):
    """Try to start a MeCab subprocess in the given way, or fail.

    Raises OSError if the given base_cmd and startupinfo don't work
    for starting up MeCab, or the MeCab they produce has a dictionary
    incompatible with our assumptions.
    """
    global MECAB_ENCODING
    global IS_UNIDIC

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
        IS_UNIDIC = True
    elif (
        bos_feature_match is not None
        and bos_feature_match.group(1).strip() == MECAB_NODE_UNIDIC_22_BOS
    ):
        node_parts = MECAB_NODE_UNIDIC_22_PARTS
        IS_UNIDIC = True
    elif (
        bos_feature_match is not None
        and bos_feature_match.group(1).strip() == MECAB_NODE_IPADIC_BOS
    ):
        node_parts = MECAB_NODE_IPADIC_PARTS
        IS_UNIDIC = False
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
    MECAB_ENCODING = charset_match.group(1)

    args = [
        "--node-format=%s\r" % ("\t".join(node_parts),),
        "--eos-format=\n",
        "--unk-format=",
    ]
    return spawn_cmd(base_cmd + args, startupinfo)


@Memoize
def mecab():  # IO MecabProc
    """Start a MeCab subprocess and return it.
    `mecab` reads expressions from stdin at runtime, so only one
    instance is needed.  That's why this function is memoized.
    """

    global mecab_source  # make it global so we can query it later

    if sys.platform.startswith("win"):
        si = subprocess.STARTUPINFO()
        try:
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        except:
            # pylint: disable=no-member
            si.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    else:
        si = None

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
    if (
        (not reading)
        and importlib.util.find_spec("ankimorphs")
        and importlib.util.find_spec("ankimorphs.deps.mecab.reading")
    ):
        try:
            reading = importlib.import_module("ankimorphs.deps.mecab.reading")
            mecab_source = "MorphMan"
        except ModuleNotFoundError:
            pass

    # 6th priority - system mecab
    if not reading:
        try:
            return spawn_mecab(["mecab"], si), "System"
        except Exception as e:
            raise OSError(
                """
            Mecab Japanese analyzer could not be found.
            Please install one of the following Anki add-ons:
                 https://ankiweb.net/shared/info/3918629684
                 https://ankiweb.net/shared/info/13462835
                 https://ankiweb.net/shared/info/278530045"""
            ) from e

    m = reading.MecabController()
    m.setup()
    # m.mecabCmd[1:4] are assumed to be the format arguments.
    print(f"Using morphman: {mecab_source} with command line {m.mecabCmd}")

    return spawn_mecab(m.mecabCmd[:1] + m.mecabCmd[4:], si), mecab_source


def interact(expr):  # Str -> IO Str
    """ "interacts" with 'mecab' command: writes expression to stdin of 'mecab' process and gets all the morpheme
    info from its stdout."""
    mecab_process, _ = mecab()
    expr = expr.encode(MECAB_ENCODING, "ignore")

    # HACK: mecab sometimes does not produce the right morphs if there are no extra characters in the expression,
    # so we just add a whitespace at the end to prevent the problem.
    expr += b"&nbsp;"

    # The line terminator is always b'\n' for binary files: https://docs.python.org/3/library/io.html#io.IOBase
    mecab_process.stdin.write(expr + b"\n")
    # The buffer will be written out to the underlying RawIOBase object when flush() is called
    mecab_process.stdin.flush()
    mecab_process.stdout.flush()

    entire_output = ""
    lines_to_read = len(expr.split(b"\n"))

    for line in mecab_process.stdout.readlines(lines_to_read):
        entire_output += str(line.rstrip(b"\r\n"), MECAB_ENCODING)

    return entire_output


def fix_reading(m):  # Morpheme -> IO Morpheme
    """
    'mecab' prints the reading of the kanji in inflected forms (and strangely in katakana). So 歩い[て] will have アルイ as
    reading. This function sets the reading to the reading of the base form (in the example it will be 'アルク').
    """
    if m.pos in ["動詞", "助動詞", "形容詞"]:  # verb, aux verb, i-adj
        n = interact(m.base).split("\t")
        if len(n) == MECAB_NODE_LENGTH_IPADIC:
            m.read = n[MECAB_NODE_READING_INDEX].strip()
    return m
