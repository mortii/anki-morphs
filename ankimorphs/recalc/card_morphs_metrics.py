from ..ankimorphs_config import AnkiMorphsConfig
from ..morpheme import Morpheme


class CardMorphsMetrics:  # pylint:disable=too-many-instance-attributes
    __slots__ = (
        "all_morphs",
        "unknown_morphs",
        "num_learning_morphs",
        "has_learning_morphs",
        "total_priority_all_morphs",
        "total_priority_unknown_morphs",
        "total_priority_learning_morphs",
        "avg_priority_all_morphs",
        "avg_priority_learning_morphs",
    )

    def __init__(
        self,
        am_config: AnkiMorphsConfig,
        card_id: int,
        card_morph_map_cache: dict[int, list[Morpheme]],
        morph_priorities: dict[tuple[str, str], int],
    ) -> None:
        self.all_morphs: list[Morpheme] = []
        self.unknown_morphs: list[Morpheme] = []
        self.num_learning_morphs: int = 0
        self.has_learning_morphs: bool = False
        self.total_priority_all_morphs: int = 0
        self.total_priority_unknown_morphs: int = 0
        self.total_priority_learning_morphs: int = 0
        self.avg_priority_all_morphs: int = 0
        self.avg_priority_learning_morphs: int = 0

        try:
            self.all_morphs = card_morph_map_cache[card_id]
        except KeyError:
            # card does not have morphs or is buggy in some way
            return

        self._process(am_config, morph_priorities)

    def _process(
        self,
        am_config: AnkiMorphsConfig,
        morph_priorities: dict[tuple[str, str], int],
    ) -> None:
        default_morph_priority = len(morph_priorities) + 1
        learning_interval_attribute: str
        sub_key_attribute: str

        if am_config.evaluate_morph_inflection:
            learning_interval_attribute = "highest_inflection_learning_interval"
            sub_key_attribute = "inflection"
        else:
            learning_interval_attribute = "highest_lemma_learning_interval"
            sub_key_attribute = "lemma"

        for morph in self.all_morphs:
            learning_interval = getattr(morph, learning_interval_attribute)
            assert learning_interval is not None

            sub_key = getattr(morph, sub_key_attribute)
            assert sub_key is not None

            # this is a composite key consisting of either:
            # - (morph.lemma, morph.lemma)
            # - (morph.lemma, morph.inflection)
            key = (morph.lemma, sub_key)

            if key in morph_priorities:
                morph_priority = morph_priorities[key]
            else:
                morph_priority = default_morph_priority

            self.total_priority_all_morphs += morph_priority

            if learning_interval == 0:
                self.unknown_morphs.append(morph)
                self.total_priority_unknown_morphs += morph_priority
            elif learning_interval < am_config.interval_for_known_morphs:
                self.num_learning_morphs += 1
                self.total_priority_learning_morphs += morph_priority

        self.avg_priority_all_morphs = int(
            self.total_priority_all_morphs / len(self.all_morphs)
        )

        if self.num_learning_morphs > 0:
            self.has_learning_morphs = True
            self.avg_priority_learning_morphs = int(
                self.total_priority_learning_morphs / self.num_learning_morphs
            )

    @staticmethod
    def get_unknown_inflections(
        card_morph_map_cache: dict[int, list[Morpheme]],
        card_id: int,
    ) -> set[str]:
        card_unknown_morphs: set[str] = set()
        try:
            card_morphs: list[Morpheme] = card_morph_map_cache[card_id]
            for morph in card_morphs:
                assert morph.highest_inflection_learning_interval is not None
                if morph.highest_inflection_learning_interval == 0:
                    card_unknown_morphs.add(morph.inflection)
                    # we don't want to do anything to cards that have multiple unknown morphs
                    if len(card_unknown_morphs) > 1:
                        break
        except KeyError:
            pass  # card does not have morphs or is buggy in some way

        return card_unknown_morphs

    @staticmethod
    def get_unknown_lemmas(
        card_morph_map_cache: dict[int, list[Morpheme]],
        card_id: int,
    ) -> set[str]:
        card_unknown_morphs: set[str] = set()
        try:
            card_morphs: list[Morpheme] = card_morph_map_cache[card_id]
            for morph in card_morphs:
                assert morph.highest_lemma_learning_interval is not None
                if morph.highest_lemma_learning_interval == 0:
                    card_unknown_morphs.add(morph.lemma)
                    # we don't want to do anything to cards that have multiple unknown morphs
                    if len(card_unknown_morphs) > 1:
                        break
        except KeyError:
            pass  # card does not have morphs or is buggy in some way

        return card_unknown_morphs
