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


class FrequencyFileType:
    FrequencyFile = "FrequencyFile"
    StudyPlan = "StudyPlan"


class FrequencyFileFormat:
    Minimal = "Minimal"
    Full = "Full"


class FrequencyFile:

    def __init__(  # pylint:disable=too-many-arguments
        self,
        file_type: str,
        file_format: str,
        lemma_header_index: int,
        inflection_header_index: int | None = None,
        lemma_priority_header_index: int | None = None,
        inflection_priority_header_index: int | None = None,
    ):
        self.type = file_type
        self.format = file_format
        self.lemma_header_index = lemma_header_index
        self.inflection_header_index = inflection_header_index
        self.lemma_priority_header_index = lemma_priority_header_index
        self.inflection_priority_header_index = inflection_priority_header_index


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
    # todo refactor this into something cleaner
    try:
        with open(frequency_file_path, mode="r+", encoding="utf-8") as csvfile:
            morph_reader = csv.reader(csvfile, delimiter=",")
            frequency_file = _get_file_type_and_format(morph_reader)

            if only_lemma_priorities:
                if frequency_file.format == FrequencyFileFormat.Full:
                    if frequency_file.type == FrequencyFileType.StudyPlan:
                        _reason = "using an inflection study plan to evaluate lemmas"
                        raise FrequencyFileMalformedException(
                            # path=str(frequency_file_path),
                            path="",
                            reason=_reason,
                        )
                    # FrequencyFileType.FrequencyFile
                    return _get_lemma_priority_from_full_frequency_file(
                        morph_reader=morph_reader,
                        file_type_and_format=frequency_file,
                    )

                # this can also be a minimal study plan, but it works the same
                return get_lemma_priority_from_minimal_frequency_file(
                    morph_reader=morph_reader,
                    file_type_and_format=frequency_file,
                )

            # evaluate based on inflection
            if frequency_file.type == FrequencyFileType.StudyPlan:
                if frequency_file.format == FrequencyFileFormat.Minimal:
                    _reason = "using a lemma study plan to evaluate inflections"
                    raise FrequencyFileMalformedException(
                        # path=str(frequency_file_path),
                        path="",
                        reason=_reason,
                    )
                return _get_inflection_priority_full_study_plan(
                    morph_reader=morph_reader,
                    file_type_and_format=frequency_file,
                )

            if frequency_file.type == FrequencyFileType.FrequencyFile:
                if frequency_file.format == FrequencyFileFormat.Minimal:
                    _reason = "using a lemma frequency file to evaluate inflections"
                    raise FrequencyFileMalformedException(
                        # path=str(frequency_file_path),
                        path="",
                        reason=_reason,
                    )
                print("evaluate inflection, full frequency file")
                return _get_inflection_priority_full_frequency_file(
                    morph_reader=morph_reader,
                    file_type_and_format=frequency_file,
                )

    except FileNotFoundError as error:
        raise FrequencyFileNotFoundException(str(frequency_file_path)) from error

    return morph_priority


def _get_file_type_and_format(morph_reader: Any) -> FrequencyFile:
    # Here is how to differentiate between them:
    #  - Minimal frequency file/study plan: does __not__ have the am_globals.INFLECTION_HEADER
    #  - Full frequency file: has the am_globals.INFLECTION_PRIORITY_HEADER
    #  - Full study plan: does __not__ have the am_globals.INFLECTION_PRIORITY_HEADER

    headers: list[str] | None = next(morph_reader, None)

    if headers is None:
        raise FrequencyFileMalformedException(
            # path=str(frequency_file_path),
            path="",
            reason="Frequency file does not have headers.",
        )

    print("has headers")

    if am_globals.LEMMA_HEADER not in headers:
        _reason = f"Frequency file is missing the '{am_globals.LEMMA_HEADER}' header"
        raise FrequencyFileMalformedException(
            # path=str(frequency_file_path),
            path="",
            reason=_reason,
        )
    print("has LEMMA_HEADER")

    lemma_header_index: int = headers.index(am_globals.LEMMA_HEADER)

    if am_globals.INFLECTION_HEADER not in headers:
        # the file type is irrelevant here since the minimal format versions
        # are treated the same
        return FrequencyFile(
            file_type=FrequencyFileType.FrequencyFile,
            file_format=FrequencyFileFormat.Minimal,
            lemma_header_index=lemma_header_index,
        )

    inflection_header_index: int = headers.index(am_globals.INFLECTION_HEADER)

    if am_globals.LEMMA_PRIORITY_HEADER in headers:
        # full format frequency file
        # todo, check if malformed
        lemma_priority_header_index: int = headers.index(
            am_globals.LEMMA_PRIORITY_HEADER
        )
        inflection_priority_header_index: int = headers.index(
            am_globals.INFLECTION_PRIORITY_HEADER
        )

        print("has am_globals.LEMMA_PRIORITY_HEADER in headers")
        return FrequencyFile(
            file_type=FrequencyFileType.FrequencyFile,
            file_format=FrequencyFileFormat.Full,
            lemma_header_index=lemma_header_index,
            inflection_header_index=inflection_header_index,
            lemma_priority_header_index=lemma_priority_header_index,
            inflection_priority_header_index=inflection_priority_header_index,
        )

    # here we either have a full format study plan or something malformed
    # todo, check if malformed

    return FrequencyFile(
        file_type=FrequencyFileType.StudyPlan,
        lemma_header_index=lemma_header_index,
        file_format=FrequencyFileFormat.Full,
        inflection_header_index=inflection_header_index,
    )


def _get_inflection_priority_full_frequency_file(
    morph_reader: Any, file_type_and_format: FrequencyFile
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
        lemma = row[file_type_and_format.lemma_header_index]
        inflection = row[file_type_and_format.inflection_header_index]
        key = lemma + inflection
        morph_priority[key] = int(
            row[file_type_and_format.inflection_priority_header_index]
        )
        # print(f"key: {key}, prio: {morph_priority[key]}")

    return morph_priority


def _get_inflection_priority_full_study_plan(
    morph_reader: Any, file_type_and_format: FrequencyFile
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
        lemma = row[file_type_and_format.lemma_header_index]
        inflection = row[file_type_and_format.inflection_header_index]
        key = lemma + inflection
        morph_priority[key] = index
        # print(f"key: {key}, prio: {morph_priority[key]}")

    return morph_priority


def _get_lemma_priority_from_full_frequency_file(
    morph_reader: Any, file_type_and_format: FrequencyFile
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
        lemma = row[file_type_and_format.lemma_header_index]
        key = lemma + lemma
        morph_priority[key] = int(row[file_type_and_format.lemma_priority_header_index])
        # print(f"key: {key}, prio: {morph_priority[key]}")

    return morph_priority


def get_lemma_priority_from_minimal_frequency_file(
    morph_reader: Any, file_type_and_format: FrequencyFile
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
        lemma = row[file_type_and_format.lemma_header_index]
        key = lemma + lemma
        morph_priority[key] = index
        # print(f"key: {key}, prio: {morph_priority[key]}")

    return morph_priority
