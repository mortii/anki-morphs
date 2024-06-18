from __future__ import annotations

from aqt.qt import QDialog, QKeySequenceEdit  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class ShortcutTab(AbstractSettingsTab):
    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_key_sequence: dict[str, QKeySequenceEdit] = {
            RawConfigKeys.SHORTCUT_RECALC: self.ui.shortcutRecalcKeySequenceEdit,
            RawConfigKeys.SHORTCUT_SETTINGS: self.ui.shortcutSettingsKeySequenceEdit,
            RawConfigKeys.SHORTCUT_BROWSE_READY_SAME_UNKNOWN: self.ui.shortcutBrowseReadyKeySequenceEdit,
            RawConfigKeys.SHORTCUT_BROWSE_ALL_SAME_UNKNOWN: self.ui.shortcutBrowseAllKeySequenceEdit,
            RawConfigKeys.SHORTCUT_BROWSE_READY_SAME_UNKNOWN_LEMMA: self.ui.shortcutBrowseReadyLemmaKeySequenceEdit,
            RawConfigKeys.SHORTCUT_SET_KNOWN_AND_SKIP: self.ui.shortcutKnownAndSkipKeySequenceEdit,
            RawConfigKeys.SHORTCUT_LEARN_NOW: self.ui.shortcutLearnNowKeySequenceEdit,
            RawConfigKeys.SHORTCUT_VIEW_MORPHEMES: self.ui.shortcutViewMorphsKeySequenceEdit,
            RawConfigKeys.SHORTCUT_GENERATORS: self.ui.shortcutGeneratorsKeySequenceEdit,
            RawConfigKeys.SHORTCUT_KNOWN_MORPHS_EXPORTER: self.ui.shortcutKnownMorphsExporterKeySequenceEdit,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def setup_buttons(self) -> None:
        self.ui.restoreShortcutsPushButton.setAutoDefault(False)
        self.ui.restoreShortcutsPushButton.clicked.connect(self.restore_defaults)

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default shortcuts settings?"
