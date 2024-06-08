from __future__ import annotations

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class SkipTab(AbstractSettingsTab):
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
        self.ui.skipKnownCheckBox.setChecked(self._config.skip_only_known_morphs_cards)
        self.ui.skipAlreadySeenCheckBox.setChecked(
            self._config.skip_unknown_morph_seen_today_cards
        )
        self.ui.skipNotificationsCheckBox.setChecked(
            self._config.skip_show_num_of_skipped_cards
        )

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
