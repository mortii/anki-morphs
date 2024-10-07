from __future__ import annotations

from functools import partial
from pathlib import Path

from aqt import mw
from aqt.qt import Qt, QTableWidgetItem  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig
from ..ankimorphs_db import AnkiMorphsDB
from ..exceptions import EmptyFileSelectionException
from ..morpheme import MorphOccurrence
from ..morphemizers.morphemizer import Morphemizer
from ..table_utils import QTableWidgetIntegerItem, QTableWidgetPercentItem
from ..ui.generators_window_ui import Ui_GeneratorsWindow
from . import generators_utils
from .generators_utils import Column, FileMorphsStats


def background_generate_report(
    ui: Ui_GeneratorsWindow,
    morphemizers: list[Morphemizer],
    input_dir_root: Path,
    input_files: list[Path],
) -> None:
    assert mw is not None

    mw.progress.start(label="Generating readability report")

    if len(input_files) == 0:
        raise EmptyFileSelectionException

    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]] = (
        generators_utils.generate_morph_occurrences_by_file(
            ui=ui,
            morphemizers=morphemizers,
            input_dir_root=input_dir_root,
            input_files=input_files,
        )
    )

    mw.taskman.run_on_main(
        partial(
            mw.progress.update,
            label="Filling out report",
        )
    )

    # sorting has to be disabled before populating because bugs can occur
    ui.numericalTableWidget.setSortingEnabled(False)
    ui.percentTableWidget.setSortingEnabled(False)

    # clear previous results
    ui.numericalTableWidget.clearContents()
    ui.percentTableWidget.clearContents()

    _populate_tables_with_report(
        ui=ui,
        input_dir_root=input_dir_root,
        input_files=input_files,
        morph_occurrences_by_file=morph_occurrences_by_file,
    )

    ui.numericalTableWidget.setSortingEnabled(True)
    ui.percentTableWidget.setSortingEnabled(True)


def _populate_tables_with_report(
    ui: Ui_GeneratorsWindow,
    input_dir_root: Path,
    input_files: list[Path],
    morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]],
) -> None:
    am_config = AnkiMorphsConfig()
    am_db = AnkiMorphsDB()

    ui.numericalTableWidget.setRowCount(len(input_files) + 1)
    ui.percentTableWidget.setRowCount(len(input_files) + 1)

    # the global report will be presented as a "Total" file in the table
    global_report_morph_stats = FileMorphsStats()

    for row, input_file in enumerate(input_files):
        file_morphs = morph_occurrences_by_file[input_file]
        file_morphs_stats = generators_utils.get_morph_stats_from_file(
            am_config, am_db, file_morphs
        )
        global_report_morph_stats += file_morphs_stats

        _populate_numerical_table(
            ui=ui,
            input_dir_root=input_dir_root,
            input_file=input_file,
            row=row,
            file_morphs_stats=file_morphs_stats,
        )
        _populate_percentage_table(
            ui=ui,
            input_dir_root=input_dir_root,
            input_file=input_file,
            row=row,
            file_morphs_stats=file_morphs_stats,
        )

    _add_total_row_to_tables(
        ui=ui,
        input_dir_root=input_dir_root,
        input_files=input_files,
        global_report_morph_stats=global_report_morph_stats,
    )

    am_db.con.close()


def _populate_numerical_table(  # pylint:disable=too-many-locals
    ui: Ui_GeneratorsWindow,
    input_dir_root: Path,
    input_file: Path,
    row: int,
    file_morphs_stats: FileMorphsStats,
) -> None:
    file_name = str(input_file.relative_to(input_dir_root))

    unique_morphs: int = (
        len(file_morphs_stats.unique_known)
        + len(file_morphs_stats.unique_learning)
        + len(file_morphs_stats.unique_unknowns)
    )

    total_morphs: int = (
        file_morphs_stats.total_known
        + file_morphs_stats.total_learning
        + file_morphs_stats.total_unknowns
    )

    # fmt: off
    file_name_item = QTableWidgetItem(file_name)

    unique_morphs_item = QTableWidgetIntegerItem(unique_morphs)
    unique_known_item = QTableWidgetIntegerItem(len(file_morphs_stats.unique_known))
    unique_learning_item = QTableWidgetIntegerItem(len(file_morphs_stats.unique_learning))
    unique_unknowns_item = QTableWidgetIntegerItem(len(file_morphs_stats.unique_unknowns))

    total_morphs_item = QTableWidgetIntegerItem(total_morphs)
    total_known_item = QTableWidgetIntegerItem(file_morphs_stats.total_known)
    total_learning_item = QTableWidgetIntegerItem(file_morphs_stats.total_learning)
    total_unknown_item = QTableWidgetIntegerItem(file_morphs_stats.total_unknowns)

    unique_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    unique_known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    unique_learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    unique_unknowns_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    total_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    total_known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    total_learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    total_unknown_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    ui.numericalTableWidget.setItem(row, Column.FILE_NAME.value, file_name_item)
    ui.numericalTableWidget.setItem(row, Column.UNIQUE_MORPHS.value, unique_morphs_item)
    ui.numericalTableWidget.setItem(row, Column.UNIQUE_KNOWN.value, unique_known_item)
    ui.numericalTableWidget.setItem(row, Column.UNIQUE_LEARNING.value, unique_learning_item)
    ui.numericalTableWidget.setItem(row, Column.UNIQUE_UNKNOWNS.value, unique_unknowns_item)
    ui.numericalTableWidget.setItem(row, Column.TOTAL_MORPHS.value, total_morphs_item)
    ui.numericalTableWidget.setItem(row, Column.TOTAL_KNOWN.value, total_known_item)
    ui.numericalTableWidget.setItem(row, Column.TOTAL_LEARNING.value, total_learning_item)
    ui.numericalTableWidget.setItem(row, Column.TOTAL_UNKNOWNS.value, total_unknown_item)
    # fmt: on


def _populate_percentage_table(  # pylint:disable=too-many-locals
    ui: Ui_GeneratorsWindow,
    input_dir_root: Path,
    input_file: Path,
    row: int,
    file_morphs_stats: FileMorphsStats,
) -> None:
    file_name = str(input_file.relative_to(input_dir_root))

    unique_morphs: int = (
        len(file_morphs_stats.unique_known)
        + len(file_morphs_stats.unique_learning)
        + len(file_morphs_stats.unique_unknowns)
    )

    total_morphs: int = (
        file_morphs_stats.total_known
        + file_morphs_stats.total_learning
        + file_morphs_stats.total_unknowns
    )

    unique_known_percent: float = 0
    unique_learning_percent: float = 0
    unique_unknown_percent: float = 0

    total_known_percent: float = 0
    total_learning_percent: float = 0
    total_unknown_percent: float = 0

    if unique_morphs != 0:
        unique_known_percent = (
            len(file_morphs_stats.unique_known) / unique_morphs
        ) * 100

        unique_learning_percent = (
            len(file_morphs_stats.unique_learning) / unique_morphs
        ) * 100

        unique_unknown_percent = (
            len(file_morphs_stats.unique_unknowns) / unique_morphs
        ) * 100

    if total_morphs != 0:
        total_known_percent = (file_morphs_stats.total_known / total_morphs) * 100
        total_learning_percent = (file_morphs_stats.total_learning / total_morphs) * 100
        total_unknown_percent = (file_morphs_stats.total_unknowns / total_morphs) * 100

    # fmt: off
    file_name_item = QTableWidgetItem(file_name)

    unique_morphs_item = QTableWidgetIntegerItem(unique_morphs)
    unique_known_item = QTableWidgetPercentItem(round(unique_known_percent, 1))
    unique_learning_item = QTableWidgetPercentItem(round(unique_learning_percent, 1))
    unique_unknowns_item = QTableWidgetPercentItem(round(unique_unknown_percent, 1))

    total_morphs_item = QTableWidgetIntegerItem(total_morphs)
    total_known_item = QTableWidgetPercentItem(round(total_known_percent, 1))
    total_learning_item = QTableWidgetPercentItem(round(total_learning_percent, 1))
    total_unknown_item = QTableWidgetPercentItem(round(total_unknown_percent, 1))

    unique_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    unique_known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    unique_learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    unique_unknowns_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    total_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    total_known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    total_learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    total_unknown_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    ui.percentTableWidget.setItem(row, Column.FILE_NAME.value, file_name_item)
    ui.percentTableWidget.setItem(row, Column.UNIQUE_MORPHS.value, unique_morphs_item)
    ui.percentTableWidget.setItem(row, Column.UNIQUE_KNOWN.value, unique_known_item)
    ui.percentTableWidget.setItem(row, Column.UNIQUE_LEARNING.value, unique_learning_item)
    ui.percentTableWidget.setItem(row, Column.UNIQUE_UNKNOWNS.value, unique_unknowns_item)
    ui.percentTableWidget.setItem(row, Column.TOTAL_MORPHS.value, total_morphs_item)
    ui.percentTableWidget.setItem(row, Column.TOTAL_KNOWN.value, total_known_item)
    ui.percentTableWidget.setItem(row, Column.TOTAL_LEARNING.value, total_learning_item)
    ui.percentTableWidget.setItem(row, Column.TOTAL_UNKNOWNS.value, total_unknown_item)
    # fmt: on


def _add_total_row_to_tables(
    ui: Ui_GeneratorsWindow,
    input_dir_root: Path,
    input_files: list[Path],
    global_report_morph_stats: FileMorphsStats,
) -> None:
    fake_input_file = Path(input_dir_root, "Total")

    _populate_numerical_table(
        ui=ui,
        input_dir_root=input_dir_root,
        input_file=fake_input_file,
        row=len(input_files),
        file_morphs_stats=global_report_morph_stats,
    )
    _populate_percentage_table(
        ui=ui,
        input_dir_root=input_dir_root,
        input_file=fake_input_file,
        row=len(input_files),
        file_morphs_stats=global_report_morph_stats,
    )
