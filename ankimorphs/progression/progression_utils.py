from __future__ import annotations

from ..ankimorphs_db import AnkiMorphsDB
from ..exceptions import InvalidBinsException


class Bins:
    """Bins, used for morph priority."""

    def __init__(
        self, min_index: int, max_index: int, bin_size: int, is_cumulative: bool
    ) -> None:
        self.min_index = min_index
        self.max_index = max_index
        self.bin_size = bin_size
        self.is_cumulative = is_cumulative

        if min_index >= max_index:
            raise InvalidBinsException(min_index, max_index)

        self.indexes = []
        working_min_index = min_index
        while working_min_index + bin_size - 1 < max_index:
            if is_cumulative:
                self.indexes.append((min_index, working_min_index + bin_size - 1))
            else:
                self.indexes.append(
                    (working_min_index, working_min_index + bin_size - 1)
                )

            working_min_index += bin_size

        if is_cumulative:
            self.indexes.append((min_index, max_index))
        else:
            self.indexes.append((working_min_index, max_index))


class ProgressReport:
    """Stores lists of know, learning, unknown, and missing morphs."""

    def __init__(self, min_priority: int, max_priority: int) -> None:

        self.min_priority = min_priority
        self.max_priority = max_priority

        # Morphs are represented as (lemma,inflection/lemma) keys,
        # identical to morph_priorities
        self.unique_known: set[tuple[str, str]] = set()
        self.unique_learning: set[tuple[str, str]] = set()
        self.unique_unknowns: set[tuple[str, str]] = set()
        self.unique_missing: set[tuple[str, str]] = set()

    def get_total_known(self) -> int:
        return len(self.unique_known)

    def get_total_learning(self) -> int:
        return len(self.unique_learning)

    def get_total_unknowns(self) -> int:
        return len(self.unique_unknowns)

    def get_total_missing(self) -> int:
        return len(self.unique_missing)

    def get_total_morphs(self) -> int:
        return (
            self.get_total_known()
            + self.get_total_learning()
            + self.get_total_unknowns()
            + self.get_total_missing()
        )


def _update_progress_report(
    progress_report: ProgressReport, morph: tuple[str, str], morph_status: str
) -> None:
    """Adds morph and status information to a progress report."""
    assert morph_status in ["known", "learning", "unknown", "missing"]
    if morph_status == "known":
        progress_report.unique_known.add(morph)
    elif morph_status == "learning":
        progress_report.unique_learning.add(morph)
    elif morph_status == "unknown":
        progress_report.unique_unknowns.add(morph)
    else:  # morph_status == "missing":
        progress_report.unique_missing.add(morph)


def get_progress_reports(
    am_db: AnkiMorphsDB,
    bins: Bins,
    morph_priorities: dict[tuple[str, str], int],
    only_lemma_priorities: bool,
) -> list[ProgressReport]:
    reports = []

    # This function could be cleaner if the learning status dictionaries were
    # keyed like the morph_priority dictionaries.
    morph_learning_statuses: dict[str, str]
    if only_lemma_priorities:
        morph_learning_statuses = am_db.get_morph_lemmas_learning_statuses()
    else:
        morph_learning_statuses = am_db.get_morph_inflections_learning_statuses()

    for min_priority, max_priority in bins.indexes:

        report = ProgressReport(min_priority, max_priority)
        morph_priorities_subset = _get_morph_priorities_subset(
            morph_priorities, min_priority, max_priority
        )

        for morph in morph_priorities_subset:

            learning_status_key = morph[0] + morph[1]
            if only_lemma_priorities:
                learning_status_key = morph[0]  # expect morph=(lemma,lemma)

            morph_status = "missing"
            if (
                learning_status_key in morph_learning_statuses
            ):  # if the morph is in the database
                morph_status = morph_learning_statuses[learning_status_key]
            _update_progress_report(report, morph, morph_status)

        reports.append(report)

    return reports


def get_priority_ordered_morph_statuses(
    am_db: AnkiMorphsDB,
    bins: Bins,
    morph_priorities: dict[tuple[str, str], int],
    only_lemma_priorities: bool,
) -> list[tuple[int, str, str, str]]:
    """Returns a list of (priority,lemma,inflection,status) tuples in order of
    increasing priority"""
    # (lemma, inflection, and status) in increasing priority order
    morph_statuses: list[tuple[int, str, str, str]] = []

    morph_priorities = _get_morph_priorities_subset(
        morph_priorities, bins.min_index, bins.max_index
    )

    sorted_morph_priorities = dict(
        sorted(
            morph_priorities.items(),
            key=lambda item: item[1],
        )
    )

    morph_learning_statuses: dict[str, str]
    if only_lemma_priorities:
        morph_learning_statuses = am_db.get_morph_lemmas_learning_statuses()
    else:
        morph_learning_statuses = am_db.get_morph_inflections_learning_statuses()

    for morph in sorted_morph_priorities:
        priority = sorted_morph_priorities[morph]
        learning_status_key = morph[0] + morph[1]
        if only_lemma_priorities:
            learning_status_key = morph[0]  # expect morph=(lemma,lemma)

        morph_status = "missing"
        if (
            learning_status_key in morph_learning_statuses
        ):  # if the morph is in the database
            morph_status = morph_learning_statuses[learning_status_key]

        if only_lemma_priorities:
            morph_statuses.append((priority, morph[0], "-", morph_status))
        else:
            morph_statuses.append((priority, morph[0], morph[1], morph_status))

    return morph_statuses


def _get_morph_priorities_subset(
    morph_priorities: dict[tuple[str, str], int], min_priority: int, max_priority: int
) -> dict[tuple[str, str], int]:
    """Returns morph priorities within a priority range."""

    def is_in_range(item: tuple[tuple[str, str], int]) -> bool:
        _, priority = item
        return min_priority <= priority <= max_priority

    return dict(filter(is_in_range, morph_priorities.items()))
