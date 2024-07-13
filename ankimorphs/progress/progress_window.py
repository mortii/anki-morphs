from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import Any, Callable

import aqt
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (  # pylint:disable=no-name-in-module
    QAbstractItemView,
    QDialog,
    QDir,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    Qt,
    QTableWidget,
    QTableWidgetItem,
)
from aqt.utils import tooltip

from .. import ankimorphs_globals
from ..ankimorphs_config import AnkiMorphsConfig
from ..ankimorphs_db import AnkiMorphsDB
from ..exceptions import CancelledOperationException, EmptyFileSelectionException
from ..morpheme import MorphOccurrence
from ..morphemizers import morphemizer, spacy_wrapper
from ..morphemizers.morphemizer import Morphemizer, SpacyMorphemizer
from ..table_utils import QTableWidgetIntegerItem, QTableWidgetPercentItem
from ..ui.generators_window_ui import Ui_GeneratorsWindow
from . import progress_text_processing, progress_utils, readability_report_utils
from .progress_output_dialog import GeneratorOutputDialog, OutputOptions
from .progress_text_processing import PreprocessOptions
from .readability_report_utils import FileMorphsStats


class ProgressWindow(QMainWindow):  # pylint:disable=too-many-instance-attributes
    ##############################################################################
    #                                   BASE
    ##############################################################################
    def __init__(
        self,
        parent: QMainWindow | None = None,
    ) -> None:
        super().__init__(parent)

        self.ui = Ui_GeneratorsWindow()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        self._input_files: list[Path] = []

        self._file_name_column = 0
        self._unique_morphs_column = 1
        self._unique_known_column = 2
        self._unique_learning_column = 3
        self._unique_unknowns_column = 4
        self._total_morphs_column = 5
        self._total_known_column = 6
        self._total_learning_column = 7
        self._total_unknowns_column = 8
        self._number_of_columns = 9

        self._morphemizers: list[Morphemizer] = morphemizer.get_all_morphemizers()
        self._populate_morphemizers()
        self._setup_checkboxes()
        self._input_dir_root: Path

        self._setup_table(self.ui.numericalTableWidget)
        self._setup_table(self.ui.percentTableWidget)
        self._setup_buttons()

        self.show()

    def _setup_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setColumnCount(self._number_of_columns)

        table.setColumnWidth(self._file_name_column, 200)
        table.setColumnWidth(self._unique_morphs_column, 90)
        table.setColumnWidth(self._unique_known_column, 90)
        table.setColumnWidth(self._unique_learning_column, 90)
        table.setColumnWidth(self._unique_unknowns_column, 90)
        table.setColumnWidth(self._total_morphs_column, 90)
        table.setColumnWidth(self._total_known_column, 90)
        table.setColumnWidth(self._total_learning_column, 90)
        table.setColumnWidth(self._total_unknowns_column, 90)

        table_horizontal_headers: QHeaderView | None = table.horizontalHeader()
        assert table_horizontal_headers is not None
        table_horizontal_headers.setSectionsMovable(True)

        # disables manual editing of the table
        self.ui.numericalTableWidget.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

    def _setup_buttons(self) -> None:
        self.ui.selectFolderPushButton.clicked.connect(self._on_select_folder_clicked)
        self.ui.loadFilesPushButton.clicked.connect(self._on_load_files_button_clicked)
        self.ui.generateReportPushButton.clicked.connect(
            self._generate_readability_report
        )
        self.ui.generateFrequencyFilePushButton.clicked.connect(
            self._generate_frequency_file
        )
        self.ui.generateStudyPlanPushButton.clicked.connect(self._generate_study_plan)

        # disable generator buttons until files have been loaded
        self.ui.generateReportPushButton.setDisabled(True)
        self.ui.generateFrequencyFilePushButton.setDisabled(True)
        self.ui.generateStudyPlanPushButton.setDisabled(True)

    def _populate_morphemizers(self) -> None:
        morphemizer_names = [mizer.get_description() for mizer in self._morphemizers]
        self.ui.morphemizerComboBox.addItems(morphemizer_names)

    def _setup_checkboxes(self) -> None:
        self.ui.txtFilesCheckBox.setChecked(True)
        self.ui.srtFilesCheckBox.setChecked(True)
        self.ui.vttFilesCheckBox.setChecked(True)
        self.ui.mdFilesCheckBox.setChecked(True)

    def _on_select_folder_clicked(self) -> None:
        input_dir: str = QFileDialog.getExistingDirectory(
            parent=self,
            caption="Directory with files to analyze",
            directory=QDir().homePath(),
        )
        self.ui.inputDirLineEdit.setText(input_dir)

    def _on_load_files_button_clicked(self) -> None:
        # gather the files in the background since it could
        # take a long time to complete
        assert mw is not None

        mw.progress.start(label="Gathering input files")
        operation = QueryOp(
            parent=self,
            op=lambda _: self._background_gather_files_and_populate_files_column(),
            success=lambda _: self._on_successfully_loaded_files(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _on_successfully_loaded_files(self) -> None:
        assert mw is not None
        mw.progress.finish()
        self.ui.generateReportPushButton.setEnabled(True)
        self.ui.generateFrequencyFilePushButton.setEnabled(True)
        self.ui.generateStudyPlanPushButton.setEnabled(True)

    def _background_gather_files_and_populate_files_column(self) -> None:
        assert mw is not None

        # clearing the list prevents duplicate when
        # the load button is clicked more than once
        self._input_files.clear()

        input_dir = self.ui.inputDirLineEdit.text()
        self._input_dir_root = Path(input_dir)
        extensions = self._get_checked_extensions()

        # os.walk goes through all the sub-dirs recursively
        for dir_path, _, file_names in os.walk(input_dir):
            for file_name in file_names:
                if mw.progress.want_cancel():  # user clicked 'x'
                    raise CancelledOperationException
                if file_name.lower().endswith(extensions):
                    file_path = Path(dir_path, file_name)
                    self._input_files.append(file_path)

        # without this sorting, the initial order will be (seemingly) random
        self._input_files.sort()
        self._populate_files_column()

    def _populate_files_column(self) -> None:
        # sorting has to be disabled before populating because bugs can occur
        self.ui.numericalTableWidget.setSortingEnabled(False)
        self.ui.percentTableWidget.setSortingEnabled(False)

        # clear previous results
        self.ui.numericalTableWidget.clearContents()
        self.ui.percentTableWidget.clearContents()

        self.ui.numericalTableWidget.setRowCount(len(self._input_files))
        self.ui.percentTableWidget.setRowCount(len(self._input_files))

        for _row, _file_name in enumerate(self._input_files):
            relative_file_name = str(_file_name.relative_to(self._input_dir_root))

            file_name_item_numerical = QTableWidgetItem(relative_file_name)
            file_name_item_percentage = QTableWidgetItem(relative_file_name)

            self.ui.numericalTableWidget.setItem(
                _row, self._file_name_column, file_name_item_numerical
            )
            self.ui.percentTableWidget.setItem(
                _row, self._file_name_column, file_name_item_percentage
            )

        self.ui.numericalTableWidget.setSortingEnabled(True)
        self.ui.percentTableWidget.setSortingEnabled(True)

    def _get_checked_extensions(self) -> tuple[str, ...]:
        extensions = []

        if self.ui.txtFilesCheckBox.isChecked():
            extensions.append(".txt")
        if self.ui.srtFilesCheckBox.isChecked():
            extensions.append(".srt")
        if self.ui.vttFilesCheckBox.isChecked():
            extensions.append(".vtt")
        if self.ui.mdFilesCheckBox.isChecked():
            extensions.append(".md")

        # we return a tuple to make it compatible with .endswith()
        return tuple(extensions)

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.close()
        dialog_name = ankimorphs_globals.GENERATOR_DIALOG_NAME
        aqt.dialogs.markClosed(dialog_name)
        callback()

    def reopen(self) -> None:
        # This is used by the Anki dialog manager
        self.show()

    def _on_success(self) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None

        mw.progress.finish()
        tooltip("Generator finished", parent=self)

    def _on_failure(
        self,
        error: Exception | CancelledOperationException | EmptyFileSelectionException,
    ) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None
        mw.progress.finish()

        if isinstance(error, CancelledOperationException):
            tooltip("Cancelled generator", parent=self)
        elif isinstance(error, EmptyFileSelectionException):
            tooltip("No input files", parent=self)
        else:
            raise error

    ##############################################################################
    #                           READABILITY REPORT
    ##############################################################################

    def _generate_readability_report(self) -> None:
        assert mw is not None

        mw.progress.start(label="Generating readability report")
        operation = QueryOp(
            parent=self,
            op=lambda _: self._background_generate_report(),
            success=lambda _: self._on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _background_generate_report(self) -> None:
        assert mw is not None
        assert mw.progress is not None

        if len(self._input_files) == 0:
            raise EmptyFileSelectionException

        morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]] = (
            self._generate_morph_occurrences_by_file()
        )

        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label="Filling out report",
            )
        )

        # sorting has to be disabled before populating because bugs can occur
        self.ui.numericalTableWidget.setSortingEnabled(False)
        self.ui.percentTableWidget.setSortingEnabled(False)

        # clear previous results
        self.ui.numericalTableWidget.clearContents()
        self.ui.percentTableWidget.clearContents()

        self._populate_tables_with_report(morph_occurrences_by_file)

        self.ui.numericalTableWidget.setSortingEnabled(True)
        self.ui.percentTableWidget.setSortingEnabled(True)

    def _get_selected_morphemizer_and_nlp(self) -> tuple[Morphemizer, Any]:
        _morphemizer = self._morphemizers[self.ui.morphemizerComboBox.currentIndex()]
        assert _morphemizer is not None
        _nlp = None  # spacy.Language

        if isinstance(_morphemizer, SpacyMorphemizer):
            selected_index = self.ui.morphemizerComboBox.currentIndex()
            selected_text: str = self.ui.morphemizerComboBox.itemText(selected_index)
            spacy_model = selected_text.removeprefix("spaCy: ")
            _nlp = spacy_wrapper.get_nlp(spacy_model)

        return _morphemizer, _nlp

    def _generate_morph_occurrences_by_file(
        self, sorted_by_table: int = False
    ) -> dict[Path, dict[str, MorphOccurrence]]:
        """
        'sorted_by_table=True' is used for study plans where the order matters.
        """
        assert mw is not None

        _morphemizer, _nlp = self._get_selected_morphemizer_and_nlp()
        preprocess_options = PreprocessOptions(self.ui)
        morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]] = {}

        sorted_input_files: list[Path]

        if sorted_by_table:
            sorted_input_files = self._get_input_files_table_sorted()
        else:
            sorted_input_files = self._input_files

        for input_file in sorted_input_files:
            if mw.progress.want_cancel():  # user clicked 'x' button
                raise CancelledOperationException

            mw.taskman.run_on_main(
                partial(
                    mw.progress.update,
                    label=f"Processing file:<br>{input_file.relative_to(self._input_dir_root)}",
                )
            )

            with open(input_file, encoding="utf-8") as file:
                file_morph_occurrences: dict[str, MorphOccurrence] = (
                    generators_text_processing.create_file_morph_occurrences(
                        preprocess_options=preprocess_options,
                        file=file,
                        morphemizer=_morphemizer,
                        nlp=_nlp,
                    )
                )
                morph_occurrences_by_file[input_file] = file_morph_occurrences

        return morph_occurrences_by_file

    def _get_input_files_table_sorted(self) -> list[Path]:
        sorted_input_files: list[Path] = []
        current_table: QTableWidget | None = None

        if self.ui.tablesTabWidget.currentIndex() == 0:
            current_table = self.ui.numericalTableWidget
        elif self.ui.tablesTabWidget.currentIndex() == 1:
            current_table = self.ui.percentTableWidget

        assert current_table is not None

        for row in range(current_table.rowCount()):
            file_name_item: QTableWidgetItem | None = current_table.item(
                row, self._file_name_column
            )
            assert file_name_item is not None
            file_name_text: str = file_name_item.text()

            if file_name_text == "Total":
                continue

            # the root dir is stripped when loading the files, so we have to add it back
            sorted_input_files.append(Path(self._input_dir_root, file_name_text))

        return sorted_input_files

    def _populate_tables_with_report(
        self, morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]]
    ) -> None:
        am_config = AnkiMorphsConfig()
        am_db = AnkiMorphsDB()

        self.ui.numericalTableWidget.setRowCount(len(self._input_files) + 1)
        self.ui.percentTableWidget.setRowCount(len(self._input_files) + 1)

        # the global report will be presented as a "Total" file in the table
        global_report_morph_stats = FileMorphsStats()

        for row, input_file in enumerate(self._input_files):
            file_morphs = morph_occurrences_by_file[input_file]

            file_morphs_stats = readability_report_utils.get_morph_stats_from_file(
                am_config, am_db, file_morphs
            )
            global_report_morph_stats += file_morphs_stats

            self._populate_numerical_table(input_file, row, file_morphs_stats)
            self._populate_percentage_table(input_file, row, file_morphs_stats)

        self._add_total_row_to_tables(global_report_morph_stats)

        am_db.con.close()

    def _populate_numerical_table(  # pylint:disable=too-many-locals
        self,
        input_file: Path,
        row: int,
        file_morphs_stats: FileMorphsStats,
    ) -> None:
        assert isinstance(self.ui, Ui_GeneratorsWindow)

        file_name = str(input_file.relative_to(self._input_dir_root))

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

        file_name_item = QTableWidgetItem(file_name)

        unique_morphs_item = QTableWidgetIntegerItem(unique_morphs)
        unique_known_item = QTableWidgetIntegerItem(len(file_morphs_stats.unique_known))
        unique_learning_item = QTableWidgetIntegerItem(
            len(file_morphs_stats.unique_learning)
        )
        unique_unknowns_item = QTableWidgetIntegerItem(
            len(file_morphs_stats.unique_unknowns)
        )

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

        self.ui.numericalTableWidget.setItem(
            row, self._file_name_column, file_name_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._unique_morphs_column, unique_morphs_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._unique_known_column, unique_known_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._unique_learning_column, unique_learning_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._unique_unknowns_column, unique_unknowns_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._total_morphs_column, total_morphs_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._total_known_column, total_known_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._total_learning_column, total_learning_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._total_unknowns_column, total_unknown_item
        )

    def _populate_percentage_table(  # pylint:disable=too-many-locals
        self,
        input_file: Path,
        row: int,
        file_morphs_stats: FileMorphsStats,
    ) -> None:
        assert isinstance(self.ui, Ui_GeneratorsWindow)

        file_name = str(input_file.relative_to(self._input_dir_root))

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

            total_learning_percent = (
                file_morphs_stats.total_learning / total_morphs
            ) * 100

            total_unknown_percent = (
                file_morphs_stats.total_unknowns / total_morphs
            ) * 100

        file_name_item = QTableWidgetItem(file_name)

        unique_morphs_item = QTableWidgetIntegerItem(unique_morphs)
        unique_known_item = QTableWidgetPercentItem(round(unique_known_percent, 1))
        unique_learning_item = QTableWidgetPercentItem(
            round(unique_learning_percent, 1)
        )
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

        self.ui.percentTableWidget.setItem(row, self._file_name_column, file_name_item)
        self.ui.percentTableWidget.setItem(
            row, self._unique_morphs_column, unique_morphs_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._unique_known_column, unique_known_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._unique_learning_column, unique_learning_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._unique_unknowns_column, unique_unknowns_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._total_morphs_column, total_morphs_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._total_known_column, total_known_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._total_learning_column, total_learning_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._total_unknowns_column, total_unknown_item
        )

    def _add_total_row_to_tables(
        self, global_report_morph_stats: FileMorphsStats
    ) -> None:
        fake_input_file = Path(self._input_dir_root, "Total")

        self._populate_numerical_table(
            input_file=fake_input_file,
            row=len(self._input_files),
            file_morphs_stats=global_report_morph_stats,
        )
        self._populate_percentage_table(
            input_file=fake_input_file,
            row=len(self._input_files),
            file_morphs_stats=global_report_morph_stats,
        )

    ##############################################################################
    #                              FREQUENCY FILE
    ##############################################################################

    def _generate_frequency_file(self) -> None:
        assert mw is not None

        if len(self._input_files) == 0:
            self._on_failure(error=EmptyFileSelectionException())
            return

        default_output_file = Path(
            mw.pm.profileFolder(),
            ankimorphs_globals.FREQUENCY_FILES_DIR_NAME,
            "frequency-file.csv",
        )

        selected_output = GeneratorOutputDialog(default_output_file)
        result_code: int = selected_output.exec()

        if result_code != QDialog.DialogCode.Accepted:
            return

        selected_output_options: OutputOptions = selected_output.get_selected_options()

        mw.progress.start(label="Generating frequency file")
        operation = QueryOp(
            parent=self,
            op=lambda _: self._background_generate_frequency_file(
                selected_output_options
            ),
            success=lambda _: self._on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _background_generate_frequency_file(
        self, selected_output_options: OutputOptions
    ) -> None:
        assert mw is not None
        assert mw.progress is not None

        morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]] = (
            self._generate_morph_occurrences_by_file()
        )

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

        generators_utils.write_out_frequency_file(
            selected_output_options, total_morph_occurrences
        )

    ##############################################################################
    #                              STUDY PLAN
    ##############################################################################

    def _generate_study_plan(self) -> None:
        assert mw is not None

        if len(self._input_files) == 0:
            self._on_failure(error=EmptyFileSelectionException())
            return

        default_output_file = Path(
            mw.pm.profileFolder(),
            ankimorphs_globals.FREQUENCY_FILES_DIR_NAME,
            "study-plan-frequency-file.csv",
        )

        selected_output = GeneratorOutputDialog(default_output_file)
        result_code: int = selected_output.exec()

        if result_code != QDialog.DialogCode.Accepted:
            return

        selected_output_options: OutputOptions = selected_output.get_selected_options()

        mw.progress.start(label="Generating study plan")
        operation = QueryOp(
            parent=self,
            op=lambda _: self._background_generate_study_plan(selected_output_options),
            success=lambda _: self._on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _background_generate_study_plan(
        self, selected_output_options: OutputOptions
    ) -> None:
        assert mw is not None
        assert mw.progress is not None

        morph_occurrences_by_file: dict[Path, dict[str, MorphOccurrence]] = (
            self._generate_morph_occurrences_by_file(sorted_by_table=True)
        )

        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label="Sorting morphs",
            )
        )

        # for every file, sort the morph occurrence dicts
        for file, morph_dict in morph_occurrences_by_file.items():
            sorted_morph_frequency = dict(
                sorted(
                    morph_dict.items(),
                    key=lambda item: item[1].occurrence,
                    reverse=True,
                )
            )
            morph_occurrences_by_file[file] = sorted_morph_frequency

        generators_utils.write_out_study_plan(
            input_dir_root=self._input_dir_root,
            selected_output_options=selected_output_options,
            morph_occurrences_by_file=morph_occurrences_by_file,
        )
