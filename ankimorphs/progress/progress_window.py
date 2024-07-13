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
from ..ui.progress_window_ui import Ui_ProgressWindow
from . import progress_text_processing, progress_utils, readability_report_utils
from .progress_output_dialog import GeneratorOutputDialog, OutputOptions
from .progress_text_processing import PreprocessOptions
from .readability_report_utils import FileMorphsStats
from .progress_utils import get_progress_reports


class ProgressWindow(QMainWindow):  # pylint:disable=too-many-instance-attributes
    ##############################################################################
    #                                   BASE
    ##############################################################################
    def __init__(
        self,
        parent: QMainWindow | None = None,
    ) -> None:
        super().__init__(parent)

        self.ui = Ui_ProgressWindow()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        #self._input_files: list[Path] = []

        self._morph_priorities_column = 0
        self._total_known_column = 1
        self._total_unknown_column = 2
        #self._unique_learning_column = 3
        #self._unique_unknowns_column = 4
        #self._total_morphs_column = 5
        #self._total_known_column = 6
        #self._total_learning_column = 7
        #self._total_unknowns_column = 8
        self._number_of_columns = 3

        #self._morphemizers: list[Morphemizer] = morphemizer.get_all_morphemizers()
        #self._populate_morphemizers()
        #self._setup_checkboxes()
        #self._input_dir_root: Path

        self._setup_table(self.ui.numericalTableWidget)
        self._setup_table(self.ui.percentTableWidget)
        self._setup_buttons()

        self.show()

    def _setup_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setColumnCount(self._number_of_columns)

        table.setColumnWidth(self._morph_priorities_column, 200)
        table.setColumnWidth(self._total_known_column, 90)
        table.setColumnWidth(self._total_unknown_column, 90)

        table.setSortingEnabled(False)
        table.setSortingEnabled(False)

        #table.setColumnWidth(self._unique_learning_column, 90)
        #table.setColumnWidth(self._unique_unknowns_column, 90)
        #table.setColumnWidth(self._total_morphs_column, 90)
        #table.setColumnWidth(self._total_known_column, 90)
        #table.setColumnWidth(self._total_learning_column, 90)
        #table.setColumnWidth(self._total_unknowns_column, 90)

        table_horizontal_headers: QHeaderView | None = table.horizontalHeader()
        assert table_horizontal_headers is not None
        table_horizontal_headers.setSectionsMovable(True)

        # disables manual editing of the table
        self.ui.numericalTableWidget.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

    def _setup_buttons(self) -> None:
        #self.ui.selectFolderPushButton.clicked.connect(self._on_select_folder_clicked)
        self.ui.calculateProgressPushButton.clicked.connect(self._on_calculate_progress_button_clicked)
        #self.ui.generateReportPushButton.clicked.connect(
        #    self._generate_readability_report
        #)
        #self.ui.generateFrequencyFilePushButton.clicked.connect(
        #    self._generate_frequency_file
        #)
        #self.ui.generateStudyPlanPushButton.clicked.connect(self._generate_study_plan)

        ## disable generator buttons until files have been loaded
        #self.ui.generateReportPushButton.setDisabled(True)
        #self.ui.generateFrequencyFilePushButton.setDisabled(True)
        #self.ui.generateStudyPlanPushButton.setDisabled(True)

    #def _populate_morphemizers(self) -> None:
    #    morphemizer_names = [mizer.get_description() for mizer in self._morphemizers]
    #    self.ui.morphemizerComboBox.addItems(morphemizer_names)

    #def _setup_checkboxes(self) -> None:
    #    self.ui.txtFilesCheckBox.setChecked(True)
    #    self.ui.srtFilesCheckBox.setChecked(True)
    #    self.ui.vttFilesCheckBox.setChecked(True)
    #    self.ui.mdFilesCheckBox.setChecked(True)

    #def _on_select_folder_clicked(self) -> None:
    #    input_dir: str = QFileDialog.getExistingDirectory(
    #        parent=self,
    #        caption="Directory with files to analyze",
    #        directory=QDir().homePath(),
    #    )
    #    self.ui.inputDirLineEdit.setText(input_dir)

    def _on_calculate_progress_button_clicked(self) -> None:
        # calculate progress stats and populate table in the background, 
        # since it could take a long time to complete
        assert mw is not None

        mw.progress.start(label="Calculating progress")
        operation = QueryOp(
            parent=self,
            op=lambda _: self._background_calculate_progress_and_populate_tables(),
            success=lambda _: self._on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _on_success(self) -> None:
        assert mw is not None
        mw.progress.finish()
    #    self.ui.generateReportPushButton.setEnabled(True)
    #    self.ui.generateFrequencyFilePushButton.setEnabled(True)
    #    self.ui.generateStudyPlanPushButton.setEnabled(True)

    def _background_calculate_progress_and_populate_tables(self) -> None:
        assert mw is not None
        assert mw.progress is not None

        am_config = AnkiMorphsConfig()
        am_db = AnkiMorphsDB()
        reports = get_progress_reports(am_config, am_db)
        print(reports[0].get_total_known() / reports[0].get_total_morphs())
        print("Success")
#
    #    # clearing the list prevents duplicate when
    #    # the load button is clicked more than once
    #    self._input_files.clear()
#
    #    input_dir = self.ui.inputDirLineEdit.text()
    #    self._input_dir_root = Path(input_dir)
    #    extensions = self._get_checked_extensions()
#
    #    # os.walk goes through all the sub-dirs recursively
    #    for dir_path, _, file_names in os.walk(input_dir):
    #        for file_name in file_names:
    #            if mw.progress.want_cancel():  # user clicked 'x'
    #                raise CancelledOperationException
    #            if file_name.lower().endswith(extensions):
    #                file_path = Path(dir_path, file_name)
    #                self._input_files.append(file_path)
#
    #    # without this sorting, the initial order will be (seemingly) random
    #    self._input_files.sort()
    #    self._populate_files_column()

    #def _populate_files_column(self) -> None:
    #    # sorting has to be disabled before populating because bugs can occur
#
    #    # clear previous results
    #    self.ui.numericalTableWidget.clearContents()
    #    self.ui.percentTableWidget.clearContents()
#
    #    self.ui.numericalTableWidget.setRowCount(len(self._input_files))
    #    self.ui.percentTableWidget.setRowCount(len(self._input_files))
#
    #    for _row, _file_name in enumerate(self._input_files):
    #        relative_file_name = str(_file_name.relative_to(self._input_dir_root))
#
    #        file_name_item_numerical = QTableWidgetItem(relative_file_name)
    #        file_name_item_percentage = QTableWidgetItem(relative_file_name)
#
    #        self.ui.numericalTableWidget.setItem(
    #            _row, self._file_name_column, file_name_item_numerical
    #        )
    #        self.ui.percentTableWidget.setItem(
    #            _row, self._file_name_column, file_name_item_percentage
    #        )

    #def _get_checked_extensions(self) -> tuple[str, ...]:
    #    extensions = []
#
    #    if self.ui.txtFilesCheckBox.isChecked():
    #        extensions.append(".txt")
    #    if self.ui.srtFilesCheckBox.isChecked():
    #        extensions.append(".srt")
    #    if self.ui.vttFilesCheckBox.isChecked():
    #        extensions.append(".vtt")
    #    if self.ui.mdFilesCheckBox.isChecked():
    #        extensions.append(".md")
#
    #    # we return a tuple to make it compatible with .endswith()
    #    return tuple(extensions)

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.close()
        dialog_name = ankimorphs_globals.PROGRESS_DIALOG_NAME
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
        error: Exception | CancelledOperationException,
    ) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None
        mw.progress.finish()

        if isinstance(error, CancelledOperationException):
            tooltip("Cancelled progress calculation", parent=self)
        else:
            raise error

