from __future__ import annotations

import os
from pathlib import Path

from aqt import mw
from aqt.qt import QDialog, QFileDialog  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from .. import ankimorphs_globals as am_globals
from ..extra_settings import extra_settings_keys
from ..extra_settings.ankimorphs_extra_settings import AnkiMorphsExtraSettings
from ..ui.generator_output_dialog_ui import Ui_GeneratorOutputDialog


class OutputOptions:  # pylint:disable=too-many-instance-attributes
    def __init__(self, ui: Ui_GeneratorOutputDialog):
        # fmt: off
        self.output_path: Path = Path(ui.outputLineEdit.text())
        self.store_only_lemma: bool = ui.storeOnlyMorphLemmaRadioButton.isChecked()
        self.store_lemma_and_inflection: bool = ui.storeMorphLemmaAndInflectionRadioButton.isChecked()
        self.min_occurrence: bool = ui.minOccurrenceRadioButton.isChecked()
        self.comprehension: bool = ui.comprehensionRadioButton.isChecked()
        self.min_occurrence_threshold: int = ui.minOccurrenceSpinBox.value()
        self.comprehension_threshold: int = ui.comprehensionSpinBox.value()
        self.selected_extra_occurrences_column: bool = ui.addOccurrencesColumnCheckBox.isChecked()
        # fmt: on


class GeneratorOutputDialog(QDialog):
    def __init__(
        self, priority_file_mode: bool = False, study_plan_mode: bool = False
    ) -> None:
        assert mw is not None

        if priority_file_mode == study_plan_mode:
            raise ValueError("Modes must be different")

        super().__init__(parent=None)  # no parent makes the dialog modeless
        self.ui = Ui_GeneratorOutputDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        self.priority_file_mode = priority_file_mode
        self.study_plan_mode = study_plan_mode
        self.am_extra_settings = AnkiMorphsExtraSettings()

        self._default_output_dir: str = os.path.join(
            mw.pm.profileFolder(), am_globals.PRIORITY_FILES_DIR_NAME
        )

        if self.priority_file_mode:
            self.am_extra_settings.beginGroup(
                extra_settings_keys.Dialogs.GENERATOR_OUTPUT_PRIORITY_FILE
            )
            self._default_output_file = "priority-file.csv"

        else:
            self.am_extra_settings.beginGroup(
                extra_settings_keys.Dialogs.GENERATOR_OUTPUT_STUDY_PLAN
            )
            self._default_output_file = "study-plan-frequency-file.csv"

        self._setup_output_path()
        self._setup_buttons()
        self._setup_spin_boxes()
        self._setup_checkboxes()
        self._setup_geometry()

        self.am_extra_settings.endGroup()

    def _setup_output_path(self) -> None:
        stored_output_file_path: str = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsOutputKeys.OUTPUT_FILE_PATH, type=str
        )
        if stored_output_file_path == "":
            self.ui.outputLineEdit.setText(
                os.path.join(self._default_output_dir, self._default_output_file)
            )
        else:
            self.ui.outputLineEdit.setText(stored_output_file_path)

    def _setup_buttons(self) -> None:
        self.ui.selectFilePushButton.setAutoDefault(True)

        # default to the min occurrence option
        stored_min_occurrence_selected: bool = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsOutputKeys.MIN_OCCURRENCE_SELECTED,
            defaultValue=True,
            type=bool,
        )
        stored_comprehension_selected: bool = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsOutputKeys.COMPREHENSION_SELECTED,
            defaultValue=False,
            type=bool,
        )
        stored_lemma_format_selected: bool = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsOutputKeys.LEMMA_FORMAT,
            defaultValue=False,
            type=bool,
        )
        stored_inflection_format_selected: bool = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsOutputKeys.INFLECTION_FORMAT,
            defaultValue=True,
            type=bool,
        )

        self.ui.minOccurrenceRadioButton.setChecked(stored_min_occurrence_selected)
        self.ui.comprehensionRadioButton.setChecked(stored_comprehension_selected)

        # also disable the spinbox of the non-selected option
        if self.ui.minOccurrenceRadioButton.isChecked():
            self.ui.comprehensionSpinBox.setDisabled(True)
        else:
            self.ui.minOccurrenceSpinBox.setDisabled(True)

        # fmt: off
        self.ui.storeMorphLemmaAndInflectionRadioButton.setChecked(stored_inflection_format_selected)
        self.ui.storeOnlyMorphLemmaRadioButton.setChecked(stored_lemma_format_selected)

        self.ui.selectFilePushButton.clicked.connect(self._on_output_button_clicked)
        self.ui.okPushButton.clicked.connect(self._on_ok_button_clicked)
        self.ui.cancelPushButton.clicked.connect(self.reject)

        self.ui.minOccurrenceRadioButton.clicked.connect(self._min_occurrence_selected)
        self.ui.comprehensionRadioButton.clicked.connect(self._comprehension_selected)
        # fmt: on

    def _setup_spin_boxes(self) -> None:
        stored_comprehension_cutoff: int = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsOutputKeys.COMPREHENSION_CUTOFF,
            defaultValue=self.ui.comprehensionSpinBox.value(),
            type=int,
        )
        stored_occurrence_cutoff: int = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsOutputKeys.MIN_OCCURRENCE_CUTOFF,
            defaultValue=self.ui.minOccurrenceSpinBox.value(),
            type=int,
        )
        self.ui.comprehensionSpinBox.setValue(stored_comprehension_cutoff)
        self.ui.minOccurrenceSpinBox.setValue(stored_occurrence_cutoff)

    def _setup_checkboxes(self) -> None:
        stored_occurrences_selected: bool = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsOutputKeys.OCCURRENCES_COLUMN_SELECTED,
            defaultValue=False,
            type=bool,
        )
        self.ui.addOccurrencesColumnCheckBox.setChecked(stored_occurrences_selected)

    def _setup_geometry(self) -> None:
        stored_geometry = self.am_extra_settings.value(
            extra_settings_keys.GeneratorsWindowKeys.WINDOW_GEOMETRY
        )
        if stored_geometry is not None:
            self.restoreGeometry(stored_geometry)

    def _min_occurrence_selected(self) -> None:
        self.ui.comprehensionSpinBox.setDisabled(True)
        self.ui.minOccurrenceSpinBox.setEnabled(True)

    def _comprehension_selected(self) -> None:
        self.ui.comprehensionSpinBox.setEnabled(True)
        self.ui.minOccurrenceSpinBox.setDisabled(True)

    def _on_output_button_clicked(self) -> None:
        assert mw is not None

        output_file_path, _filter = QFileDialog.getOpenFileName(
            directory=self._default_output_dir
        )

        if output_file_path == "":
            output_file_path = os.path.join(
                self._default_output_dir, self._default_output_file
            )

        self.ui.outputLineEdit.setText(output_file_path)

    def _on_ok_button_clicked(self) -> None:
        if self.ui.outputLineEdit.text().endswith(".csv"):
            self.accept()
        else:
            tooltip(msg="Output needs to be a .csv file", parent=self)

    def get_selected_options(self) -> OutputOptions:
        return OutputOptions(self.ui)

    def done(self, result: int) -> None:
        if self.priority_file_mode:
            self.am_extra_settings.save_generator_priority_file_settings(
                ui=self.ui, geometry=self.saveGeometry()
            )
        else:
            self.am_extra_settings.save_generator_study_plan_settings(
                ui=self.ui, geometry=self.saveGeometry()
            )

        super().done(result)
