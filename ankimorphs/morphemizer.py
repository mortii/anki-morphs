import re
from functools import lru_cache
from typing import Optional

from .deps.jieba import posseg
from .deps.zhon.hanzi import characters
from .mecab_wrapper import get_mecab_identity, get_morphemes_mecab
from .morphemes import Morpheme

####################################################################################################
# Base Class
####################################################################################################


class Morphemizer:
    def __init__(self):
        pass

    @lru_cache(maxsize=131072)
    def get_morphemes_from_expr(self, expression: str) -> [Morpheme]:
        morphs = self._get_morphemes_from_expr(expression)
        return morphs

    def _get_morphemes_from_expr(self, expression: str) -> [Morpheme]:
        """
        The heart of this plugin: convert an expression to a list of its morphemes.
        """
        return []

    def get_description(self) -> str:
        """
        Returns a single line, for which languages this Morphemizer is.
        """
        return "No information available"

    def get_name(self) -> str:
        return self.__class__.__name__


####################################################################################################
# Morphemizer Helpers
####################################################################################################

morphemizers = None  # pylint:disable=invalid-name
morphemizers_by_name = {}


def get_all_morphemizers() -> [Morphemizer]:
    global morphemizers  # pylint:disable=global-statement
    if morphemizers is None:
        morphemizers = [
            SpaceMorphemizer(),
            MecabMorphemizer(),
            JiebaMorphemizer(),
            CjkCharMorphemizer(),
        ]

        for morphemizer in morphemizers:
            morphemizers_by_name[morphemizer.get_name()] = morphemizer

    return morphemizers


def get_morphemizer_by_name(name: str) -> Optional[Morphemizer]:
    get_all_morphemizers()
    return morphemizers_by_name.get(name, None)


####################################################################################################
# Mecab Morphemizer
####################################################################################################

space_char_regex = re.compile(" ")


class MecabMorphemizer(Morphemizer):
    """
    Because in japanese there are no spaces to differentiate between morphemes,
    a extra tool called 'mecab' has to be used.
    """

    def _get_morphemes_from_expr(self, expression):
        # Remove simple spaces that could be added by other add-ons and break the parsing.
        if space_char_regex.search(expression):
            expression = space_char_regex.sub("", expression)

        return get_morphemes_mecab(expression)

    def get_description(self):
        # try:
        identity = get_mecab_identity()
        # except:
        #     identity = "UNAVAILABLE"
        return "Japanese " + identity


####################################################################################################
# Space Morphemizer
####################################################################################################


class SpaceMorphemizer(Morphemizer):
    """
    Morphemizer for languages that use spaces (English, German, Spanish, ...). Because it is
    a general-use-morphemizer, it can't generate the base form from inflection.
    """

    def _get_morphemes_from_expr(self, expression):
        word_list = [
            word.lower() for word in re.findall(r"\b[^\s\d]+\b", expression, re.UNICODE)
        ]
        return [
            Morpheme(word, word, word, word, "UNKNOWN", "UNKNOWN") for word in word_list
        ]

    def get_description(self):
        return "Language w/ Spaces"


####################################################################################################
# CJK Character Morphemizer
####################################################################################################


class CjkCharMorphemizer(Morphemizer):
    """
    Morphemizer that splits sentence into characters and filters for Chinese-Japanese-Korean logographic/idiographic
    characters.
    """

    def _get_morphemes_from_expr(self, expression):
        return [
            Morpheme(character, character, character, character, "CJK_CHAR", "UNKNOWN")
            for character in re.findall(
                "[%s]" % characters,  # pylint:disable=consider-using-f-string
                expression,
            )
        ]

    def get_description(self):
        return "CJK Characters"


####################################################################################################
# Jieba Morphemizer (Chinese)
####################################################################################################


class JiebaMorphemizer(Morphemizer):
    """
    Jieba Chinese text segmentation: built to be the best Python Chinese word segmentation module.
    https://github.com/fxsjy/jieba
    """

    def _get_morphemes_from_expr(self, expression):
        # remove all punctuation
        expression = "".join(
            re.findall(
                "[%s]" % characters,  # pylint:disable=consider-using-f-string
                expression,
            )
        )
        return [
            Morpheme(m.word, m.word, m.word, m.word, m.flag, "UNKNOWN")
            for m in posseg.cut(expression)
        ]  # find morphemes using jieba's POS segmenter

    def get_description(self):
        return "Chinese"
