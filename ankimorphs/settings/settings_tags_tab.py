from __future__ import annotations

from aqt.qt import QDialog, QLineEdit  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_tab import SettingsTab


class TagsTab(SettingsTab):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_line_edit: dict[str, QLineEdit] = {
            RawConfigKeys.TAG_FRESH: self.ui.tagfreshLineEdit,
            RawConfigKeys.TAG_READY: self.ui.tagReadyLineEdit,
            RawConfigKeys.TAG_NOT_READY: self.ui.tagNotReadyLineEdit,
            RawConfigKeys.TAG_KNOWN_AUTOMATICALLY: self.ui.tagKnownAutomaticallyLineEdit,
            RawConfigKeys.TAG_KNOWN_MANUALLY: self.ui.tagKnownManuallyLineEdit,
            RawConfigKeys.TAG_LEARN_CARD_NOW: self.ui.tagLearnCardNowLineEdit,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def setup_buttons(self) -> None:
        self.ui.restoreTagsPushButton.setAutoDefault(False)
        self.ui.restoreTagsPushButton.clicked.connect(self.restore_defaults)

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default tags settings?"
