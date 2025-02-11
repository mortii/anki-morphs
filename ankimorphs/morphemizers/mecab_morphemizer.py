import re
from collections.abc import Iterator

from ..morpheme import Morpheme
from ..morphemizers.morphemizer import Morphemizer
from . import mecab_wrapper

space_char_regex = re.compile(" ")


class MecabMorphemizer(Morphemizer):
    def __init__(self) -> None:
        super().__init__()
        mecab_wrapper.setup_mecab()

    def init_successful(self) -> bool:
        return mecab_wrapper.successful_import

    def get_morphemes(self, sentences: list[str]) -> Iterator[list[Morpheme]]:
        for sentence in sentences:
            # Remove simple spaces that could be added by other add-ons and break the parsing.
            if space_char_regex.search(sentence):
                sentence = space_char_regex.sub("", sentence)
            yield mecab_wrapper.get_morphemes_mecab(sentence)

    def get_description(self) -> str:
        return "AnkiMorphs: Japanese"
