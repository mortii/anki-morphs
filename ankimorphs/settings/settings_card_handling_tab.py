from __future__ import annotations

from aqt.qt import QCheckBox, QDialog, QSpinBox, Qt  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class CardHandlingTab(AbstractSettingsTab):
    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_check_box: dict[str, QCheckBox] = {
            RawConfigKeys.SKIP_ONLY_KNOWN_MORPHS_CARDS: self.ui.skipKnownCheckBox,
            RawConfigKeys.SKIP_UNKNOWN_MORPH_SEEN_TODAY_CARDS: self.ui.skipAlreadySeenCheckBox,
            RawConfigKeys.SKIP_SHOW_NUM_OF_SKIPPED_CARDS: self.ui.skipNotificationsCheckBox,
            RawConfigKeys.RECALC_SUSPEND_KNOWN_NEW_CARDS: self.ui.recalcSuspendKnownCheckBox,
            RawConfigKeys.RECALC_OFFSET_NEW_CARDS: self.ui.shiftNewCardsCheckBox,
            RawConfigKeys.RECALC_MOVE_KNOWN_NEW_CARDS_TO_THE_END: self.ui.recalcMoveKnownNewCardsToTheEndCheckBox,
        }

        self._raw_config_key_to_spin_box: dict[str, QSpinBox] = {
            RawConfigKeys.RECALC_DUE_OFFSET: self.ui.dueOffsetSpinBox,
            RawConfigKeys.RECALC_NUMBER_OF_MORPHS_TO_OFFSET: self.ui.offsetFirstMorphsSpinBox,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def populate(self) -> None:
        for config_attribute, checkbox in self._raw_config_key_to_check_box.items():
            is_checked = getattr(self._config, config_attribute)
            checkbox.setChecked(is_checked)

        for config_attribute, spin_box in self._raw_config_key_to_spin_box.items():
            value = getattr(self._config, config_attribute)
            spin_box.setValue(value)

        self._toggle_disable_shift_cards_settings(
            check_state=self.ui.shiftNewCardsCheckBox.checkState()
        )

    def setup_buttons(self) -> None:
        self.ui.restoreCardHandlingPushButton.setAutoDefault(False)
        self.ui.restoreCardHandlingPushButton.clicked.connect(self.restore_defaults)

        self.ui.shiftNewCardsCheckBox.checkStateChanged.connect(
            self._toggle_disable_shift_cards_settings
        )

    def _toggle_disable_shift_cards_settings(self, check_state: Qt.CheckState) -> None:
        if check_state == Qt.CheckState.Unchecked:
            self.ui.dueOffsetSpinBox.setDisabled(True)
            self.ui.offsetFirstMorphsSpinBox.setDisabled(True)
        else:
            self.ui.dueOffsetSpinBox.setEnabled(True)
            self.ui.offsetFirstMorphsSpinBox.setEnabled(True)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default skip settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        for config_attribute, spin_box in self._raw_config_key_to_spin_box.items():
            value = getattr(self._default_config, config_attribute)
            spin_box.setValue(value)

        for config_attribute, checkbox in self._raw_config_key_to_check_box.items():
            is_checked = getattr(self._default_config, config_attribute)
            checkbox.setChecked(is_checked)

    def restore_to_config_state(self) -> None:
        assert self._previous_state is not None

        for config_key, spin_box in self._raw_config_key_to_spin_box.items():
            previous_value = self._previous_state[config_key]
            assert isinstance(previous_value, int)
            spin_box.setValue(previous_value)

        for config_key, checkbox in self._raw_config_key_to_check_box.items():
            previous_check_state = self._previous_state[config_key]
            assert isinstance(previous_check_state, bool)
            checkbox.setChecked(previous_check_state)

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        spin_box_settings = {
            config_key: spin_box.value()
            for config_key, spin_box in self._raw_config_key_to_spin_box.items()
        }
        check_box_settings = {
            config_key: checkbox.isChecked()
            for config_key, checkbox in self._raw_config_key_to_check_box.items()
        }
        settings_dict: dict[str, str | int | bool | object] = {}
        settings_dict.update(spin_box_settings)
        settings_dict.update(check_box_settings)
        return settings_dict
