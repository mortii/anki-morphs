from pathlib import Path

from aqt import mw
from aqt.qt import QByteArray, QSettings  # pylint:disable=no-name-in-module

from .. import ankimorphs_globals
from ..ui.generator_output_dialog_ui import Ui_GeneratorOutputDialog
from ..ui.generators_window_ui import Ui_GeneratorsWindow
from ..ui.known_morphs_exporter_dialog_ui import Ui_KnownMorphsExporterDialog
from ..ui.progression_window_ui import Ui_ProgressionWindow
from . import extra_settings_keys as keys  # pylint:disable=no-name-in-module
from .extra_settings_keys import (
    FileFormatsKeys,
    GeneratorsOutputKeys,
    GeneratorsWindowKeys,
    KnownMorphsExporterKeys,
    PreprocessKeys,
    ProgressionWindowKeys,
)


class AnkiMorphsExtraSettings(QSettings):
    def __init__(self) -> None:
        assert mw is not None
        extra_settings_path = Path(
            mw.pm.profileFolder(), "ankimorphs_extra_settings.ini"
        )
        super().__init__(str(extra_settings_path), QSettings.Format.IniFormat)

    def save_current_ankimorphs_version(self) -> None:
        self.setValue(keys.General.ANKIMORPHS_VERSION, ankimorphs_globals.__version__)

    def save_generators_window_settings(
        self, ui: Ui_GeneratorsWindow, geometry: QByteArray
    ) -> None:
        # fmt: off
        self.beginGroup(keys.Dialogs.GENERATORS_WINDOW)
        self.setValue(GeneratorsWindowKeys.WINDOW_GEOMETRY, geometry)
        self.setValue(GeneratorsWindowKeys.MORPHEMIZER, ui.morphemizerComboBox.currentText())
        self.setValue(GeneratorsWindowKeys.INPUT_DIR, ui.inputDirLineEdit.text())

        self.beginGroup(GeneratorsWindowKeys.FILE_FORMATS)
        self.setValue(FileFormatsKeys.ASS, ui.assFilesCheckBox.isChecked())
        self.setValue(FileFormatsKeys.EPUB, ui.epubFilesCheckBox.isChecked())
        self.setValue(FileFormatsKeys.HTML, ui.htmlFilesCheckBox.isChecked())
        self.setValue(FileFormatsKeys.MD, ui.mdFilesCheckBox.isChecked())
        self.setValue(FileFormatsKeys.SRT, ui.srtFilesCheckBox.isChecked())
        self.setValue(FileFormatsKeys.TXT, ui.txtFilesCheckBox.isChecked())
        self.setValue(FileFormatsKeys.VTT, ui.vttFilesCheckBox.isChecked())
        self.endGroup()  # file format group

        self.beginGroup(GeneratorsWindowKeys.PREPROCESS)
        self.setValue(PreprocessKeys.IGNORE_SQUARE_BRACKETS, ui.squareBracketsCheckBox.isChecked())
        self.setValue(PreprocessKeys.IGNORE_ROUND_BRACKETS, ui.roundBracketsCheckBox.isChecked())
        self.setValue(PreprocessKeys.IGNORE_SLIM_ROUND_BRACKETS, ui.slimRoundBracketsCheckBox.isChecked())
        self.setValue(PreprocessKeys.IGNORE_NAMES_MORPHEMIZER, ui.namesMorphemizerCheckBox.isChecked())
        self.setValue(PreprocessKeys.IGNORE_NAMES_IN_FILE, ui.namesFileCheckBox.isChecked())
        self.setValue(PreprocessKeys.IGNORE_NUMBERS, ui.numbersCheckBox.isChecked())
        self.endGroup()  # preprocess group
        self.endGroup()  # generators window group
        # fmt: on

    def save_known_morphs_exporter_settings(
        self, ui: Ui_KnownMorphsExporterDialog, geometry: QByteArray
    ) -> None:
        # fmt: off
        self.beginGroup(keys.Dialogs.KNOWN_MORPHS_EXPORTER)
        self.setValue(KnownMorphsExporterKeys.WINDOW_GEOMETRY, geometry)
        self.setValue(KnownMorphsExporterKeys.OUTPUT_DIR, ui.outputLineEdit.text())
        self.setValue(KnownMorphsExporterKeys.LEMMA, ui.storeOnlyMorphLemmaRadioButton.isChecked())
        self.setValue(KnownMorphsExporterKeys.INFLECTION, ui.storeMorphLemmaAndInflectionRadioButton.isChecked())
        self.setValue(KnownMorphsExporterKeys.INTERVAL, ui.knownIntervalSpinBox.value())
        self.setValue(KnownMorphsExporterKeys.OCCURRENCES, ui.addOccurrencesColumnCheckBox.isChecked())
        self.endGroup()
        # fmt: on

    def save_progression_window_settings(
        self, ui: Ui_ProgressionWindow, geometry: QByteArray
    ) -> None:
        # fmt: off
        self.beginGroup(keys.Dialogs.PROGRESSION_WINDOW)
        self.setValue(KnownMorphsExporterKeys.WINDOW_GEOMETRY, geometry)
        self.setValue(ProgressionWindowKeys.PRIORITY_FILE, ui.morphPriorityCBox.currentText())
        self.setValue(ProgressionWindowKeys.LEMMA_EVALUATION, ui.lemmaRadioButton.isChecked())
        self.setValue(ProgressionWindowKeys.INFLECTION_EVALUATION, ui.inflectionRadioButton.isChecked())
        self.setValue(ProgressionWindowKeys.PRIORITY_RANGE_START, ui.minPrioritySpinBox.value())
        self.setValue(ProgressionWindowKeys.PRIORITY_RANGE_END, ui.maxPrioritySpinBox.value())
        self.setValue(ProgressionWindowKeys.BIN_SIZE, ui.binSizeSpinBox.value())
        self.setValue(ProgressionWindowKeys.BIN_TYPE_NORMAL, ui.normalRadioButton.isChecked())
        self.setValue(ProgressionWindowKeys.BIN_TYPE_CUMULATIVE, ui.cumulativeRadioButton.isChecked())
        self.endGroup()
        # fmt: on

    def save_generator_priority_file_settings(
        self, ui: Ui_GeneratorOutputDialog, geometry: QByteArray
    ) -> None:
        # fmt: off
        self.beginGroup(keys.Dialogs.GENERATOR_OUTPUT_PRIORITY_FILE)
        self.setValue(GeneratorsOutputKeys.WINDOW_GEOMETRY, geometry)
        self.setValue(GeneratorsOutputKeys.OUTPUT_FILE_PATH, ui.outputLineEdit.text())
        self.setValue(GeneratorsOutputKeys.LEMMA_FORMAT, ui.storeOnlyMorphLemmaRadioButton.isChecked())
        self.setValue(GeneratorsOutputKeys.INFLECTION_FORMAT, ui.storeMorphLemmaAndInflectionRadioButton.isChecked())
        self.setValue(GeneratorsOutputKeys.MIN_OCCURRENCE_SELECTED, ui.minOccurrenceRadioButton.isChecked())
        self.setValue(GeneratorsOutputKeys.MIN_OCCURRENCE_CUTOFF, ui.minOccurrenceSpinBox.value())
        self.setValue(GeneratorsOutputKeys.COMPREHENSION_SELECTED, ui.comprehensionRadioButton.isChecked())
        self.setValue(GeneratorsOutputKeys.COMPREHENSION_CUTOFF, ui.comprehensionSpinBox.value())
        self.setValue(GeneratorsOutputKeys.OCCURRENCES_COLUMN_SELECTED, ui.addOccurrencesColumnCheckBox.isChecked())
        self.endGroup()
        # fmt: on

    def save_generator_study_plan_settings(
        self, ui: Ui_GeneratorOutputDialog, geometry: QByteArray
    ) -> None:
        # fmt: off
        self.beginGroup(keys.Dialogs.GENERATOR_OUTPUT_STUDY_PLAN)
        self.setValue(GeneratorsOutputKeys.WINDOW_GEOMETRY, geometry)
        self.setValue(GeneratorsOutputKeys.OUTPUT_FILE_PATH, ui.outputLineEdit.text())
        self.setValue(GeneratorsOutputKeys.LEMMA_FORMAT, ui.storeOnlyMorphLemmaRadioButton.isChecked())
        self.setValue(GeneratorsOutputKeys.INFLECTION_FORMAT, ui.storeMorphLemmaAndInflectionRadioButton.isChecked())
        self.setValue(GeneratorsOutputKeys.MIN_OCCURRENCE_SELECTED, ui.minOccurrenceRadioButton.isChecked())
        self.setValue(GeneratorsOutputKeys.MIN_OCCURRENCE_CUTOFF, ui.minOccurrenceSpinBox.value())
        self.setValue(GeneratorsOutputKeys.COMPREHENSION_SELECTED, ui.comprehensionRadioButton.isChecked())
        self.setValue(GeneratorsOutputKeys.COMPREHENSION_CUTOFF, ui.comprehensionSpinBox.value())
        self.setValue(GeneratorsOutputKeys.OCCURRENCES_COLUMN_SELECTED, ui.addOccurrencesColumnCheckBox.isChecked())
        self.endGroup()
        # fmt: on
