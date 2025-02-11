from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from .. import text_preprocessing
from ..ankimorphs_config import AnkiMorphsConfig
from ..morpheme import Morpheme


class Morphemizer(ABC):
    @abstractmethod
    def init_successful(self) -> bool:
        """
        Returns 'False' if something went wrong on startup
        """

    @abstractmethod
    def get_description(self) -> str:
        """
        Returns a string with the name of the morphemizer.
        """

    def get_processed_morphs(
        self, am_config: AnkiMorphsConfig, sentences: list[str]
    ) -> Iterator[list[Morpheme]]:
        for morphs in self.get_morphemes(sentences):
            if am_config.preprocess_ignore_names_morphemizer:
                morphs = self.remove_names_morphemizer(morphs)
            if am_config.preprocess_ignore_names_textfile:
                morphs = text_preprocessing.remove_names_textfile(morphs)
            yield morphs

    @abstractmethod
    def get_morphemes(self, sentences: list[str]) -> Iterator[list[Morpheme]]:
        pass

    @staticmethod
    def remove_names_morphemizer(morphs: list[Morpheme]) -> list[Morpheme]:
        return [morph for morph in morphs if not morph.is_proper_noun()]
