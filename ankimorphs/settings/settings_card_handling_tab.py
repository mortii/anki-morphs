from __future__ import annotations

from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QSpinBox,
    Qt,
)

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_tab import SettingsTab


class CardHandlingTab(SettingsTab):
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

        self._raw_config_key_to_spin_box: dict[str, QSpinBox | QDoubleSpinBox] = {
            RawConfigKeys.RECALC_DUE_OFFSET: self.ui.dueOffsetSpinBox,
            RawConfigKeys.RECALC_NUMBER_OF_MORPHS_TO_OFFSET: self.ui.offsetFirstMorphsSpinBox,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def populate(self, use_default_config: bool = False) -> None:
        super().populate(use_default_config)
        self._toggle_disable_shift_cards_settings()

    def setup_buttons(self) -> None:
        self.ui.restoreCardHandlingPushButton.setAutoDefault(False)
        self.ui.restoreCardHandlingPushButton.clicked.connect(self.restore_defaults)

        self.ui.shiftNewCardsCheckBox.stateChanged.connect(
            self._toggle_disable_shift_cards_settings
        )

    def _toggle_disable_shift_cards_settings(self) -> None:
        if self.ui.shiftNewCardsCheckBox.checkState() == Qt.CheckState.Unchecked:
            self.ui.dueOffsetSpinBox.setDisabled(True)
            self.ui.offsetFirstMorphsSpinBox.setDisabled(True)
        else:
            self.ui.dueOffsetSpinBox.setEnabled(True)
            self.ui.offsetFirstMorphsSpinBox.setEnabled(True)

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default skip settings?"
