from typing import Optional


class Morpheme:
    __slots__ = (
        "lemma",
        "inflection",
        "part_of_speech",
        "sub_part_of_speech",
        "highest_learning_interval",
        "lemma_and_inflection",
    )

    def __init__(  # pylint:disable=too-many-arguments
        self,
        lemma: str,
        inflection: str,
        part_of_speech: str = "",
        sub_part_of_speech: str = "",
        highest_learning_interval: Optional[int] = None,
    ):
        """
        Lemma: dictionary form, e.g.: break
        Inflection: surface lemma, e.g.: broke, broken, etc.
        Part of speech: grammatical category, e.g.: nouns, verb.
        Sub Part of speech: no idea, probably more fine-grained categories. Used by Mecab.
        Highest Learning Interval: used to determine the 'known' status of the morph.
        """
        # mecab uses pos and sub_pos to determine proper nouns.

        self.lemma: str = lemma  # dictionary form
        self.inflection: str = inflection  # surface lemma
        self.part_of_speech = part_of_speech  # determined by mecab tool. for example: u'動詞' or u'助動詞', u'形容詞'
        self.sub_part_of_speech = sub_part_of_speech
        self.highest_learning_interval: Optional[int] = highest_learning_interval
        self.lemma_and_inflection: str = self.lemma + self.inflection

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, Morpheme)
        return all(
            [
                self.lemma == other.lemma,
                self.inflection == other.inflection,
            ]
        )

    def __hash__(self) -> int:
        return hash((self.lemma, self.inflection))

    def is_proper_noun(self) -> bool:
        return self.sub_part_of_speech == "固有名詞" or self.part_of_speech == "PROPN"


class MorphOccurrence:
    __slots__ = (
        "morph",
        "occurrence",
    )

    def __init__(self, morph: Morpheme) -> None:
        self.morph: Morpheme = morph
        self.occurrence: int = 1


# mypy crashes if the files don't run something...
pass  # pylint:disable=unnecessary-pass
