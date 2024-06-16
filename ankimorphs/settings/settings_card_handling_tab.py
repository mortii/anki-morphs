from __future__ import annotations

from aqt.qt import QDialog, Qt  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig
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
        self._parent = parent
        self.ui = ui
        self._config = config
        self._default_config = default_config

    def populate(self) -> None:
        self.ui.skipKnownCheckBox.setChecked(self._config.skip_only_known_morphs_cards)
        self.ui.skipAlreadySeenCheckBox.setChecked(
            self._config.skip_unknown_morph_seen_today_cards
        )
        self.ui.skipNotificationsCheckBox.setChecked(
            self._config.skip_show_num_of_skipped_cards
        )
        self.ui.recalcSuspendKnownCheckBox.setChecked(
            self._config.recalc_suspend_known_new_cards
        )
        self.ui.shiftNewCardsCheckBox.setChecked(self._config.recalc_offset_new_cards)
        self.ui.dueOffsetSpinBox.setValue(self._config.recalc_due_offset)
        self.ui.offsetFirstMorphsSpinBox.setValue(
            self._config.recalc_number_of_morphs_to_offset
        )
        self.ui.recalcMoveKnownNewCardsToTheEndCheckBox.setChecked(
            self._config.recalc_move_known_new_cards_to_the_end
        )

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

        self.ui.skipKnownCheckBox.setChecked(
            self._default_config.skip_only_known_morphs_cards
        )
        self.ui.skipAlreadySeenCheckBox.setChecked(
            self._default_config.skip_unknown_morph_seen_today_cards
        )
        self.ui.skipNotificationsCheckBox.setChecked(
            self._default_config.skip_show_num_of_skipped_cards
        )
        self.ui.recalcSuspendKnownCheckBox.setChecked(
            self._default_config.recalc_suspend_known_new_cards
        )
        self.ui.shiftNewCardsCheckBox.setChecked(
            self._default_config.recalc_offset_new_cards
        )
        self.ui.dueOffsetSpinBox.setValue(self._default_config.recalc_due_offset)
        self.ui.offsetFirstMorphsSpinBox.setValue(
            self._default_config.recalc_number_of_morphs_to_offset
        )
        self.ui.recalcMoveKnownNewCardsToTheEndCheckBox.setChecked(
            self._default_config.recalc_move_known_new_cards_to_the_end
        )

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            "skip_only_known_morphs_cards": self.ui.skipKnownCheckBox.isChecked(),
            "skip_unknown_morph_seen_today_cards": self.ui.skipAlreadySeenCheckBox.isChecked(),
            "skip_show_num_of_skipped_cards": self.ui.skipNotificationsCheckBox.isChecked(),
            "recalc_suspend_known_new_cards": self.ui.recalcSuspendKnownCheckBox.isChecked(),
            "recalc_offset_new_cards": self.ui.shiftNewCardsCheckBox.isChecked(),
            "recalc_due_offset": self.ui.dueOffsetSpinBox.value(),
            "recalc_number_of_morphs_to_offset": self.ui.offsetFirstMorphsSpinBox.value(),
            "recalc_move_known_new_cards_to_the_end": self.ui.recalcMoveKnownNewCardsToTheEndCheckBox.isChecked(),
        }
