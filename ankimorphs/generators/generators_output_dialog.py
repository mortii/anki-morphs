from __future__ import annotations

from pathlib import Path

from aqt.qt import QDialog, QDir, QFileDialog  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from ..ui.generator_output_dialog_ui import Ui_GeneratorOutputDialog


class OutputOptions:  # pylint:disable=too-many-instance-attributes
    def __init__(self, ui: Ui_GeneratorOutputDialog):
        self.output_path: Path = Path(ui.outputLineEdit.text())

        self.store_only_lemma: bool = ui.storeOnlyMorphLemmaRadioButton.isChecked()
        self.store_lemma_and_inflection: bool = (
            ui.storeMorphLemmaAndInflectionRadioButton.isChecked()
        )

        self.min_occurrence: bool = ui.minOccurrenceRadioButton.isChecked()
        self.comprehension: bool = ui.comprehensionRadioButton.isChecked()

        self.min_occurrence_threshold: int = ui.minOccurrenceSpinBox.value()
        self.comprehension_threshold: int = ui.comprehensionSpinBox.value()

        self.selected_extra_occurrences_column: bool = (
            ui.addOccurrencesColumnCheckBox.isChecked()
        )


class GeneratorOutputDialog(QDialog):
    def __init__(self, default_output_path: Path) -> None:
        super().__init__(parent=None)  # no parent makes the dialog modeless
        self.ui = Ui_GeneratorOutputDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        self.ui.outputLineEdit.setText(str(default_output_path))

        self._default_output_file_name = default_output_path.name
        self._setup_buttons()

    def _setup_buttons(self) -> None:
        self.ui.selectFolderPushButton.setAutoDefault(True)

        # default to the min. occurrence option
        self.ui.minOccurrenceRadioButton.setChecked(True)
        # also disable the spinbox of the non-selected option
        self.ui.comprehensionSpinBox.setDisabled(True)

        self.ui.storeMorphLemmaAndInflectionRadioButton.setChecked(True)
        self.ui.storeOnlyMorphLemmaRadioButton.setChecked(False)

        self.ui.selectFolderPushButton.clicked.connect(self._on_output_button_clicked)
        self.ui.okPushButton.clicked.connect(self._on_ok_button_clicked)
        self.ui.cancelPushButton.clicked.connect(self.reject)

        self.ui.minOccurrenceRadioButton.clicked.connect(self._min_occurrence_selected)
        self.ui.comprehensionRadioButton.clicked.connect(self._comprehension_selected)

    def _min_occurrence_selected(self) -> None:
        self.ui.comprehensionSpinBox.setDisabled(True)
        self.ui.minOccurrenceSpinBox.setEnabled(True)

    def _comprehension_selected(self) -> None:
        self.ui.comprehensionSpinBox.setEnabled(True)
        self.ui.minOccurrenceSpinBox.setDisabled(True)

    def _on_output_button_clicked(self) -> None:
        output_dir: str = QFileDialog.getExistingDirectory(
            caption="Directory to place file",
            directory=QDir().homePath(),
        )
        _output_path = Path(output_dir, self._default_output_file_name)
        self.ui.outputLineEdit.setText(str(_output_path))

    def _on_ok_button_clicked(self) -> None:
        if self.ui.outputLineEdit.text().endswith(".csv"):
            self.accept()
        else:
            tooltip(msg="Output needs to be a .csv file", parent=self)

    def get_selected_options(self) -> OutputOptions:
        return OutputOptions(self.ui)
