from __future__ import annotations

import copy
import csv
from pathlib import Path

from .. import ankimorphs_globals as am_globals
from ..ankimorphs_db import AnkiMorphsDB
from ..morpheme import MorphOccurrence
from .generators_output_dialog import OutputOptions


def get_total_morph_occurrences_dict(
    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]]
) -> dict[str, MorphOccurrence]:
    """
    Returns total_morph_occurrences: dict[str, MorphOccurrence]
    where key: lemma + inflection
    """
    total_morph_occurrences: dict[str, MorphOccurrence] = {}

    for file_morph_dict in morph_occurrences_by_file.values():
        for key in file_morph_dict:
            # print(f"file_morph_dict key: {key}")
            if key not in total_morph_occurrences:
                total_morph_occurrences[key] = file_morph_dict[key]
            else:
                total_morph_occurrences[key] += file_morph_dict[key]

    return total_morph_occurrences


def get_morph_key_cutoff(
    selected_output_options: OutputOptions,
    sorted_morph_occurrences: dict[str, MorphOccurrence],
) -> str | None:
    if selected_output_options.comprehension:
        morph_key_cutoff = get_comprehension_cutoff(
            sorted_morph_occurrences,
            selected_output_options.comprehension_threshold,
        )
    else:
        morph_key_cutoff = get_min_occurrence_cutoff(
            sorted_morph_occurrences,
            selected_output_options.min_occurrence_threshold,
        )

    return morph_key_cutoff


def get_comprehension_cutoff(
    sorted_morph_occurrence: dict[str, MorphOccurrence],
    comprehension_threshold: int,
) -> str | None:
    total_occurrences = 0

    for morph_occurrence in sorted_morph_occurrence.values():
        total_occurrences += morph_occurrence.occurrence

    # _comprehension_threshold is between 100 and 1
    target_percent = comprehension_threshold / 100
    target_number = target_percent * total_occurrences

    running_total = 0

    for key, morph_occurrence in sorted_morph_occurrence.items():
        running_total += morph_occurrence.occurrence
        if running_total > target_number:
            return key

    return None


def get_min_occurrence_cutoff(
    sorted_morph_occurrence: dict[str, MorphOccurrence],
    min_occurrence_threshold: int,
) -> str | None:
    for morph_key in sorted_morph_occurrence:
        if sorted_morph_occurrence[morph_key].occurrence < min_occurrence_threshold:
            return morph_key
    return None


def get_sorted_lemma_occurrence_dict(
    morph_occurrence_dict_original: dict[str, MorphOccurrence]
) -> dict[str, MorphOccurrence]:
    """
    This creates a new dict with keys that only consist of the lemma, and
    sums all the inflections into the respective lemma occurrences.
    """

    # we clone the original dict to prevent mutation problems
    morph_occurrence_dict = copy.deepcopy(morph_occurrence_dict_original)
    lemma_occurrence: dict[str, MorphOccurrence] = {}

    for morph_occurrence in morph_occurrence_dict.values():
        lemma: str = morph_occurrence.morph.lemma
        if lemma in lemma_occurrence:
            lemma_occurrence[lemma] += morph_occurrence
        else:
            lemma_occurrence[lemma] = morph_occurrence

    sorted_lemma_frequency: dict[str, MorphOccurrence] = dict(
        sorted(
            lemma_occurrence.items(),
            key=lambda item: item[1].occurrence,
            reverse=True,
        )
    )

    return sorted_lemma_frequency


def write_out_frequency_file(
    selected_output_options: OutputOptions,
    total_morph_occurrences: dict[str, MorphOccurrence],
) -> None:

    output_file: Path = selected_output_options.output_path

    # make sure the parent dirs exist before creating the file
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    if selected_output_options.store_only_lemma:
        lemma_only_writer(
            selected_output_options=selected_output_options,
            total_morph_occurrences=total_morph_occurrences,
        )
    else:
        lemma_and_inflection_writer(
            selected_output_options=selected_output_options,
            total_morph_occurrences=total_morph_occurrences,
        )


def lemma_and_inflection_writer(  # pylint:disable=too-many-locals
    selected_output_options: OutputOptions,
    total_morph_occurrences: dict[str, MorphOccurrence],
) -> None:
    output_file: Path = selected_output_options.output_path

    headers = [
        am_globals.LEMMA_HEADER,
        am_globals.INFLECTION_HEADER,
        am_globals.LEMMA_PRIORITY_HEADER,
        am_globals.INFLECTION_PRIORITY_HEADER,
    ]

    sorted_inflection_occurrences = dict(
        sorted(
            total_morph_occurrences.items(),
            key=lambda item: item[1].occurrence,
            reverse=True,
        )
    )

    sorted_lemma_occurrences: dict[str, MorphOccurrence] = (
        get_sorted_lemma_occurrence_dict(total_morph_occurrences)
    )
    sorted_index_replaced_lemma_dict: dict[str, int] = {
        morph_lemma: index for index, morph_lemma in enumerate(sorted_lemma_occurrences)
    }

    if selected_output_options.selected_extra_occurrences_column:
        headers.append("Occurrence")

    morph_key_cutoff = get_morph_key_cutoff(
        selected_output_options, sorted_inflection_occurrences
    )

    with open(output_file, mode="w+", encoding="utf-8", newline="") as csvfile:
        morph_writer = csv.writer(csvfile)
        morph_writer.writerow(headers)

        for index, (key, morph_occurrence) in enumerate(
            sorted_inflection_occurrences.items()
        ):
            if key == morph_key_cutoff:
                break

            morph = morph_occurrence.morph
            occurrence = morph_occurrence.occurrence
            row_values: list[str | int] = [morph.lemma]

            if selected_output_options.store_lemma_and_inflection:
                row_values.append(morph.inflection)
                row_values.append(sorted_index_replaced_lemma_dict[morph.lemma])
                row_values.append(index)

            if selected_output_options.selected_extra_occurrences_column:
                row_values.append(occurrence)

            morph_writer.writerow(row_values)


def lemma_only_writer(
    selected_output_options: OutputOptions,
    total_morph_occurrences: dict[str, MorphOccurrence],
) -> None:
    output_file: Path = selected_output_options.output_path
    headers = [am_globals.LEMMA_HEADER]

    if selected_output_options.selected_extra_occurrences_column:
        headers.append(am_globals.OCCURRENCES_HEADER)

    sorted_lemma_occurrences: dict[str, MorphOccurrence] = (
        get_sorted_lemma_occurrence_dict(total_morph_occurrences)
    )
    morph_key_cutoff = get_morph_key_cutoff(
        selected_output_options, sorted_lemma_occurrences
    )

    with open(output_file, mode="w+", encoding="utf-8", newline="") as csvfile:
        morph_writer = csv.writer(csvfile)
        morph_writer.writerow(headers)

        for key, morph_occurrence in sorted_lemma_occurrences.items():
            if key == morph_key_cutoff:
                break

            morph = morph_occurrence.morph
            occurrence = morph_occurrence.occurrence
            row_values: list[str | int] = [morph.lemma]

            if selected_output_options.selected_extra_occurrences_column:
                row_values.append(occurrence)

            morph_writer.writerow(row_values)


def write_out_study_plan(  # pylint:disable=too-many-locals
    input_dir_root: Path,
    selected_output_options: OutputOptions,
    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]],
) -> None:
    # Note: the study plan cannot have a full-format where one can switch
    # between evaluating lemmas and inflections like you can with regular
    # frequency files, because the same lemma can span multiple files,
    # even though the inflections do not, so the priorities do not align
    # cleanly.

    am_db = AnkiMorphsDB()
    output_file = selected_output_options.output_path

    # make sure the parent dirs exist before creating the file
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    morph_in_study_plan: dict[str, None] = {}  # we only care about lookup not the value
    learning_status_of_morph: dict[str, str]

    if selected_output_options.store_lemma_and_inflection:
        learning_status_of_morph = am_db.get_morph_inflections_learning_statuses()
    else:
        learning_status_of_morph = am_db.get_morph_lemmas_learning_statuses()

    with open(output_file, mode="w+", encoding="utf-8", newline="") as csvfile:
        morph_writer = csv.writer(csvfile)
        headers = _get_study_plan_headers(selected_output_options)
        morph_writer.writerow(headers)

        print(f"headers: {headers}")

        for file_path, file_morph_occurrences in morph_occurrences_by_file.items():
            # we always include the lemmas
            sorted_lemma_occurrences: dict[str, MorphOccurrence] = (
                get_sorted_lemma_occurrence_dict(file_morph_occurrences)
            )
            sorted_dict_to_use: dict[str, MorphOccurrence]
            morph_key_cutoff: str | None

            if selected_output_options.store_lemma_and_inflection:
                sorted_inflection_occurrences = dict(
                    sorted(
                        file_morph_occurrences.items(),
                        key=lambda item: item[1].occurrence,
                        reverse=True,
                    )
                )

                morph_key_cutoff = get_morph_key_cutoff(
                    selected_output_options=selected_output_options,
                    sorted_morph_occurrences=sorted_inflection_occurrences,
                )
                sorted_dict_to_use = sorted_inflection_occurrences

            else:
                morph_key_cutoff = get_morph_key_cutoff(
                    selected_output_options=selected_output_options,
                    sorted_morph_occurrences=sorted_lemma_occurrences,
                )
                sorted_dict_to_use = sorted_lemma_occurrences

            for key, morph_occurrence in sorted_dict_to_use.items():
                if key == morph_key_cutoff:
                    break

                if key in morph_in_study_plan:
                    continue

                row = _get_study_plan_row(
                    selected_output_options=selected_output_options,
                    input_dir_root=input_dir_root,
                    file_path=file_path,
                    learning_status_of_morph=learning_status_of_morph,
                    morph_key=key,
                    morph_occurrence=morph_occurrence,
                )

                morph_writer.writerow(row)
                morph_in_study_plan[key] = None  # inserts the key


def _get_study_plan_headers(selected_output_options: OutputOptions) -> list[str]:
    """
    A full headers list looks like this:
        headers = [
            am_globals.LEMMA_HEADER,
            am_globals.INFLECTION_HEADER,
            "Learning-status",
            "Occurrence",
            "File",
        ]

    A minimal headers list looks like this:
        headers = [
            am_globals.LEMMA_HEADER,
            "Learning-status",
            "File",
        ]
    """
    headers = [
        am_globals.LEMMA_HEADER,
    ]
    if selected_output_options.store_lemma_and_inflection:
        print(
            f"selected_output_options.store_lemma_and_inflection: {selected_output_options.store_lemma_and_inflection}"
        )
        headers.append(am_globals.INFLECTION_HEADER)
    headers.append("Learning-status")
    if selected_output_options.selected_extra_occurrences_column:
        headers.append("Occurrence")
    headers.append("File")
    return headers


def _get_study_plan_row(  # pylint:disable=too-many-arguments
    selected_output_options: OutputOptions,
    input_dir_root: Path,
    file_path: Path,
    learning_status_of_morph: dict[str, str],
    morph_key: str,
    morph_occurrence: MorphOccurrence,
) -> list[str]:
    learning_status: str

    if morph_key not in learning_status_of_morph:
        learning_status = "unknown"
    else:
        learning_status = learning_status_of_morph[morph_key]

    row = [morph_occurrence.morph.lemma]

    if selected_output_options.store_lemma_and_inflection:
        row.append(morph_occurrence.morph.inflection)

    row.append(learning_status)

    if selected_output_options.selected_extra_occurrences_column:
        row.append(str(morph_occurrence.occurrence))

    row.append(str(file_path.relative_to(input_dir_root)))
    return row
