from __future__ import annotations

from aqt.qt import QDialog, QSpinBox  # pylint:disable=no-name-in-module

from .. import message_box_utils
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
        self._previous_state = self.settings_to_dict()

    def populate(self) -> None:
        for config_attribute, spin_box in self._raw_config_key_to_spin_box.items():
            value = getattr(self._config, config_attribute)
            spin_box.setValue(value)

        # making sure the lower values are always smaller the upper ones
        self.ui.lowerTargetAllMorphsSpinBox.setMaximum(
            self.ui.upperTargetAllMorphsSpinBox.value()
        )
        self.ui.lowerTargetLearningMorphsSpinBox.setMaximum(
            self.ui.upperTargetLearningMorphsSpinBox.value()
        )

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

    def setup_buttons(self) -> None:
        self.ui.restoreAlgorithmPushButton.setAutoDefault(False)
        self.ui.restoreAlgorithmPushButton.clicked.connect(self.restore_defaults)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default algorithm settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        for config_attribute, spin_box in self._raw_config_key_to_spin_box.items():
            value = getattr(self._default_config, config_attribute)
            spin_box.setValue(value)

    def restore_to_config_state(self) -> None:
        assert self._previous_state is not None

        for config_key, spin_box in self._raw_config_key_to_spin_box.items():
            previous_value = self._previous_state[config_key]
            assert isinstance(previous_value, int)
            spin_box.setValue(previous_value)

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            config_key: spin_box.value()
            for config_key, spin_box in self._raw_config_key_to_spin_box.items()
        }
