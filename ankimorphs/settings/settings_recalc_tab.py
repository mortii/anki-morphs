from __future__ import annotations

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class RecalcTab(AbstractSettingsTab):

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
        self.ui.recalcIntervalSpinBox.setValue(self._config.recalc_interval_for_known)
        self.ui.dueOffsetSpinBox.setValue(self._config.recalc_due_offset)
        self.ui.offsetFirstMorphsSpinBox.setValue(
            self._config.recalc_number_of_morphs_to_offset
        )

        self.ui.recalcBeforeSyncCheckBox.setChecked(self._config.recalc_on_sync)
        self.ui.recalcSuspendKnownCheckBox.setChecked(
            self._config.recalc_suspend_known_new_cards
        )
        self.ui.recalcMoveKnownNewCardsToTheEndCheckBox.setChecked(
            self._config.recalc_move_known_new_cards_to_the_end
        )
        self.ui.recalcReadKnownMorphsFolderCheckBox.setChecked(
            self._config.recalc_read_known_morphs_folder
        )
        self.ui.toolbarStatsUseSeenRadioButton.setChecked(
            self._config.recalc_toolbar_stats_use_seen
        )
        self.ui.toolbarStatsUseKnownRadioButton.setChecked(
            self._config.recalc_toolbar_stats_use_known
        )
        self.ui.unknownsFieldShowsInflectionsRadioButton.setChecked(
            self._config.recalc_unknowns_field_shows_inflections
        )
        self.ui.unknownsFieldShowsLemmasRadioButton.setChecked(
            self._config.recalc_unknowns_field_shows_lemmas
        )
        self.ui.shiftNewCardsCheckBox.setChecked(self._config.recalc_offset_new_cards)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default recalc settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        self.ui.recalcIntervalSpinBox.setValue(
            self._default_config.recalc_interval_for_known
        )
        self.ui.dueOffsetSpinBox.setValue(self._default_config.recalc_due_offset)
        self.ui.offsetFirstMorphsSpinBox.setValue(
            self._default_config.recalc_number_of_morphs_to_offset
        )

        self.ui.recalcBeforeSyncCheckBox.setChecked(self._default_config.recalc_on_sync)
        self.ui.recalcSuspendKnownCheckBox.setChecked(
            self._default_config.recalc_suspend_known_new_cards
        )
        self.ui.recalcMoveKnownNewCardsToTheEndCheckBox.setChecked(
            self._default_config.recalc_move_known_new_cards_to_the_end
        )
        self.ui.recalcReadKnownMorphsFolderCheckBox.setChecked(
            self._default_config.recalc_read_known_morphs_folder
        )
        self.ui.toolbarStatsUseSeenRadioButton.setChecked(
            self._default_config.recalc_toolbar_stats_use_seen
        )
        self.ui.toolbarStatsUseKnownRadioButton.setChecked(
            self._default_config.recalc_toolbar_stats_use_known
        )
        self.ui.unknownsFieldShowsInflectionsRadioButton.setChecked(
            self._default_config.recalc_unknowns_field_shows_inflections
        )
        self.ui.unknownsFieldShowsLemmasRadioButton.setChecked(
            self._default_config.recalc_unknowns_field_shows_lemmas
        )
        self.ui.shiftNewCardsCheckBox.setChecked(
            self._default_config.recalc_offset_new_cards
        )
