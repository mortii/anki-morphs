from __future__ import annotations

import re
from collections.abc import Iterator

from .. import text_preprocessing
from ..ankimorphs_config import AnkiMorphsConfig
from ..morpheme import Morpheme
from ..morphemizers import camel_wrapper
from ..morphemizers.morphemizer import Morphemizer


class CamelMorphemizer(Morphemizer):
    def __init__(self, db_name: str) -> None:
        super().__init__()
        self.db_name = db_name
        # CAMeL POS tags to skip entirely (punctuation, digits, Latin, foreign text)
        self.excluded_pos = {"PUNC", "DIGIT", "LATIN", "FOREIGN"}
        # CAMeL source values that indicate non-Arabic tokens
        self.excluded_sources = {"punc", "digit", "foreign"}

    def get_processed_morphs(
        self, am_config: AnkiMorphsConfig, sentences: list[str]
    ) -> Iterator[list[Morpheme]]:
        analyzer = camel_wrapper.get_analyzer(self.db_name)

        for sentence in sentences:
            morphs: list[Morpheme] = []

            for word in sentence.split():
                try:
                    analyses = analyzer.analyze(word)
                except re.error:
                    # Safety net: some camel-tools code paths build a regex from
                    # the surface form and can raise on certain inputs (e.g. the
                    # backoff re.sub bug under Python 3.13). Skip such words rather
                    # than aborting the whole generation run.
                    continue
                if not analyses:
                    continue

                best = max(analyses, key=lambda a: a.get("pos_lex_logprob", -99.0))
                pos = best.get("pos", "").upper()
                source = best.get("source", "")

                if pos in self.excluded_pos or source in self.excluded_sources:
                    continue

                if am_config.preprocess_ignore_numbers and pos == "NOUN_NUM":
                    continue

                # CAMeL proper noun POS contains "PROP" (e.g. "NOUN_PROP")
                if am_config.preprocess_ignore_names_morphemizer and "PROP" in pos:
                    continue

                lemma = best.get("lex", word)
                morphs.append(
                    Morpheme(
                        lemma=lemma,
                        inflection=word,
                        part_of_speech=pos,
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
        return camel_wrapper.successful_import

    def get_description(self) -> str:
        label = camel_wrapper.available_databases.get(self.db_name, self.db_name)
        return f"CAMeL Tools: {label}"
