from __future__ import annotations

from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QRadioButton,
    QSpinBox,
    Qt,
)

from .. import ankimorphs_globals as am_globals
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
            RawConfigKeys.SKIP_NO_UNKNOWN_MORPHS: self.ui.skipNoUnKnownMorphsCheckBox,
            RawConfigKeys.SKIP_UNKNOWN_MORPH_SEEN_TODAY_CARDS: self.ui.skipAlreadySeenCheckBox,
            RawConfigKeys.SKIP_SHOW_NUM_OF_SKIPPED_CARDS: self.ui.skipNotificationsCheckBox,
            RawConfigKeys.RECALC_OFFSET_NEW_CARDS: self.ui.shiftNewCardsCheckBox,
        }

        self._raw_config_key_to_spin_box: dict[str, QSpinBox | QDoubleSpinBox] = {
            RawConfigKeys.RECALC_DUE_OFFSET: self.ui.dueOffsetSpinBox,
            RawConfigKeys.RECALC_NUMBER_OF_MORPHS_TO_OFFSET: self.ui.offsetFirstMorphsSpinBox,
        }

        self._raw_config_key_to_combo_box: dict[str, QComboBox] = {
            RawConfigKeys.RECALC_SUSPEND_NEW_CARDS: self.ui.suspendNewCardsComboBox,
            RawConfigKeys.RECALC_MOVE_NEW_CARDS_TO_THE_END: self.ui.MoveNewCardsComboBox,
        }

        self._raw_config_key_to_radio_button: dict[str, QRadioButton] = {
            RawConfigKeys.SKIP_DONT_WHEN_CONTAINS_FRESH_MORPHS: self.ui.skipDontWhenFreshMorphsRadioButton,
            RawConfigKeys.SKIP_WHEN_CONTAINS_FRESH_MORPHS: self.ui.skipEvenWithFreshMorphsRadioButton,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def populate(self, use_default_config: bool = False) -> None:
        self._populate_combo_boxes()  # add items before running super populate
        super().populate(use_default_config)
        self._toggle_disable_shift_cards_settings()
        self._toggle_disable_skip_fresh_morphs_radio_buttons()

    def setup_buttons(self) -> None:
        self.ui.restoreCardHandlingPushButton.setAutoDefault(False)
        self.ui.restoreCardHandlingPushButton.clicked.connect(self.restore_defaults)

        self.ui.shiftNewCardsCheckBox.stateChanged.connect(
            self._toggle_disable_shift_cards_settings
        )
        self.ui.skipNoUnKnownMorphsCheckBox.stateChanged.connect(
            self._toggle_disable_skip_fresh_morphs_radio_buttons
        )

    def _populate_combo_boxes(self) -> None:
        items: list[str] = [
            am_globals.NEVER_OPTION,
            am_globals.ONLY_KNOWN_OPTION,
            am_globals.ONLY_KNOWN_OR_FRESH_OPTION,
        ]

        # populate can be called multiple times, so we have to clear
        self.ui.suspendNewCardsComboBox.clear()
        self.ui.MoveNewCardsComboBox.clear()

        self.ui.suspendNewCardsComboBox.addItems(items)
        self.ui.MoveNewCardsComboBox.addItems(items)

    def _toggle_disable_shift_cards_settings(self) -> None:
        if self.ui.shiftNewCardsCheckBox.checkState() == Qt.CheckState.Unchecked:
            self.ui.dueOffsetSpinBox.setDisabled(True)
            self.ui.offsetFirstMorphsSpinBox.setDisabled(True)
        else:
            self.ui.dueOffsetSpinBox.setEnabled(True)
            self.ui.offsetFirstMorphsSpinBox.setEnabled(True)

    def _toggle_disable_skip_fresh_morphs_radio_buttons(self) -> None:
        if self.ui.skipNoUnKnownMorphsCheckBox.checkState() == Qt.CheckState.Unchecked:
            self.ui.skipDontWhenFreshMorphsRadioButton.setDisabled(True)
            self.ui.skipEvenWithFreshMorphsRadioButton.setDisabled(True)
        else:
            self.ui.skipDontWhenFreshMorphsRadioButton.setEnabled(True)
            self.ui.skipEvenWithFreshMorphsRadioButton.setEnabled(True)

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default skip settings?"
