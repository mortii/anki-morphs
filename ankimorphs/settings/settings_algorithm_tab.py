from __future__ import annotations

from aqt.qt import QDialog, QSpinBox  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class AlgorithmTab(AbstractSettingsTab):
    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_spin_box: dict[str, QSpinBox] = {
            RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_UNKNOWN_MORPHS: self.ui.totalPriorityUknownMorphsSpinBox,
            RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_ALL_MORPHS: self.ui.totalPriorityAllMorphsSpinBox,
            RawConfigKeys.ALGORITHM_AVERAGE_PRIORITY_ALL_MORPHS: self.ui.averagePriorityAllMorphsSpinBox,
            RawConfigKeys.ALGORITHM_ALL_MORPHS_TARGET_DISTANCE: self.ui.allMorphsTargetDistanceSpinBox,
            RawConfigKeys.ALGORITHM_LEARNING_MORPHS_TARGET_DISTANCE: self.ui.learningMorphsTargetDistanceSpinBox,
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

    def populate(self) -> None:
        super().populate()

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
