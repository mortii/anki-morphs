import re
from collections.abc import Iterator
from typing import Any

from .. import text_preprocessing
from ..ankimorphs_config import AnkiMorphsConfig
from ..morpheme import Morpheme
from ..morphemizers import spacy_wrapper
from ..morphemizers.morphemizer import Morphemizer

# matches strings/words entirely made up of punctuations and symbols
punctuation_and_symbols = re.compile(r"^[\W_]+$", re.UNICODE)


class SpacyMorphemizer(Morphemizer):
    def __init__(self, spacy_model: str):
        super().__init__()
        self.spacy_model: str = spacy_model
        # part of speech tags: https://universaldependencies.org/u/pos/
        self.excluded_pos = {"X", "SPACE", "SYM", "PUNCT"}

    def get_processed_morphs(
        self, am_config: AnkiMorphsConfig, sentences: list[str]
    ) -> Iterator[list[Morpheme]]:

        # creating nlp objects is very expensive so we do it lazily here (cached)
        nlp: Any = spacy_wrapper.get_nlp(self.spacy_model)

        for doc in nlp.pipe(sentences):
            morphs: list[Morpheme] = []

            # doc: spacy.tokens.Doc
            for w in doc:

                if w.pos_ in self.excluded_pos:
                    continue

                if am_config.preprocess_ignore_names_morphemizer and w.pos_ == "PROPN":
                    continue

                if am_config.preprocess_ignore_numbers and w.pos_ == "NUM":
                    continue

                # spaCy can miscategorize text, so we include this as a failsafe.
                if punctuation_and_symbols.match(w.text):
                    continue

                morphs.append(
                    Morpheme(
                        lemma=w.lemma_,
                        inflection=w.text,
                    )
                )

            if am_config.preprocess_ignore_names_textfile:
                morphs = text_preprocessing.remove_names_textfile(morphs)

            yield morphs

    def get_morphemes(self, sentences: list[str]) -> Iterator[list[Morpheme]]:
        """
        Use 'get_processed_morphs()' instead of this
        """
        yield []

    def init_successful(self) -> bool:
        return spacy_wrapper.successful_import

    def get_description(self) -> str:
        return f"spaCy: {self.spacy_model}"
