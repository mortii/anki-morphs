from __future__ import annotations

from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QRadioButton,
    QSpinBox,
)

from .. import tags_and_queue_utils
from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_tab import SettingsTab


class GeneralTab(SettingsTab):
    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_radio_button: dict[str, QRadioButton] = {
            RawConfigKeys.EVALUATE_MORPH_LEMMA: self.ui.priorityLemmaRadioButton,
            RawConfigKeys.EVALUATE_MORPH_INFLECTION: self.ui.priorityInflectionRadioButton,
        }

        self._raw_config_key_to_check_box: dict[str, QCheckBox] = {
            RawConfigKeys.RECALC_ON_SYNC: self.ui.recalcBeforeSyncCheckBox,
            RawConfigKeys.READ_KNOWN_MORPHS_FOLDER: self.ui.recalcReadKnownMorphsFolderCheckBox,
        }

        self._raw_config_key_to_spin_box: dict[str, QSpinBox | QDoubleSpinBox] = {
            RawConfigKeys.INTERVAL_FOR_KNOWN_MORPHS: self.ui.recalcIntervalSpinBox,
        }

        self.previous_priority_selection: QRadioButton | None = None

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def populate(self, use_default_config: bool = False) -> None:
        super().populate()
        if self.ui.priorityLemmaRadioButton.isChecked():
            self.previous_priority_selection = self.ui.priorityLemmaRadioButton
        else:
            self.previous_priority_selection = self.ui.priorityInflectionRadioButton

    def setup_buttons(self) -> None:
        self.ui.restoreGeneralPushButton.setAutoDefault(False)
        self.ui.restoreGeneralPushButton.clicked.connect(self.restore_defaults)

        self.ui.priorityLemmaRadioButton.toggled.connect(
            self.on_priority_radio_button_toggled
        )
        self.ui.priorityInflectionRadioButton.toggled.connect(
            self.on_priority_radio_button_toggled
        )

    def on_priority_radio_button_toggled(self) -> None:
        if (
            self.ui.priorityInflectionRadioButton.isChecked()
            and self.previous_priority_selection == self.ui.priorityLemmaRadioButton
        ):
            reason_to_reset = "morph evaluation from 'lemma' to 'inflection'"
            if self._want_to_reset_am_tags(reason_to_reset):
                tags_and_queue_utils.reset_am_tags(parent=self._parent)

        if self.ui.priorityLemmaRadioButton.isChecked():
            self.previous_priority_selection = self.ui.priorityLemmaRadioButton
        elif self.ui.priorityInflectionRadioButton.isChecked():
            self.previous_priority_selection = self.ui.priorityInflectionRadioButton

    def restore_to_config_state(self) -> None:
        # prevent the "reset tags?" dialog displaying when we discard changes
        self.ui.priorityLemmaRadioButton.blockSignals(True)
        self.ui.priorityInflectionRadioButton.blockSignals(True)

        self.populate()

        self.ui.priorityLemmaRadioButton.blockSignals(False)
        self.ui.priorityInflectionRadioButton.blockSignals(False)

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default general settings?"
