from __future__ import annotations

import functools
import re

from ..morpheme import Morpheme
from . import jieba_wrapper, mecab_wrapper, spacy_wrapper

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
        morphemizers = [
            SimpleSpaceMorphemizer(),
        ]

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
# Simple Space Morphemizer
####################################################################################################


class SimpleSpaceMorphemizer(Morphemizer):
    """
    This morphemizer only splits on whitespaces.
    """

    def _get_morphemes_from_expr(self, expression: str) -> list[Morpheme]:
        word_list = [word.lower() for word in expression.split()]
        return [Morpheme(lemma=word, inflection=word) for word in word_list]

    def get_description(self) -> str:
        return "AnkiMorphs: Simple Space Splitter"


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
