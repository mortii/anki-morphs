from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from aqt import mw

from .. import ankimorphs_globals as am_globals
from ..ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from ..ankimorphs_db import AnkiMorphsDB
from ..exceptions import FrequencyFileMalformedException, FrequencyFileNotFoundException

# todo: import this?
_DEFAULT_SCORE: int = 2_047_483_647


def _get_morph_priority(
    am_db: AnkiMorphsDB,
    am_config: AnkiMorphsConfig,
    am_config_filter: AnkiMorphsConfigFilter,
) -> dict[str, int]:

    if (
        am_config_filter.morph_priority_selection
        == am_globals.COLLECTION_FREQUENCY_OPTION
    ):
        morph_priorities = am_db.get_morph_collection_priorities(am_config)
    else:
        morph_priorities = _get_morph_frequency_file_priority(
            frequency_file_name=am_config_filter.morph_priority_selection,
            only_lemma_priorities=am_config.evaluate_morph_lemma,
        )

    return morph_priorities


def _get_morph_frequency_file_priority(
    frequency_file_name: str, only_lemma_priorities: bool
) -> dict[str, int]:
    # Full-format frequency files were designed to allow switching between evaluating
    # morphs based on their lemma or their inflections. However, this switching
    # is not possible with full-format study plans, so they must be treated differently.
    #
    # Scenarios to handle:
    #  - frequency file minimal (only lemma) format
    #    - evaluating lemma -> ok
    #    - evaluating inflection -> raise exception
    #  - frequency file full (lemma and inflection) format
    #    - evaluating lemma -> ok
    #    - evaluating inflection -> ok
    #  - study plan minimal (only lemma) format
    #    - evaluating lemma -> ok
    #    - evaluating inflection -> raise exception
    #  - study plan full (lemma and inflection) format
    #    - evaluating lemma -> raise exception
    #    - evaluating inflection -> ok
    #
    # Here is how to differentiate between them:
    #  - Minimal frequency file/study plan: does __not__ have the am_globals.INFLECTION_HEADER
    #  - Full frequency file: has the am_globals.INFLECTION_PRIORITY_HEADER
    #  - Full study plan: does __not__ have the am_globals.INFLECTION_PRIORITY_HEADER

    assert mw is not None

    print(f"mw.pm.profileFolder(): {mw.pm.profileFolder()}")
    print(
        f"am_globals.FREQUENCY_FILES_DIR_NAME): {am_globals.FREQUENCY_FILES_DIR_NAME}"
    )
    print(f"frequency_file_name: {frequency_file_name}")

    morph_priority: dict[str, int] = {}
    frequency_file_path = Path(
        mw.pm.profileFolder(),
        am_globals.FREQUENCY_FILES_DIR_NAME,
        frequency_file_name,
    )
    try:
        with open(frequency_file_path, mode="r+", encoding="utf-8") as csvfile:
            morph_reader = csv.reader(csvfile, delimiter=",")
            headers: list[str] | None = next(morph_reader, None)

            if headers is None:
                raise FrequencyFileMalformedException(
                    path=str(frequency_file_path),
                    reason="Frequency file does not have headers.",
                )

            # lemma_column = headers.index(am_globals.LEMMA_HEADER)
            if am_globals.LEMMA_HEADER not in headers:
                _reason = (
                    f"Frequency file is missing the '{am_globals.LEMMA_HEADER}' header"
                )
                raise FrequencyFileMalformedException(
                    path=str(frequency_file_path),
                    reason=_reason,
                )

            if only_lemma_priorities:
                # Here we have two options, a frequency file that either has
                # a single column of only lemmas, or a full frequency file that
                # contains a "Lemma-Priority" column
                if am_globals.LEMMA_PRIORITY_HEADER in headers:
                    lemma_priority_column = headers.index(
                        am_globals.LEMMA_PRIORITY_HEADER
                    )
                    morph_priority = _get_lemma_priority_from_full_frequency_file(
                        morph_reader=morph_reader,
                        lemma_priority_column=lemma_priority_column,
                    )
                else:
                    morph_priority = get_lemma_priority_from_minimal_frequency_file(
                        morph_reader=morph_reader,
                    )
            else:
                # here we always have an inflection column that contains priorities
                if am_globals.INFLECTION_PRIORITY_HEADER not in headers:
                    _reason = f"Frequency file is missing the '{am_globals.INFLECTION_PRIORITY_HEADER}' header"
                    raise FrequencyFileMalformedException(
                        path=str(frequency_file_path),
                        reason=_reason,
                    )

                inflection_priority_column = headers.index(
                    am_globals.INFLECTION_PRIORITY_HEADER
                )

                morph_priority = _get_inflection_priority_full_frequency_file(
                    morph_reader=morph_reader,
                    inflection_priority_column=inflection_priority_column,
                )

    except FileNotFoundError as error:
        raise FrequencyFileNotFoundException(str(frequency_file_path)) from error

    return morph_priority


def _get_inflection_priority_full_frequency_file(
    morph_reader: Any, inflection_priority_column: int
) -> dict[str, int]:
    morph_priority: dict[str, int] = {}

    # print(f"inflection_priority_column: {inflection_priority_column}")

    for index, row in enumerate(morph_reader):
        if index > _DEFAULT_SCORE:  # todo, change this
            # the scoring algorithm ignores values > 50K
            # so any rows after this will be ignored anyway
            break
        # print(f"row: {row}")
        # print(f"row[inflection_priority_column]: {row[inflection_priority_column]}")
        key = row[0] + row[1]  # todo: use dynamic column, dont assume 0
        morph_priority[key] = int(row[inflection_priority_column])
        # print(f"key: {key}, prio: {morph_priority[key]}")

    return morph_priority


def _get_lemma_priority_from_full_frequency_file(
    morph_reader: Any, lemma_priority_column: int
) -> dict[str, int]:
    morph_priority: dict[str, int] = {}

    # print(f"inflection_priority_column: {inflection_priority_column}")

    for index, row in enumerate(morph_reader):
        if index > _DEFAULT_SCORE:  # todo, change this
            # the scoring algorithm ignores values > 50K
            # so any rows after this will be ignored anyway
            break
        # print(f"row: {row}")
        # print(f"row[inflection_priority_column]: {row[inflection_priority_column]}")
        key = row[0] + row[0]
        morph_priority[key] = int(row[lemma_priority_column])
        # print(f"key: {key}, prio: {morph_priority[key]}")

    return morph_priority


def get_lemma_priority_from_minimal_frequency_file(
    morph_reader: Any,
) -> dict[str, int]:
    morph_priority: dict[str, int] = {}

    # print(f"inflection_priority_column: {inflection_priority_column}")

    for index, row in enumerate(morph_reader):
        if index > _DEFAULT_SCORE:  # todo, change this
            # the scoring algorithm ignores values > 50K
            # so any rows after this will be ignored anyway
            break
        # print(f"row: {row}")
        # print(f"row[inflection_priority_column]: {row[inflection_priority_column]}")
        key = row[0] + row[0]
        morph_priority[key] = index
        # print(f"key: {key}, prio: {morph_priority[key]}")

    return morph_priority
