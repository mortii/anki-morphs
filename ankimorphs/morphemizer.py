from __future__ import annotations

import functools
import re

from . import jieba_wrapper, mecab_wrapper, spacy_wrapper
from .morpheme import Morpheme

space_char_regex = re.compile(" ")


####################################################################################################
# Base Class
####################################################################################################


class Morphemizer:
    def __init__(self) -> None:
        pass

    # the cache needs to have a max size to maintain garbage collection
    @functools.lru_cache(maxsize=131072)
    def get_morphemes_from_expr(self, expression: str) -> list[Morpheme]:
        morphs = self._get_morphemes_from_expr(expression)
        return morphs

    def _get_morphemes_from_expr(  # pylint:disable=unused-argument
        self, expression: str
    ) -> list[Morpheme]:
        """
        The heart of this plugin: convert an expression to a list of its morphemes.
        """
        return []

    def get_description(self) -> str:
        """
        Returns a single line, for which languages this Morphemizer is.
        """
        return "No information available"


####################################################################################################
# Morphemizer Helpers
####################################################################################################

morphemizers: list[Morphemizer] | None = None
morphemizers_by_description: dict[str, Morphemizer] = {}


def get_all_morphemizers() -> list[Morphemizer]:
    global morphemizers

    if morphemizers is None:
        # the space morphemizer is just a regex splitter, and is
        # therefore always included since nothing has to be installed
        morphemizers = [SpaceMorphemizer()]

        _mecab = MecabMorphemizer()
        if mecab_wrapper.successful_startup:
            morphemizers.append(_mecab)

        _jieba = JiebaMorphemizer()
        if jieba_wrapper.successful_startup:
            morphemizers.append(_jieba)

        for spacy_model in spacy_wrapper.get_installed_models():
            morphemizers.append(SpacyMorphemizer(spacy_model))

        # update the 'names to morphemizers' dict while we are at it
        for morphemizer in morphemizers:
            morphemizers_by_description[morphemizer.get_description()] = morphemizer

    return morphemizers


def get_morphemizer_by_description(description: str) -> Morphemizer | None:
    get_all_morphemizers()
    return morphemizers_by_description.get(description, None)


####################################################################################################
# Mecab Morphemizer
####################################################################################################


class MecabMorphemizer(Morphemizer):

    def __init__(self) -> None:
        super().__init__()
        mecab_wrapper.setup_mecab()

    def _get_morphemes_from_expr(self, expression: str) -> list[Morpheme]:
        # Remove simple spaces that could be added by other add-ons and break the parsing.
        if space_char_regex.search(expression):
            expression = space_char_regex.sub("", expression)
        return mecab_wrapper.get_morphemes_mecab(expression)

    def get_description(self) -> str:
        return "AnkiMorphs: Japanese"


####################################################################################################
# Space Morphemizer
####################################################################################################


class SpaceMorphemizer(Morphemizer):
    """
    Morphemizer for languages that use spaces (English, German, Spanish, ...). Because it is
    a general-use-morphemizer, it can't generate the base form from inflection.
    """

    def _get_morphemes_from_expr(self, expression: str) -> list[Morpheme]:
        # We want the expression: "At 3 o'clock that god-forsaken-man shows up..."
        # to produce: ['at', '3', "o'clock", 'that', 'god-forsaken-man', 'shows', 'up']
        #
        # Regex:
        # The '\w' character matches alphanumeric and underscore characters
        #
        # To also match words that have multiple hyphens or apostrophes, we add
        # the optional group: '([-']\w+)*'
        #
        # re.findall() treats groups in a special way:
        #   "If one or more capturing groups are present in the pattern, return
        #    a list of groups; this will be a list of tuples if the pattern
        #    has more than one group."
        # We don't want this to happen, we want a pure list of matches. To prevent
        # this we prepend '?:' to make the group non-capturing.

        word_list = [
            word.lower()
            for word in re.findall(r"\w+(?:[-']\w+)*", expression, re.UNICODE)
        ]
        return [Morpheme(lemma=word, inflection=word) for word in word_list]

    def get_description(self) -> str:
        return "AnkiMorphs: Language w/ Spaces"


####################################################################################################
# spaCy Morphemizer
####################################################################################################


class SpacyMorphemizer(Morphemizer):
    """Mostly a stub class for spaCy"""

    def __init__(self, spacy_model: str):
        super().__init__()
        self.spacy_model: str = spacy_model

    def get_description(self) -> str:
        return f"spaCy: {self.spacy_model}"


####################################################################################################
# Jieba Morphemizer (Chinese)
####################################################################################################


class JiebaMorphemizer(Morphemizer):
    # Jieba Chinese text segmentation: https://github.com/fxsjy/jieba

    def __init__(self) -> None:
        super().__init__()
        jieba_wrapper.import_jieba()

    def _get_morphemes_from_expr(self, expression: str) -> list[Morpheme]:
        return jieba_wrapper.get_morphemes_jieba(expression)

    def get_description(self) -> str:
        return "AnkiMorphs: Chinese"
