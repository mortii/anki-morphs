from __future__ import annotations

import os
import time
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
from ..exceptions import CancelledOperationException, \
NoMorphsInPriorityRangeException, FrequencyFileMalformedException, InvalidBinsException
from ..table_utils import QTableWidgetIntegerItem, QTableWidgetPercentItem
from ..ui.progression_window_ui import Ui_ProgressionWindow
from . import progression_utils
from .progression_utils import ProgressReport, Bins, get_progress_reports, get_priority_ordered_morph_statuses
from ..settings.settings_note_filters_tab import NoteFiltersTab
from ..recalc.morph_priority_utils import _get_morph_priority, _load_morph_priorities_from_file


class ProgressionWindow(QMainWindow):  # pylint:disable=too-many-instance-attributes
    ##############################################################################
    #                                   BASE
    ##############################################################################
    def __init__(
        self,
        parent: QMainWindow | None = None,
    ) -> None:
        super().__init__(parent)

        self.ui = Ui_ProgressionWindow()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

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
        self.num_morph_columns = 4

        self._setup_numerical_percent_table(self.ui.numericalTableWidget)
        self._setup_numerical_percent_table(self.ui.percentTableWidget)
        self._setup_morph_table(self.ui.morphTableWidget)
        self._setup_buttons()
        self._setup_checkboxes()
        self._setup_morph_priority_cbox()

        self.show()

    def _setup_numerical_percent_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)
        table.setColumnCount(self.num_numerical_percent_columns)

        table.setColumnWidth(self._columns['morph_priorities'], 90)
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

    def _setup_morph_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)
        table.setColumnCount(self.num_morph_columns)

        table.setColumnWidth(self._columns['morph_priorities'], 90)
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
        self.ui.calculateProgressPushButton.clicked.connect(self._on_calculate_progress_button_clicked)

    def _setup_checkboxes(self) -> None:
        self.ui.cumulativeCheckBox.setChecked(False)
        am_config = AnkiMorphsConfig()
        if am_config.evaluate_morph_lemma:
            self.ui.lemmaRadioButton.setChecked(True)
            self.ui.inflectionRadioButton.setChecked(False)
        else:
            self.ui.lemmaRadioButton.setChecked(False)
            self.ui.inflectionRadioButton.setChecked(True)

    def _setup_morph_priority_cbox(self) -> None:
        frequency_files: list[str] = [
            ankimorphs_globals.COLLECTION_FREQUENCY_OPTION,
        ]
        frequency_files += NoteFiltersTab._get_frequency_files()
        self.ui.morphPriorityCBox.addItems(frequency_files)


    def _on_calculate_progress_button_clicked(self) -> None:
        # calculate progress stats and populate table in the background, 
        # since it could take a long time to complete
        assert mw is not None

        mw.progress.start(label="Calculating progress report")
        operation = QueryOp(
            parent=self,
            op=lambda _: self._background_calculate_progress_and_populate_tables(),
            success=lambda _: self._on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _get_selected_bins(self) -> Bins:

        return Bins(
            min_index = self.ui.minPrioritySpinBox.value(),
            max_index = self.ui.maxPrioritySpinBox.value(),
            bin_size = self.ui.binSizeSpinBox.value(),
            is_cumulative = self.ui.cumulativeCheckBox.isChecked() 
        )

    def _get_selected_morph_priorities(self) -> dict[tuple[str,str],int]:

        am_db = AnkiMorphsDB()

        if self.ui.morphPriorityCBox.currentIndex() == 0: # Collection frequency
            return am_db.get_morph_priorities_from_collection(True)
        #Else
        return _load_morph_priorities_from_file(
            frequency_file_name=self.ui.morphPriorityCBox.currentText(),
            only_lemma_priorities=self._is_lemma_priority_selected(),
        )

    def _is_lemma_priority_selected(self) -> bool:

        return self.ui.lemmaRadioButton.isChecked()


    def _background_calculate_progress_and_populate_tables(self) -> None:
        assert mw is not None

        am_config = AnkiMorphsConfig()
        am_db = AnkiMorphsDB()

        bins = self._get_selected_bins()

        morph_priorities = self._get_selected_morph_priorities()
        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label="Calculating binned statistics",
            )
        )
        reports = get_progress_reports(am_db, bins, morph_priorities, 
                                       self._is_lemma_priority_selected())
        if mw.progress.want_cancel():  
            raise CancelledOperationException
        
        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label="Calculating morph statuses",
            )
        )
        morph_statuses = get_priority_ordered_morph_statuses(am_db, bins, morph_priorities,
                                       self._is_lemma_priority_selected())
        if mw.progress.want_cancel():  
            raise CancelledOperationException
        
        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label="Populating tables",
            )
        )
        self._populate_tables(reports,morph_statuses)

    def _populate_tables(self, 
        reports: list[ProgressReport], 
        morph_statuses: list[tuple[int,str,str,str]],
    ) -> None:
        
        assert isinstance(self.ui, Ui_ProgressionWindow)

        self.ui.numericalTableWidget.clearContents()
        self.ui.percentTableWidget.clearContents()
        self.ui.morphTableWidget.clearContents()

        self.ui.numericalTableWidget.setRowCount(len(reports))
        self.ui.percentTableWidget.setRowCount(len(reports))
        self.ui.morphTableWidget.setRowCount(len(morph_statuses))

        error_indexes: tuple[int,int] | None = None

        for row, report in enumerate(reports):
            if report.get_total_morphs() == 0:
                self.ui.numericalTableWidget.setRowCount(row)
                self.ui.percentTableWidget.setRowCount(row)
                error_indexes = (report.min_priority, report.max_priority)
                break
            else:
                self._populate_numerical_table(report, row)
                self._populate_percent_table(report, row)

        for row, morph_status in enumerate(morph_statuses):
            self._populate_morph_table(morph_status,row) 

        if error_indexes is not None:
            raise NoMorphsInPriorityRangeException(
                min_priority = error_indexes[0],
                max_priority = error_indexes[1]
            )


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

    def _populate_morph_table(self, morph_status: tuple[int,str,str,str], row: int) -> None:

        morph_priorities_item = QTableWidgetIntegerItem(morph_status[0])
        lemma_item = QTableWidgetItem(morph_status[1])
        inflection_item = QTableWidgetItem(morph_status[2])
        status_item = QTableWidgetItem(morph_status[3])

        morph_priorities_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        lemma_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        inflection_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ui.morphTableWidget.setItem(
            row, self._columns['morph_priorities'], morph_priorities_item
        )
        self.ui.morphTableWidget.setItem(
            row, self._columns['lemma'], lemma_item
        )
        self.ui.morphTableWidget.setItem(
            row, self._columns['inflection'], inflection_item
        )
        self.ui.morphTableWidget.setItem(
            row, self._columns['status'], status_item
        )


    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.close()
        dialog_name = ankimorphs_globals.PROGRESSION_DIALOG_NAME
        aqt.dialogs.markClosed(dialog_name)
        callback()

    def reopen(self) -> None:
        # This is used by the Anki dialog manager
        self.show()

    def _on_success(self) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None

        self.ui.calculateProgressPushButton.setText("Recalculate\nProgress\nReport")

        mw.progress.finish()
        tooltip("Progress report finished", parent=self)

    def _on_failure(
        self,
        error: Exception | CancelledOperationException | NoMorphsInPriorityRangeException | 
               FrequencyFileMalformedException | InvalidBinsException,
    ) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None

        self.ui.calculateProgressPushButton.setText("Recalculate\nProgress\nReport")

        mw.progress.finish()

        if isinstance(error, CancelledOperationException):
            tooltip("Cancelled progress report calculation", parent=self)
        elif isinstance(error, NoMorphsInPriorityRangeException):
             tooltip(f"No morphs in priority range {error.min_priority}-{error.max_priority}", 
                    parent=self)
        elif isinstance(error, FrequencyFileMalformedException):
             tooltip(error.reason, 
                    parent=self)
        elif isinstance(error, InvalidBinsException):
             tooltip(f"Invalid priority range", 
                    parent=self)

        else:
            raise error

