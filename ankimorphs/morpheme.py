from typing import Optional


class Morpheme:
    __slots__ = (
        "base",
        "inflected",
        "pos",
        "sub_pos",
        "highest_learning_interval",
        "base_and_inflected",
    )

    def __init__(  # pylint:disable=too-many-arguments
        self,
        base: str,
        inflected: str,
        pos: str = "",
        sub_pos: str = "",
        highest_learning_interval: Optional[int] = None,
    ):
        # base = lemma
        # inflected = surface lemma
        # mecab uses pos and sub_pos to determine proper nouns.

        self.base: str = base
        self.inflected: str = inflected
        self.pos = pos  # determined by mecab tool. for example: u'動詞' or u'助動詞', u'形容詞'
        self.sub_pos = sub_pos
        self.highest_learning_interval: Optional[int] = highest_learning_interval
        self.base_and_inflected: str = self.base + self.inflected

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, Morpheme)
        return all(
            [
                self.base == other.base,
                self.inflected == other.inflected,
            ]
        )

    def __hash__(self) -> int:
        return hash((self.base, self.inflected))

    def is_proper_noun(self) -> bool:
        return self.sub_pos == "固有名詞" or self.pos == "PROPN"


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
