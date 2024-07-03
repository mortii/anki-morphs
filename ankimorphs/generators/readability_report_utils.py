from __future__ import annotations

from ..ankimorphs_config import AnkiMorphsConfig
from ..ankimorphs_db import AnkiMorphsDB
from ..morpheme import Morpheme, MorphOccurrence


class FileMorphsStats:
    __slots__ = (
        "unique_morphs",
        "unique_known",
        "unique_learning",
        "unique_unknowns",
        "total_morphs",
        "total_known",
        "total_learning",
        "total_unknowns",
    )

    def __init__(
        self,
    ) -> None:
        self.unique_known: set[Morpheme] = set()
        self.unique_learning: set[Morpheme] = set()
        self.unique_unknowns: set[Morpheme] = set()

        self.total_known: int = 0
        self.total_learning: int = 0
        self.total_unknowns: int = 0

    def __add__(self, other: FileMorphsStats) -> FileMorphsStats:
        self.unique_known.update(other.unique_known)
        self.unique_learning.update(other.unique_learning)
        self.unique_unknowns.update(other.unique_unknowns)

        self.total_known += other.total_known
        self.total_learning += other.total_learning
        self.total_unknowns += other.total_unknowns

        return self


def get_morph_stats_from_file(
    am_config: AnkiMorphsConfig,
    am_db: AnkiMorphsDB,
    file_morphs: dict[str, MorphOccurrence],
) -> FileMorphsStats:
    file_morphs_stats = FileMorphsStats()
    highest_learning_interval: int | None

    if am_config.evaluate_morph_inflection:
        for morph_occurrence_object in file_morphs.values():
            morph = morph_occurrence_object.morph
            occurrence = morph_occurrence_object.occurrence
            highest_learning_interval = am_db.get_highest_inflection_learning_interval(
                morph
            )

            _update_file_morphs_stats(
                file_morphs_stats=file_morphs_stats,
                interval_for_known=am_config.interval_for_known_morphs,
                morph=morph,
                occurrence=occurrence,
                highest_learning_interval=highest_learning_interval,
            )
    else:
        for morph_occurrence_object in file_morphs.values():
            morph = morph_occurrence_object.morph
            occurrence = morph_occurrence_object.occurrence
            highest_learning_interval = am_db.get_highest_lemma_learning_interval(morph)

            _update_file_morphs_stats(
                file_morphs_stats=file_morphs_stats,
                interval_for_known=am_config.interval_for_known_morphs,
                morph=morph,
                occurrence=occurrence,
                highest_learning_interval=highest_learning_interval,
            )

    return file_morphs_stats


def _update_file_morphs_stats(
    file_morphs_stats: FileMorphsStats,
    interval_for_known: int,
    morph: Morpheme,
    occurrence: int,
    highest_learning_interval: int | None,
) -> None:
    if highest_learning_interval is None:
        file_morphs_stats.total_unknowns += occurrence
        file_morphs_stats.unique_unknowns.add(morph)
        return

    if highest_learning_interval == 0:
        file_morphs_stats.total_unknowns += occurrence
        file_morphs_stats.unique_unknowns.add(morph)
    elif highest_learning_interval < interval_for_known:
        file_morphs_stats.total_learning += occurrence
        file_morphs_stats.unique_learning.add(morph)
    else:
        file_morphs_stats.total_known += occurrence
        file_morphs_stats.unique_known.add(morph)
