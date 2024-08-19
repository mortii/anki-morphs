from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

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
    QTableWidget,
    QTableWidgetItem,
)
from aqt.utils import tooltip

from .. import ankimorphs_globals, message_box_utils
from ..exceptions import (
    CancelledOperationException,
    EmptyFileSelectionException,
    UnicodeException,
)
from ..morphemizers import morphemizer
from ..morphemizers.morphemizer import Morphemizer
from ..ui.generators_window_ui import Ui_GeneratorsWindow
from . import (
    priority_file_generator,
    readability_report_generator,
    study_plan_generator,
)
from .generators_output_dialog import GeneratorOutputDialog, OutputOptions
from .generators_utils import Column


class GeneratorWindow(QMainWindow):  # pylint:disable=too-many-instance-attributes
    def __init__(
        self,
        parent: QMainWindow | None = None,
    ) -> None:
        super().__init__(parent)

        self.ui = Ui_GeneratorsWindow()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        self._input_files: list[Path] = []
        self._morphemizers: list[Morphemizer] = morphemizer.get_all_morphemizers()
        self._populate_morphemizers()
        self._setup_checkboxes()
        self._input_dir_root: Path

        self._setup_table(self.ui.numericalTableWidget)
        self._setup_table(self.ui.percentTableWidget)
        self._setup_buttons()

        self.ui.inputDirLineEdit.textEdited.connect(
            lambda: self.ui.loadFilesPushButton.setEnabled(True)
        )

        self.show()

    def _setup_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setColumnCount(Column.NUMBER_OF_COLUMNS.value)

        table.setColumnWidth(Column.FILE_NAME.value, 200)
        table.setColumnWidth(Column.UNIQUE_MORPHS.value, 90)
        table.setColumnWidth(Column.UNIQUE_KNOWN.value, 90)
        table.setColumnWidth(Column.UNIQUE_LEARNING.value, 90)
        table.setColumnWidth(Column.UNIQUE_UNKNOWNS.value, 90)
        table.setColumnWidth(Column.TOTAL_MORPHS.value, 90)
        table.setColumnWidth(Column.TOTAL_KNOWN.value, 90)
        table.setColumnWidth(Column.TOTAL_LEARNING.value, 90)
        table.setColumnWidth(Column.TOTAL_UNKNOWNS.value, 90)

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
        self.ui.generatePriorityFilePushButton.clicked.connect(
            self._generate_priority_file
        )
        self.ui.generateStudyPlanPushButton.clicked.connect(self._generate_study_plan)

        # disable generator buttons until files have been loaded
        self.ui.generateReportPushButton.setDisabled(True)
        self.ui.generatePriorityFilePushButton.setDisabled(True)
        self.ui.generateStudyPlanPushButton.setDisabled(True)

    def _populate_morphemizers(self) -> None:
        morphemizer_names = [mizer.get_description() for mizer in self._morphemizers]
        self.ui.morphemizerComboBox.addItems(morphemizer_names)

    def _setup_checkboxes(self) -> None:
        checkboxes = [
            self.ui.txtFilesCheckBox,
            self.ui.srtFilesCheckBox,
            self.ui.vttFilesCheckBox,
            self.ui.mdFilesCheckBox,
        ]

        for checkbox in checkboxes:
            checkbox.setChecked(True)
            checkbox.clicked.connect(
                lambda: self.ui.loadFilesPushButton.setEnabled(True)
            )

    def _on_select_folder_clicked(self) -> None:
        input_dir: str = QFileDialog.getExistingDirectory(
            parent=self,
            caption="Directory with files to analyze",
            directory=QDir().homePath(),
        )
        self.ui.inputDirLineEdit.setText(input_dir)
        self.ui.loadFilesPushButton.setEnabled(True)

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
        self.ui.generatePriorityFilePushButton.setEnabled(True)
        self.ui.generateStudyPlanPushButton.setEnabled(True)

        # give a visual que that reloading is not necessary
        self.ui.loadFilesPushButton.setEnabled(False)

    def _background_gather_files_and_populate_files_column(self) -> None:
        assert mw is not None

        # clearing the list prevents duplicate when
        # the load button is clicked more than once
        self._input_files.clear()

        input_dir = self.ui.inputDirLineEdit.text()
        self._input_dir_root = Path(input_dir)
        extensions = self._get_checked_extensions()

        if not Path(input_dir).exists():
            raise NotADirectoryError

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
                _row, Column.FILE_NAME.value, file_name_item_numerical
            )
            self.ui.percentTableWidget.setItem(
                _row, Column.FILE_NAME.value, file_name_item_percentage
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

    def _generate_readability_report(self) -> None:
        assert mw is not None

        mw.progress.start(label="Generating readability report")
        operation = QueryOp(
            parent=self,
            op=lambda _: readability_report_generator.background_generate_report(
                ui=self.ui,
                morphemizers=self._morphemizers,
                input_dir_root=self._input_dir_root,
                input_files=self._input_files,
            ),
            success=lambda _: self._on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _generate_priority_file(self) -> None:
        assert mw is not None

        if len(self._input_files) == 0:
            self._on_failure(error=EmptyFileSelectionException())
            return

        default_output_file = Path(
            mw.pm.profileFolder(),
            ankimorphs_globals.PRIORITY_FILES_DIR_NAME,
            "priority-file.csv",
        )

        selected_output = GeneratorOutputDialog(default_output_file)
        result_code: int = selected_output.exec()

        if result_code != QDialog.DialogCode.Accepted:
            return

        selected_output_options: OutputOptions = selected_output.get_selected_options()

        mw.progress.start(label="Generating priority file")
        operation = QueryOp(
            parent=self,
            op=lambda _: priority_file_generator.background_generate_priority_file(
                selected_output_options=selected_output_options,
                ui=self.ui,
                morphemizers=self._morphemizers,
                input_dir_root=self._input_dir_root,
                input_files=self._input_files,
            ),
            success=lambda _: self._on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _generate_study_plan(self) -> None:
        assert mw is not None

        if len(self._input_files) == 0:
            self._on_failure(error=EmptyFileSelectionException())
            return

        default_output_file = Path(
            mw.pm.profileFolder(),
            ankimorphs_globals.PRIORITY_FILES_DIR_NAME,
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
            op=lambda _: study_plan_generator.background_generate_study_plan(
                selected_output_options=selected_output_options,
                ui=self.ui,
                morphemizers=self._morphemizers,
                input_dir_root=self._input_dir_root,
                input_files=self._input_files,
            ),
            success=lambda _: self._on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

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
        error: (
            Exception
            | CancelledOperationException
            | EmptyFileSelectionException
            | UnicodeException
            | NotADirectoryError
        ),
    ) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None
        mw.progress.finish()

        if isinstance(error, CancelledOperationException):
            tooltip("Cancelled generator", parent=self)
        elif isinstance(error, EmptyFileSelectionException):
            tooltip("No input files", parent=self)
        elif isinstance(error, UnicodeException):
            title = "Decoding Error"
            text = (
                f"Error: All files must be UTF-8 encoded.\n\n"
                f"The file at path '{error.path}' does not have UTF-8 encoding.\n\n"
            )
            message_box_utils.show_error_box(title=title, body=text, parent=self)
        elif isinstance(error, NotADirectoryError):
            tooltip("Input folder does not exist", parent=self)
        else:
            raise error
