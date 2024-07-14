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
from ..exceptions import CancelledOperationException, EmptyFileSelectionException, \
NoMorphsInPriorityRangeException
from ..morpheme import MorphOccurrence
from ..morphemizers import morphemizer, spacy_wrapper
from ..morphemizers.morphemizer import Morphemizer, SpacyMorphemizer
from ..table_utils import QTableWidgetIntegerItem, QTableWidgetPercentItem
from ..ui.progress_window_ui import Ui_ProgressWindow
from . import progress_text_processing, progress_utils, readability_report_utils
from .progress_output_dialog import GeneratorOutputDialog, OutputOptions
from .progress_text_processing import PreprocessOptions
from .readability_report_utils import FileMorphsStats
from .progress_utils import get_progress_reports, Bins


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

        self._columns = {}
        # For all tables
        self._columns['morph_priorities'] = 0
        # For numerical and percentage tables
        self._columns['total_morphs'] = 1
        self._columns['known'] = 2
        self._columns['learning'] = 3
        self._columns['unknowns'] = 4
        self._columns['missing'] = 5
        # For morph lists
        self._columns['lemma'] = 1
        self._columns['inflection'] = 2
        self._columns['status'] = 3

        self.num_numerical_percent_columns = 6
        self.num_morph_list_columns = 4

        self._setup_numerical_percent_table(self.ui.numericalTableWidget)
        self._setup_numerical_percent_table(self.ui.percentTableWidget)
        self._setup_morph_list_table(self.ui.morphListTableWidget)
        self._setup_buttons()
        self._setup_checkboxes()

        self.show()

    def _setup_numerical_percent_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)
        table.setColumnCount(self.num_numerical_percent_columns)

        table.setColumnWidth(self._columns['morph_priorities'], 200)
        table.setColumnWidth(self._columns['total_morphs'], 90)
        table.setColumnWidth(self._columns['known'], 90)
        table.setColumnWidth(self._columns['learning'], 90)
        table.setColumnWidth(self._columns['unknowns'], 90)
        table.setColumnWidth(self._columns['missing'], 90)

        table_horizontal_headers: QHeaderView | None = table.horizontalHeader()
        assert table_horizontal_headers is not None
        table_horizontal_headers.setSectionsMovable(True)

        # disables manual editing of the table
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

    def _setup_morph_list_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)
        table.setColumnCount(self.num_morph_list_columns)

        table.setColumnWidth(self._columns['morph_priorities'], 200)
        table.setColumnWidth(self._columns['lemma'], 90)
        table.setColumnWidth(self._columns['inflection'], 90)
        table.setColumnWidth(self._columns['status'], 90)

        table_horizontal_headers: QHeaderView | None = table.horizontalHeader()
        assert table_horizontal_headers is not None
        table_horizontal_headers.setSectionsMovable(True)

        # disables manual editing of the table
        table.setEditTriggers(
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

    def _setup_checkboxes(self) -> None:
        self.ui.cumulativeCheckBox.setChecked(False)
        am_config = AnkiMorphsConfig()
        if am_config.evaluate_morph_lemma:
            self.ui.lemmaRadioButton.setChecked(True)
            self.ui.inflectionRadioButton.setChecked(False)
        else:
            self.ui.lemmaRadioButton.setChecked(False)
            self.ui.inflectionRadioButton.setChecked(True)


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

    def _get_selected_bins(self) -> Bins:

        min_priority = self.ui.minPrioritySpinBox.value()
        original_min_priority = min_priority
        max_priority = self.ui.maxPrioritySpinBox.value()
        bin_size = self.ui.binSizeSpinBox.value()
        use_cumulative_statistics = self.ui.cumulativeCheckBox.isChecked() 

        spec = []
        while min_priority+bin_size-1 < max_priority:
            if use_cumulative_statistics:
                spec.append((original_min_priority,min_priority+bin_size-1))
            else:
                spec.append((min_priority,min_priority+bin_size-1))
            
            min_priority = min_priority+bin_size

        if use_cumulative_statistics:
            spec.append((original_min_priority,max_priority))
        else:
            spec.append((min_priority,max_priority))

        return Bins(spec)


    def _background_calculate_progress_and_populate_tables(self) -> None:
        assert mw is not None
        assert mw.progress is not None

        am_config = AnkiMorphsConfig()
        am_db = AnkiMorphsDB()


        bins = self._get_selected_bins()

        reports = get_progress_reports(am_config, am_db, bins)
        self._populate_tables(reports)

    def _populate_tables(self, reports: list[ProgressReport]) -> None:
        
        assert isinstance(self.ui, Ui_ProgressWindow)

        self.ui.numericalTableWidget.clearContents()
        self.ui.percentTableWidget.clearContents()

        self.ui.numericalTableWidget.setRowCount(len(reports))
        self.ui.percentTableWidget.setRowCount(len(reports))

        for row, report in enumerate(reports):
            if report.get_total_morphs() == 0:
                self.ui.numericalTableWidget.setRowCount(row)
                self.ui.percentTableWidget.setRowCount(row)
                raise NoMorphsInPriorityRangeException(report.min_priority,
                    report.max_priority)
            else:
                self._populate_numerical_table(report, row)
                self._populate_percent_table(report, row)



    def _populate_numerical_table(self, report: ProgressReport, row: int) -> None:

        known_percent = round(report.get_total_known()/report.get_total_morphs()*100,1)
        learning_percent = round(report.get_total_learning()/report.get_total_morphs()*100,1)
        unknowns_percent = round(report.get_total_unknowns()/report.get_total_morphs()*100,1)

        # Eliminates any possiblity of strange rounding 
        missing_percent = round(100 - known_percent - learning_percent - unknowns_percent,1) 

        morph_priorities_item = QTableWidgetItem(f"{report.min_priority}-{report.max_priority}")
        total_morphs_item = QTableWidgetIntegerItem(report.get_total_morphs())
        known_item = QTableWidgetIntegerItem(report.get_total_known())
        learning_item = QTableWidgetIntegerItem(report.get_total_learning())
        unknowns_item = QTableWidgetIntegerItem(report.get_total_unknowns())
        missing_item = QTableWidgetIntegerItem(report.get_total_missing())


        morph_priorities_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unknowns_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        missing_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)


        self.ui.numericalTableWidget.setItem(
            row, self._columns['morph_priorities'], morph_priorities_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._columns['total_morphs'], total_morphs_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._columns['known'], known_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._columns['learning'], learning_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._columns['unknowns'], unknowns_item
        )
        self.ui.numericalTableWidget.setItem(
            row, self._columns['missing'], missing_item
        )

    def _populate_percent_table(self, report: ProgressReport, row: int) -> None:

        known_percent = round(report.get_total_known()/report.get_total_morphs()*100,1)
        learning_percent = round(report.get_total_learning()/report.get_total_morphs()*100,1)
        unknowns_percent = round(report.get_total_unknowns()/report.get_total_morphs()*100,1)

        # Eliminates any possiblity of strange rounding 
        missing_percent = round(100 - known_percent - learning_percent - unknowns_percent,1) 

        morph_priorities_item = QTableWidgetItem(f"{report.min_priority}-{report.max_priority}")
        total_morphs_item = QTableWidgetIntegerItem(report.get_total_morphs())
        known_item = QTableWidgetPercentItem(known_percent)
        learning_item = QTableWidgetPercentItem(learning_percent)
        unknowns_item = QTableWidgetPercentItem(unknowns_percent)
        missing_item = QTableWidgetPercentItem(missing_percent)


        morph_priorities_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unknowns_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        missing_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)


        self.ui.percentTableWidget.setItem(
            row, self._columns['morph_priorities'], morph_priorities_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._columns['total_morphs'], total_morphs_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._columns['known'], known_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._columns['learning'], learning_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._columns['unknowns'], unknowns_item
        )
        self.ui.percentTableWidget.setItem(
            row, self._columns['missing'], missing_item
        )


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
        tooltip("Progress report finished", parent=self)

    def _on_failure(
        self,
        error: Exception | CancelledOperationException | NoMorphsInPriorityRangeException,
    ) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None
        mw.progress.finish()

        if isinstance(error, CancelledOperationException):
            tooltip("Cancelled progress report calculation", parent=self)
        elif isinstance(error, NoMorphsInPriorityRangeException):
             tooltip(f"No morphs in priority range {error.min_priority}-{error.max_priority}", 
                    parent=self)
        else:
            raise error

