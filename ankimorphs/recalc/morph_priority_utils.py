from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from aqt import mw

from .. import ankimorphs_globals as am_globals
from ..ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from ..ankimorphs_db import AnkiMorphsDB
from ..exceptions import FrequencyFileMalformedException, FrequencyFileNotFoundException
from .card_score import MORPH_UNKNOWN_PENALTY


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
) -> dict[tuple[str, str], int]:
    if am_config_filter.morph_priority_selection == am_globals.COLLECTION_FREQUENCY_OPTION:  # fmt: skip
        return am_db.get_morph_priorities_from_collection(am_config)

    return _load_morph_priorities_from_file(
        frequency_file_name=am_config_filter.morph_priority_selection,
        only_lemma_priorities=am_config.evaluate_morph_lemma,
    )


def _load_morph_priorities_from_file(
    frequency_file_name: str, only_lemma_priorities: bool
) -> dict[tuple[str, str], int]:
    assert mw is not None

    print(f"mw.pm.profileFolder(): {mw.pm.profileFolder()}")
    print(
        f"am_globals.FREQUENCY_FILES_DIR_NAME): {am_globals.FREQUENCY_FILES_DIR_NAME}"
    )
    print(f"frequency_file_name: {frequency_file_name}")

    frequency_file_path = Path(
        mw.pm.profileFolder(),
        am_globals.FREQUENCY_FILES_DIR_NAME,
        frequency_file_name,
    )
    try:
        with open(frequency_file_path, mode="r+", encoding="utf-8") as csvfile:
            morph_reader = csv.reader(csvfile, delimiter=",")
            headers: list[str] | None = next(morph_reader, None)
            frequency_file: FrequencyFile = _get_file_type_and_format(
                frequency_file_path, headers
            )
            return _get_morph_priorities_from_file(
                frequency_file_path=frequency_file_path,
                morph_reader=morph_reader,
                frequency_file=frequency_file,
                only_lemma_priorities=only_lemma_priorities,
            )
    except FileNotFoundError as exc:
        raise FrequencyFileNotFoundException(str(frequency_file_path)) from exc


def _get_morph_priorities_from_file(
    frequency_file_path: Path,
    morph_reader: Any,
    frequency_file: FrequencyFile,
    only_lemma_priorities: bool,
) -> dict[tuple[str, str], int]:
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

    morph_priority_dict: dict[tuple[str, str], int] = {}

    if only_lemma_priorities:
        if frequency_file.format == FrequencyFileFormat.Full:
            if frequency_file.type == FrequencyFileType.StudyPlan:
                raise FrequencyFileMalformedException(
                    path=frequency_file_path,
                    reason="Study plans containing inflections are incompatible with the 'evaluate lemmas' option.",
                )
            _populate_priorities_with_lemmas_from_full_frequency_file(
                morph_reader=morph_reader,
                file_type_and_format=frequency_file,
                morph_priority_dict=morph_priority_dict,
            )
            return morph_priority_dict

        # this could be either a study plan or frequency file,
        # but both are handled the same
        _populate_priorities_with_lemmas_from_minimal_frequency_file(
            morph_reader=morph_reader,
            file_type_and_format=frequency_file,
            morph_priority_dict=morph_priority_dict,
        )
        return morph_priority_dict

    if frequency_file.format == FrequencyFileFormat.Minimal:
        raise FrequencyFileMalformedException(
            path=frequency_file_path,
            reason="Frequency files or study plans without inflections are incompatible with the 'evaluate inflections' option.",
        )

    if frequency_file.type == FrequencyFileType.FrequencyFile:
        _populate_priorities_with_lemmas_and_inflections_from_full_frequency_file(
            morph_reader=morph_reader,
            file_type_and_format=frequency_file,
            morph_priority_dict=morph_priority_dict,
        )
        return morph_priority_dict

    if frequency_file.type == FrequencyFileType.StudyPlan:
        _populate_priorities_with_lemmas_and_inflections_from_full_study_plan(
            morph_reader=morph_reader,
            file_type_and_format=frequency_file,
            morph_priority_dict=morph_priority_dict,
        )
        return morph_priority_dict

    # this should never be reached
    raise FrequencyFileMalformedException(
        path=frequency_file_path, reason="unsupported frequency file type or format"
    )


def _get_file_type_and_format(
    frequency_file_path: Path, headers: list[str] | None
) -> FrequencyFile:
    # Here is how to differentiate between the types and formats:
    #  - Minimal frequency file/study plan: does __not__ have the am_globals.INFLECTION_HEADER
    #  - Full frequency file: has the am_globals.INFLECTION_PRIORITY_HEADER
    #  - Full study plan: does __not__ have the am_globals.INFLECTION_PRIORITY_HEADER

    if headers is None or len(headers) == 0:
        raise FrequencyFileMalformedException(
            path=str(frequency_file_path),
            reason="Frequency file does not have headers.",
        )

    if am_globals.LEMMA_HEADER not in headers:
        reason = f"Frequency file is missing the '{am_globals.LEMMA_HEADER}' header"
        raise FrequencyFileMalformedException(
            path=str(frequency_file_path),
            reason=reason,
        )

    lemma_header_index: int = headers.index(am_globals.LEMMA_HEADER)

    if am_globals.INFLECTION_HEADER not in headers:
        # this is either a minimal frequency file or a minimal study plan,
        # but we don't have to differentiate the file types since
        # minimal format files are handled in the same way
        return FrequencyFile(
            file_type=FrequencyFileType.FrequencyFile,  # arbitrary choice
            file_format=FrequencyFileFormat.Minimal,
            lemma_header_index=lemma_header_index,
        )

    inflection_header_index: int = headers.index(am_globals.INFLECTION_HEADER)

    if am_globals.LEMMA_PRIORITY_HEADER in headers:
        # full format frequency file
        lemma_priority_header_index: int = headers.index(
            am_globals.LEMMA_PRIORITY_HEADER
        )
        try:
            # this should always exist at this point
            inflection_priority_header_index: int = headers.index(
                am_globals.INFLECTION_PRIORITY_HEADER
            )
        except ValueError as exc:
            reason = f"Frequency file is missing the '{am_globals.INFLECTION_PRIORITY_HEADER}' header"
            raise FrequencyFileMalformedException(
                path=str(frequency_file_path),
                reason=reason,
            ) from exc

        return FrequencyFile(
            file_type=FrequencyFileType.FrequencyFile,
            file_format=FrequencyFileFormat.Full,
            lemma_header_index=lemma_header_index,
            inflection_header_index=inflection_header_index,
            lemma_priority_header_index=lemma_priority_header_index,
            inflection_priority_header_index=inflection_priority_header_index,
        )

    # here we should be left with a full format study plan
    return FrequencyFile(
        file_type=FrequencyFileType.StudyPlan,
        lemma_header_index=lemma_header_index,
        file_format=FrequencyFileFormat.Full,
        inflection_header_index=inflection_header_index,
    )


def _populate_priorities_with_lemmas_and_inflections_from_full_frequency_file(
    morph_reader: Any,
    file_type_and_format: FrequencyFile,
    morph_priority_dict: dict[tuple[str, str], int],
) -> None:
    for index, row in enumerate(morph_reader):
        if index > MORPH_UNKNOWN_PENALTY:
            # rows after this will be ignored by the scoring algorithm
            break
        lemma = row[file_type_and_format.lemma_header_index]
        inflection = row[file_type_and_format.inflection_header_index]
        key = (lemma, inflection)
        morph_priority_dict[key] = int(
            row[file_type_and_format.inflection_priority_header_index]
        )


def _populate_priorities_with_lemmas_and_inflections_from_full_study_plan(
    morph_reader: Any,
    file_type_and_format: FrequencyFile,
    morph_priority_dict: dict[tuple[str, str], int],
) -> None:
    for index, row in enumerate(morph_reader):
        if index > MORPH_UNKNOWN_PENALTY:
            # rows after this will be ignored by the scoring algorithm
            break
        lemma = row[file_type_and_format.lemma_header_index]
        inflection = row[file_type_and_format.inflection_header_index]
        key = (lemma, inflection)
        morph_priority_dict[key] = index


def _populate_priorities_with_lemmas_from_full_frequency_file(
    morph_reader: Any,
    file_type_and_format: FrequencyFile,
    morph_priority_dict: dict[tuple[str, str], int],
) -> None:
    for index, row in enumerate(morph_reader):
        if index > MORPH_UNKNOWN_PENALTY:
            # rows after this will be ignored by the scoring algorithm
            break
        lemma = row[file_type_and_format.lemma_header_index]
        key = (lemma, lemma)
        morph_priority_dict[key] = int(
            row[file_type_and_format.lemma_priority_header_index]
        )


def _populate_priorities_with_lemmas_from_minimal_frequency_file(
    morph_reader: Any,
    file_type_and_format: FrequencyFile,
    morph_priority_dict: dict[tuple[str, str], int],
) -> None:
    for index, row in enumerate(morph_reader):
        if index > MORPH_UNKNOWN_PENALTY:
            # rows after this will be ignored by the scoring algorithm
            break
        lemma = row[file_type_and_format.lemma_header_index]
        key = (lemma, lemma)
        morph_priority_dict[key] = index
