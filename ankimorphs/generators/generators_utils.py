from __future__ import annotations

import copy
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Any, Callable
from unittest.mock import Mock

from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
)

from .. import text_preprocessing
from ..ankimorphs_config import AnkiMorphsConfig
from ..ankimorphs_db import AnkiMorphsDB
from ..exceptions import CancelledOperationException, UnicodeException
from ..morpheme import Morpheme, MorphOccurrence
from ..morphemizers import spacy_wrapper
from ..morphemizers.morphemizer import Morphemizer
from ..morphemizers.spacy_morphemizer import SpacyMorphemizer
from ..ui.generators_window_ui import Ui_GeneratorsWindow
from .generators_output_dialog import OutputOptions
from .text_extractors import (
    extract_ass_text,
    extract_basic_text,
    extract_epub_text,
    extract_html_text,
    extract_srt_text,
    extract_vtt_text,
)

extractors: dict[str, Callable[[Path], list[str]]] = {
    ".ass": extract_ass_text,
    ".epub": extract_epub_text,
    ".html": extract_html_text,
    ".srt": extract_srt_text,
    ".vtt": extract_vtt_text,
    ".md": extract_basic_text,
    ".txt": extract_basic_text,
}


class Column(Enum):
    FILE_NAME = 0
    UNIQUE_MORPHS = 1
    UNIQUE_KNOWN = 2
    UNIQUE_LEARNING = 3
    UNIQUE_UNKNOWNS = 4
    TOTAL_MORPHS = 5
    TOTAL_KNOWN = 6
    TOTAL_LEARNING = 7
    TOTAL_UNKNOWNS = 8
    NUMBER_OF_COLUMNS = len(
        [
            FILE_NAME,
            UNIQUE_MORPHS,
            UNIQUE_KNOWN,
            UNIQUE_LEARNING,
            UNIQUE_UNKNOWNS,
            TOTAL_MORPHS,
            TOTAL_KNOWN,
            TOTAL_LEARNING,
            TOTAL_UNKNOWNS,
        ]
    )


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


class PreprocessOptions:  # pylint:disable=too-many-instance-attributes
    def __init__(self, ui: Ui_GeneratorsWindow):
        self.filter_square_brackets: bool = ui.squareBracketsCheckBox.isChecked()
        self.filter_round_brackets: bool = ui.roundBracketsCheckBox.isChecked()
        self.filter_slim_round_brackets: bool = ui.slimRoundBracketsCheckBox.isChecked()
        self.filter_numbers: bool = ui.numbersCheckBox.isChecked()
        self.filter_morphemizer_names: bool = ui.namesMorphemizerCheckBox.isChecked()
        self.filter_names_from_file: bool = ui.namesFileCheckBox.isChecked()
        self.filter_custom_chars: bool = ui.customCharactersCheckBox.isChecked()
        self.custom_chars_to_ignore: str = ui.customCharactersLineEdit.text()

    def to_mock_am_config(self) -> AnkiMorphsConfig:
        return Mock(
            spec=AnkiMorphsConfig,
            preprocess_ignore_bracket_contents=self.filter_square_brackets,
            preprocess_ignore_round_bracket_contents=self.filter_round_brackets,
            preprocess_ignore_slim_round_bracket_contents=self.filter_slim_round_brackets,
            preprocess_ignore_numbers=self.filter_numbers,
            preprocess_ignore_names_morphemizer=self.filter_morphemizer_names,
            preprocess_ignore_names_textfile=self.filter_names_from_file,
            preprocess_ignore_custom_characters=self.filter_custom_chars,
            preprocess_custom_characters_to_ignore=self.custom_chars_to_ignore,
        )


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


def generate_morph_occurrences_by_file(
    ui: Ui_GeneratorsWindow,
    morphemizers: list[Morphemizer],
    input_dir_root: Path,
    input_files: list[Path],
    sorted_by_table: int = False,
) -> dict[Path, dict[str, MorphOccurrence]]:
    """
    'sorted_by_table=True' is used for study plans where the order matters.
    """
    assert mw is not None

    _morphemizer, _nlp = _get_selected_morphemizer_and_nlp(
        morphemizers=morphemizers, morphemizer_combobox=ui.morphemizerComboBox
    )
    preprocess_options = PreprocessOptions(ui)
    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]] = {}
    sorted_input_files: list[Path]

    if sorted_by_table:
        sorted_input_files = _get_input_files_table_sorted(
            ui=ui,
            input_dir_root=input_dir_root,
        )
    else:
        sorted_input_files = input_files

    translation_table = str.maketrans("", "", preprocess_options.custom_chars_to_ignore)

    for input_file in sorted_input_files:
        if mw.progress.want_cancel():  # user clicked 'x' button
            raise CancelledOperationException

        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label=f"Processing file:<br>{input_file.relative_to(input_dir_root)}",
            )
        )

        file_morph_occurrences: dict[str, MorphOccurrence] = (
            create_file_morph_occurrences(
                preprocess_options=preprocess_options,
                file_path=input_file,
                morphemizer=_morphemizer,
                translation_table=translation_table,
            )
        )
        morph_occurrences_by_file[input_file] = file_morph_occurrences

    return morph_occurrences_by_file


def create_file_morph_occurrences(
    preprocess_options: PreprocessOptions,
    file_path: Path,
    morphemizer: Morphemizer,
    translation_table: dict[int, int | None],
) -> dict[str, MorphOccurrence]:

    raw_lines: list[str]
    filtered_lines: list[str] = []
    extension = file_path.suffix
    mock_am_config = preprocess_options.to_mock_am_config()

    if extension in extractors:
        raw_lines = extractors[extension](file_path)
    else:
        raise ValueError(f"Unsupported file format: {extension}")

    try:
        for line in raw_lines:
            # lower-case to avoid proper noun false-positives
            filtered_line = text_preprocessing.get_processed_text(
                am_config=mock_am_config,
                text=line.strip().lower(),
                translation_table=translation_table,
            )
            if filtered_line:
                filtered_lines.append(filtered_line)
    except UnicodeDecodeError as exc:
        raise UnicodeException(path=file_path) from exc

    return get_morph_occurrences(
        mock_am_config=mock_am_config,
        morphemizer=morphemizer,
        all_lines=filtered_lines,
    )


def get_morph_occurrences(
    mock_am_config: AnkiMorphsConfig,
    morphemizer: Morphemizer,
    all_lines: list[str],
) -> dict[str, MorphOccurrence]:
    morph_occurrences: dict[str, MorphOccurrence] = {}

    for processed_morphs in morphemizer.get_processed_morphs(mock_am_config, all_lines):
        for morph in processed_morphs:
            key = morph.lemma + morph.inflection
            if key in morph_occurrences:
                morph_occurrences[key].occurrence += 1
            else:
                morph_occurrences[key] = MorphOccurrence(morph)

    return morph_occurrences


def _get_selected_morphemizer_and_nlp(
    morphemizers: list[Morphemizer], morphemizer_combobox: QComboBox
) -> tuple[Morphemizer, Any]:
    _morphemizer = morphemizers[morphemizer_combobox.currentIndex()]
    assert _morphemizer is not None
    _nlp = None  # spacy.Language

    if isinstance(_morphemizer, SpacyMorphemizer):
        selected_index = morphemizer_combobox.currentIndex()
        selected_text: str = morphemizer_combobox.itemText(selected_index)
        spacy_model = selected_text.removeprefix("spaCy: ")
        _nlp = spacy_wrapper.get_nlp(spacy_model)

    return _morphemizer, _nlp


def _get_input_files_table_sorted(
    ui: Ui_GeneratorsWindow, input_dir_root: Path
) -> list[Path]:
    sorted_input_files: list[Path] = []
    current_table: QTableWidget | None = None

    if ui.tablesTabWidget.currentIndex() == 0:
        current_table = ui.numericalTableWidget
    elif ui.tablesTabWidget.currentIndex() == 1:
        current_table = ui.percentTableWidget

    assert current_table is not None

    for row in range(current_table.rowCount()):
        file_name_item: QTableWidgetItem | None = current_table.item(
            row, Column.FILE_NAME.value
        )
        assert file_name_item is not None
        file_name_text: str = file_name_item.text()

        if file_name_text == "Total":
            continue

        # the root dir is stripped when loading the files, so we have to add it back
        sorted_input_files.append(Path(input_dir_root, file_name_text))

    return sorted_input_files


def get_total_morph_occurrences_dict(
    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]],
) -> dict[str, MorphOccurrence]:
    """
    Returns total_morph_occurrences: dict[str, MorphOccurrence]
    where key: lemma + inflection
    """
    total_morph_occurrences: dict[str, MorphOccurrence] = {}

    for file_morph_dict in morph_occurrences_by_file.values():
        for key in file_morph_dict:
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
    morph_occurrence_dict_original: dict[str, MorphOccurrence],
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
