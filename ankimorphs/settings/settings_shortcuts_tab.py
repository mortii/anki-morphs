from __future__ import annotations

from aqt.qt import QDialog, QKeySequenceEdit  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_tab import SettingsTab


class ShortcutTab(SettingsTab):
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
            RawConfigKeys.SHORTCUT_PROGRESSION: self.ui.shortcutProgressionKeySequenceEdit,
            RawConfigKeys.SHORTCUT_KNOWN_MORPHS_EXPORTER: self.ui.shortcutKnownMorphsExporterKeySequenceEdit,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def setup_buttons(self) -> None:
        self.ui.restoreShortcutsPushButton.setAutoDefault(False)
        self.ui.shortcutRecalcDisablePushButton.setAutoDefault(False)
        self.ui.shortcutSettingsDisablePushButton.setAutoDefault(False)
        self.ui.shortcutKnownAndSkipDisablePushButton.setAutoDefault(False)
        self.ui.shortcutLearnNowDisablePushButton.setAutoDefault(False)
        self.ui.shortcutViewMorphsDisablePushButton.setAutoDefault(False)
        self.ui.shortcutGeneratorsDisablePushButton.setAutoDefault(False)
        self.ui.shortcutProgressionDisablePushButton.setAutoDefault(False)
        self.ui.shortcutKnownMorphsExporterDisablePushButton.setAutoDefault(False)
        self.ui.shortcutBrowseReadyDisablePushButton.setAutoDefault(False)
        self.ui.shortcutBrowseAllDisablePushButton.setAutoDefault(False)
        self.ui.shortcutBrowseReadyLemmaDisablePushButton.setAutoDefault(False)

        self.ui.restoreShortcutsPushButton.clicked.connect(self.restore_defaults)

        self.ui.shortcutRecalcDisablePushButton.clicked.connect(
            self.ui.shortcutRecalcKeySequenceEdit.clear
        )
        self.ui.shortcutSettingsDisablePushButton.clicked.connect(
            self.ui.shortcutSettingsKeySequenceEdit.clear
        )
        self.ui.shortcutKnownAndSkipDisablePushButton.clicked.connect(
            self.ui.shortcutKnownAndSkipKeySequenceEdit.clear
        )
        self.ui.shortcutLearnNowDisablePushButton.clicked.connect(
            self.ui.shortcutLearnNowKeySequenceEdit.clear
        )
        self.ui.shortcutViewMorphsDisablePushButton.clicked.connect(
            self.ui.shortcutViewMorphsKeySequenceEdit.clear
        )
        self.ui.shortcutGeneratorsDisablePushButton.clicked.connect(
            self.ui.shortcutGeneratorsKeySequenceEdit.clear
        )
        self.ui.shortcutProgressionDisablePushButton.clicked.connect(
            self.ui.shortcutProgressionKeySequenceEdit.clear
        )
        self.ui.shortcutKnownMorphsExporterDisablePushButton.clicked.connect(
            self.ui.shortcutKnownMorphsExporterKeySequenceEdit.clear
        )
        self.ui.shortcutBrowseReadyDisablePushButton.clicked.connect(
            self.ui.shortcutBrowseReadyKeySequenceEdit.clear
        )
        self.ui.shortcutBrowseAllDisablePushButton.clicked.connect(
            self.ui.shortcutBrowseAllKeySequenceEdit.clear
        )
        self.ui.shortcutBrowseReadyLemmaDisablePushButton.clicked.connect(
            self.ui.shortcutBrowseReadyLemmaKeySequenceEdit.clear
        )

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default shortcuts settings?"
