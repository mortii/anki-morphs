from __future__ import annotations

from aqt.qt import QDialog, QDoubleSpinBox, QSpinBox  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_tab import SettingsTab


class AlgorithmTab(SettingsTab):
    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_spin_box: dict[str, QSpinBox | QDoubleSpinBox] = {
            RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_ALL_MORPHS_WEIGHT: self.ui.totalPriorityAllMorphsSpinBox,
            RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_UNKNOWN_MORPHS_WEIGHT: self.ui.totalPriorityUknownMorphsSpinBox,
            RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_LEARNING_MORPHS_WEIGHT: self.ui.totalPriorityLearningMorphsSpinBox,
            RawConfigKeys.ALGORITHM_AVERAGE_PRIORITY_ALL_MORPHS_WEIGHT: self.ui.averagePriorityAllMorphsSpinBox,
            RawConfigKeys.ALGORITHM_AVERAGE_PRIORITY_LEARNING_MORPHS_WEIGHT: self.ui.averagePriorityLearningMorphsSpinBox,
            RawConfigKeys.ALGORITHM_ALL_MORPHS_TARGET_DIFFERENCE_WEIGHT: self.ui.targetDifferenceAllMorphsSpinBox,
            RawConfigKeys.ALGORITHM_LEARNING_MORPHS_TARGET_DIFFERENCE_WEIGHT: self.ui.targetDifferenceLearningMorphsSpinBox,
            RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS: self.ui.upperTargetAllMorphsSpinBox,
            RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_A: self.ui.upperTargetAllMorphsCoefficientA,
            RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_B: self.ui.upperTargetAllMorphsCoefficientB,
            RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_C: self.ui.upperTargetAllMorphsCoefficientC,
            RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS: self.ui.lowerTargetAllMorphsSpinBox,
            RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_A: self.ui.lowerTargetAllMorphsCoefficientA,
            RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_B: self.ui.lowerTargetAllMorphsCoefficientB,
            RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_C: self.ui.lowerTargetAllMorphsCoefficientC,
            RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS: self.ui.upperTargetLearningMorphsSpinBox,
            RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS: self.ui.lowerTargetLearningMorphsSpinBox,
            RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_A: self.ui.upperTargetLearningMorphsCoefficientA,
            RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_B: self.ui.upperTargetLearningMorphsCoefficientB,
            RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_C: self.ui.upperTargetLearningMorphsCoefficientC,
            RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_A: self.ui.lowerTargetLearningMorphsCoefficientA,
            RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_B: self.ui.lowerTargetLearningMorphsCoefficientB,
            RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_C: self.ui.lowerTargetLearningMorphsCoefficientC,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def populate(self, use_default_config: bool = False) -> None:
        super().populate(use_default_config)

        # making sure the lower values are always smaller the upper ones
        self.ui.lowerTargetAllMorphsSpinBox.setMaximum(
            self.ui.upperTargetAllMorphsSpinBox.value()
        )
        self.ui.lowerTargetLearningMorphsSpinBox.setMaximum(
            self.ui.upperTargetLearningMorphsSpinBox.value()
        )

    def setup_buttons(self) -> None:
        self.ui.restoreAlgorithmPushButton.setAutoDefault(False)
        self.ui.restoreAlgorithmPushButton.clicked.connect(self.restore_defaults)

        # making sure the lower values are always smaller the upper ones
        self.ui.upperTargetAllMorphsSpinBox.valueChanged.connect(
            lambda: self.ui.lowerTargetAllMorphsSpinBox.setMaximum(
                self.ui.upperTargetAllMorphsSpinBox.value()
            )
        )

        self.ui.upperTargetLearningMorphsSpinBox.valueChanged.connect(
            lambda: self.ui.lowerTargetLearningMorphsSpinBox.setMaximum(
                self.ui.upperTargetLearningMorphsSpinBox.value()
            )
        )

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default algorithm settings?"
