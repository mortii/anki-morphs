from __future__ import annotations

import csv
from functools import partial
from pathlib import Path

from aqt import mw

from .. import ankimorphs_globals as am_globals
from ..ankimorphs_db import AnkiMorphsDB
from ..morpheme import MorphOccurrence
from ..morphemizers.morphemizer import Morphemizer
from ..ui.generators_window_ui import Ui_GeneratorsWindow
from . import generators_utils
from .generators_output_dialog import OutputOptions


def background_generate_study_plan(
    selected_output_options: OutputOptions,
    ui: Ui_GeneratorsWindow,
    morphemizers: list[Morphemizer],
    input_dir_root: Path,
    input_files: list[Path],
) -> None:
    assert mw is not None

    mw.progress.start(label="Generating study plan")

    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]] = (
        generators_utils.generate_morph_occurrences_by_file(
            ui=ui,
            morphemizers=morphemizers,
            input_dir_root=input_dir_root,
            input_files=input_files,
            sorted_by_table=True,
        )
    )

    mw.taskman.run_on_main(
        partial(
            mw.progress.update,
            label="Sorting morphs",
        )
    )

    write_out_study_plan(
        input_dir_root=input_dir_root,
        selected_output_options=selected_output_options,
        morph_occurrences_by_file=morph_occurrences_by_file,
    )


def write_out_study_plan(  # pylint:disable=too-many-locals
    input_dir_root: Path,
    selected_output_options: OutputOptions,
    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]],
) -> None:
    # Note: the study plan cannot have a full-format where one can switch
    # between evaluating lemmas and inflections like you can with regular
    # priority files, because the same lemma can span multiple files,
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

        for file_path, file_morph_occurrences in morph_occurrences_by_file.items():
            # we always include the lemmas
            sorted_lemma_occurrences: dict[str, MorphOccurrence] = (
                generators_utils.get_sorted_lemma_occurrence_dict(
                    file_morph_occurrences
                )
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

                morph_key_cutoff = generators_utils.get_morph_key_cutoff(
                    selected_output_options=selected_output_options,
                    sorted_morph_occurrences=sorted_inflection_occurrences,
                )
                sorted_dict_to_use = sorted_inflection_occurrences

            else:
                morph_key_cutoff = generators_utils.get_morph_key_cutoff(
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
