from __future__ import annotations

from collections.abc import Iterator

from ..morpheme import Morpheme
from ..morphemizers.morphemizer import Morphemizer


class SimpleSpaceMorphemizer(Morphemizer):
    """
    This morphemizer only splits on whitespaces.
    """

    def init_successful(self) -> bool:
        return True  # this uses pure python, so it should always work

    def get_morphemes(self, sentences: list[str]) -> Iterator[list[Morpheme]]:
        for element in sentences:
            word_list = [word.lower() for word in element.split()]
            yield [Morpheme(lemma=word, inflection=word) for word in word_list]

    def get_description(self) -> str:
        return "AnkiMorphs: Simple Space Splitter"
