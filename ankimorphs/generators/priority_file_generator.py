from __future__ import annotations

import csv
from functools import partial
from pathlib import Path

from aqt import mw

from .. import ankimorphs_globals as am_globals
from ..morpheme import MorphOccurrence
from ..morphemizers.morphemizer import Morphemizer
from ..ui.generators_window_ui import Ui_GeneratorsWindow
from . import generators_utils
from .generators_output_dialog import OutputOptions


def background_generate_priority_file(
    selected_output_options: OutputOptions,
    ui: Ui_GeneratorsWindow,
    morphemizers: list[Morphemizer],
    input_dir_root: Path,
    input_files: list[Path],
) -> None:
    assert mw is not None
    assert mw.progress is not None

    # pylint: disable=duplicate-code
    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]] = (
        generators_utils.generate_morph_occurrences_by_file(
            ui=ui,
            morphemizers=morphemizers,
            input_dir_root=input_dir_root,
            input_files=input_files,
        )
    )
    # pylint: enable=duplicate-code

    mw.taskman.run_on_main(
        partial(
            mw.progress.update,
            label="Sorting morphs",
        )
    )

    # key: lemma + inflection
    total_morph_occurrences: dict[str, MorphOccurrence] = (
        generators_utils.get_total_morph_occurrences_dict(morph_occurrences_by_file)
    )

    write_out_priority_file(selected_output_options, total_morph_occurrences)


def write_out_priority_file(
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
        generators_utils.get_sorted_lemma_occurrence_dict(total_morph_occurrences)
    )
    sorted_index_replaced_lemma_dict: dict[str, int] = {
        morph_lemma: index for index, morph_lemma in enumerate(sorted_lemma_occurrences)
    }

    if selected_output_options.selected_extra_occurrences_column:
        headers.append("Occurrence")

    morph_key_cutoff = generators_utils.get_morph_key_cutoff(
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
        generators_utils.get_sorted_lemma_occurrence_dict(total_morph_occurrences)
    )
    morph_key_cutoff = generators_utils.get_morph_key_cutoff(
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
