from __future__ import annotations

import importlib
import importlib.util
import sys
from types import ModuleType

from .morpheme import Morpheme

posseg: ModuleType | None = None
successful_startup: bool = False

################################################################################
# This section about cjk_ideographs is based on zhon/hanzi.py in:
# https://github.com/tsroten/zhon
################################################################################

#: Character code ranges for pertinent CJK ideograph Unicode blocks.
cjk_ideograph_unicode_ranges = [
    (0x3007, 0x3007),  # Ideographic number zero
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
]
if sys.maxunicode > 0xFFFF:
    cjk_ideograph_unicode_ranges += [
        (0x20000, 0x2A6DF),  # CJK Unified Ideographs Extension B
        (0x2A700, 0x2B73F),  # CJK Unified Ideographs Extension C
        (0x2B740, 0x2B81F),  # CJK Unified Ideographs Extension D
        (0x2F800, 0x2FA1F),  # CJK Compatibility Ideographs Supplement
    ]
################################################################################


def import_jieba() -> None:
    global posseg, successful_startup

    if importlib.util.find_spec("1857311956"):
        posseg = importlib.import_module("1857311956.jieba.posseg")
    elif importlib.util.find_spec("ankimorphs_chinese_jieba"):
        posseg = importlib.import_module("ankimorphs_chinese_jieba.jieba.posseg")
    else:
        return

    successful_startup = True


def get_morphemes_jieba(expression: str) -> list[Morpheme]:
    assert posseg is not None
    _morphs: list[Morpheme] = []

    # The "posseg.cut" function returns "Pair" instances:
    #   Pair.word
    #   Pair.flag  # part of speech
    for posseg_pair in posseg.cut(expression):
        if text_contains_only_cjk_ranges(_text=posseg_pair.word) is False:
            continue

        # chinese does not have inflections, so we use the lemma for both
        _morphs.append(Morpheme(lemma=posseg_pair.word, inflection=posseg_pair.word))

    return _morphs


def char_found_in_cjk_ranges(_char: str) -> bool:
    for start, end in cjk_ideograph_unicode_ranges:
        if start <= ord(_char) <= end:
            return True
    return False


def text_contains_only_cjk_ranges(_text: str) -> bool:
    for char in _text:
        if not char_found_in_cjk_ranges(char):
            return False
    return True
