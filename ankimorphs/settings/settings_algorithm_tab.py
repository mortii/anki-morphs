from __future__ import annotations

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class AlgorithmTab(AbstractSettingsTab):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ):
        self._parent = parent
        self.ui = ui
        self._config = config
        self._default_config = default_config

    def populate(self) -> None:

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

        self.ui.totalPriorityUknownMorphsSpinBox.setValue(
            self._config.algorithm_total_priority_unknown_morphs
        )
        self.ui.totalPriorityAllMorphsSpinBox.setValue(
            self._config.algorithm_total_priority_all_morphs
        )
        self.ui.averagePriorityAllMorphsSpinBox.setValue(
            self._config.algorithm_average_priority_all_morphs
        )
        self.ui.allMorphsTargetDistanceSpinBox.setValue(
            self._config.algorithm_all_morphs_target_distance
        )
        self.ui.learningMorphsTargetDistanceSpinBox.setValue(
            self._config.algorithm_learning_morphs_target_distance
        )
        self.ui.upperTargetAllMorphsSpinBox.setValue(
            self._config.algorithm_upper_target_all_morphs
        )
        self.ui.lowerTargetAllMorphsSpinBox.setValue(
            self._config.algorithm_lower_target_all_morphs
        )
        self.ui.upperTargetAllMorphsCoefficientA.setValue(
            self._config.algorithm_upper_target_all_morphs_coefficient_a
        )
        self.ui.upperTargetAllMorphsCoefficientB.setValue(
            self._config.algorithm_upper_target_all_morphs_coefficient_b
        )
        self.ui.upperTargetAllMorphsCoefficientC.setValue(
            self._config.algorithm_upper_target_all_morphs_coefficient_c
        )
        self.ui.lowerTargetAllMorphsCoefficientA.setValue(
            self._config.algorithm_lower_target_all_morphs_coefficient_a
        )
        self.ui.lowerTargetAllMorphsCoefficientB.setValue(
            self._config.algorithm_lower_target_all_morphs_coefficient_b
        )
        self.ui.lowerTargetAllMorphsCoefficientC.setValue(
            self._config.algorithm_lower_target_all_morphs_coefficient_c
        )
        self.ui.upperTargetLearningMorphsSpinBox.setValue(
            self._config.algorithm_upper_target_learning_morphs
        )
        self.ui.lowerTargetLearningMorphsSpinBox.setValue(
            self._config.algorithm_lower_target_learning_morphs
        )
        self.ui.upperTargetLearningMorphsCoefficientA.setValue(
            self._config.algorithm_upper_target_learning_morphs_coefficient_a
        )
        self.ui.upperTargetLearningMorphsCoefficientB.setValue(
            self._config.algorithm_upper_target_learning_morphs_coefficient_b
        )
        self.ui.upperTargetLearningMorphsCoefficientC.setValue(
            self._config.algorithm_upper_target_learning_morphs_coefficient_c
        )
        self.ui.lowerTargetLearningMorphsCoefficientA.setValue(
            self._config.algorithm_lower_target_learning_morphs_coefficient_a
        )
        self.ui.lowerTargetLearningMorphsCoefficientB.setValue(
            self._config.algorithm_lower_target_learning_morphs_coefficient_b
        )
        self.ui.lowerTargetLearningMorphsCoefficientC.setValue(
            self._config.algorithm_lower_target_learning_morphs_coefficient_c
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

        self.ui.totalPriorityUknownMorphsSpinBox.setValue(
            self._default_config.algorithm_total_priority_unknown_morphs
        )
        self.ui.totalPriorityAllMorphsSpinBox.setValue(
            self._default_config.algorithm_total_priority_all_morphs
        )
        self.ui.averagePriorityAllMorphsSpinBox.setValue(
            self._default_config.algorithm_average_priority_all_morphs
        )

        self.ui.allMorphsTargetDistanceSpinBox.setValue(
            self._default_config.algorithm_all_morphs_target_distance
        )
        self.ui.learningMorphsTargetDistanceSpinBox.setValue(
            self._default_config.algorithm_learning_morphs_target_distance
        )

        self.ui.upperTargetAllMorphsSpinBox.setValue(
            self._default_config.algorithm_upper_target_all_morphs
        )
        self.ui.lowerTargetAllMorphsSpinBox.setValue(
            self._default_config.algorithm_lower_target_all_morphs
        )

        self.ui.upperTargetAllMorphsCoefficientA.setValue(
            self._default_config.algorithm_upper_target_all_morphs_coefficient_a
        )
        self.ui.upperTargetAllMorphsCoefficientB.setValue(
            self._default_config.algorithm_upper_target_all_morphs_coefficient_b
        )
        self.ui.upperTargetAllMorphsCoefficientC.setValue(
            self._default_config.algorithm_upper_target_all_morphs_coefficient_c
        )

        self.ui.lowerTargetAllMorphsCoefficientA.setValue(
            self._default_config.algorithm_lower_target_all_morphs_coefficient_a
        )
        self.ui.lowerTargetAllMorphsCoefficientB.setValue(
            self._default_config.algorithm_lower_target_all_morphs_coefficient_b
        )
        self.ui.lowerTargetAllMorphsCoefficientC.setValue(
            self._default_config.algorithm_lower_target_all_morphs_coefficient_c
        )

        self.ui.upperTargetLearningMorphsSpinBox.setValue(
            self._default_config.algorithm_upper_target_learning_morphs
        )
        self.ui.lowerTargetLearningMorphsSpinBox.setValue(
            self._default_config.algorithm_lower_target_learning_morphs
        )

        self.ui.upperTargetLearningMorphsCoefficientA.setValue(
            self._default_config.algorithm_upper_target_learning_morphs_coefficient_a
        )
        self.ui.upperTargetLearningMorphsCoefficientB.setValue(
            self._default_config.algorithm_upper_target_learning_morphs_coefficient_b
        )
        self.ui.upperTargetLearningMorphsCoefficientC.setValue(
            self._default_config.algorithm_upper_target_learning_morphs_coefficient_c
        )

        self.ui.lowerTargetLearningMorphsCoefficientA.setValue(
            self._default_config.algorithm_lower_target_learning_morphs_coefficient_a
        )
        self.ui.lowerTargetLearningMorphsCoefficientB.setValue(
            self._default_config.algorithm_lower_target_learning_morphs_coefficient_b
        )
        self.ui.lowerTargetLearningMorphsCoefficientC.setValue(
            self._default_config.algorithm_lower_target_learning_morphs_coefficient_c
        )

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            "algorithm_total_priority_unknown_morphs": self.ui.totalPriorityUknownMorphsSpinBox.value(),
            "algorithm_total_priority_all_morphs": self.ui.totalPriorityAllMorphsSpinBox.value(),
            "algorithm_average_priority_all_morphs": self.ui.averagePriorityAllMorphsSpinBox.value(),
            "algorithm_all_morphs_target_distance": self.ui.allMorphsTargetDistanceSpinBox.value(),
            "algorithm_learning_morphs_target_distance": self.ui.learningMorphsTargetDistanceSpinBox.value(),
            "algorithm_upper_target_all_morphs": self.ui.upperTargetAllMorphsSpinBox.value(),
            "algorithm_upper_target_all_morphs_coefficient_a": self.ui.upperTargetAllMorphsCoefficientA.value(),
            "algorithm_upper_target_all_morphs_coefficient_b": self.ui.upperTargetAllMorphsCoefficientB.value(),
            "algorithm_upper_target_all_morphs_coefficient_c": self.ui.upperTargetAllMorphsCoefficientC.value(),
            "algorithm_lower_target_all_morphs": self.ui.lowerTargetAllMorphsSpinBox.value(),
            "algorithm_lower_target_all_morphs_coefficient_a": self.ui.lowerTargetAllMorphsCoefficientA.value(),
            "algorithm_lower_target_all_morphs_coefficient_b": self.ui.lowerTargetAllMorphsCoefficientB.value(),
            "algorithm_lower_target_all_morphs_coefficient_c": self.ui.lowerTargetAllMorphsCoefficientC.value(),
            "algorithm_upper_target_learning_morphs": self.ui.upperTargetLearningMorphsSpinBox.value(),
            "algorithm_lower_target_learning_morphs": self.ui.lowerTargetLearningMorphsSpinBox.value(),
            "algorithm_upper_target_learning_morphs_coefficient_a": self.ui.upperTargetLearningMorphsCoefficientA.value(),
            "algorithm_upper_target_learning_morphs_coefficient_b": self.ui.upperTargetLearningMorphsCoefficientB.value(),
            "algorithm_upper_target_learning_morphs_coefficient_c": self.ui.upperTargetLearningMorphsCoefficientC.value(),
            "algorithm_lower_target_learning_morphs_coefficient_a": self.ui.lowerTargetLearningMorphsCoefficientA.value(),
            "algorithm_lower_target_learning_morphs_coefficient_b": self.ui.lowerTargetLearningMorphsCoefficientB.value(),
            "algorithm_lower_target_learning_morphs_coefficient_c": self.ui.lowerTargetLearningMorphsCoefficientC.value(),
        }
