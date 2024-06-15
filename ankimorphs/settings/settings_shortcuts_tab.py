from __future__ import annotations

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class ShortcutTab(AbstractSettingsTab):

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
        self.ui.shortcutRecalcKeySequenceEdit.setKeySequence(
            self._config.shortcut_recalc
        )
        self.ui.shortcutSettingsKeySequenceEdit.setKeySequence(
            self._config.shortcut_settings
        )
        self.ui.shortcutBrowseReadyKeySequenceEdit.setKeySequence(
            self._config.shortcut_browse_ready_same_unknown.toString()
        )
        self.ui.shortcutBrowseAllKeySequenceEdit.setKeySequence(
            self._config.shortcut_browse_all_same_unknown.toString()
        )
        self.ui.shortcutBrowseReadyLemmaKeySequenceEdit.setKeySequence(
            self._config.shortcut_browse_ready_same_unknown_lemma.toString()
        )
        self.ui.shortcutKnownAndSkipKeySequenceEdit.setKeySequence(
            self._config.shortcut_set_known_and_skip.toString()
        )
        self.ui.shortcutLearnNowKeySequenceEdit.setKeySequence(
            self._config.shortcut_learn_now.toString()
        )
        self.ui.shortcutViewMorphsKeySequenceEdit.setKeySequence(
            self._config.shortcut_view_morphemes.toString()
        )
        self.ui.shortcutGeneratorsKeySequenceEdit.setKeySequence(
            self._config.shortcut_generators.toString()
        )
        self.ui.shortcutKnownMorphsExporterKeySequenceEdit.setKeySequence(
            self._config.shortcut_known_morphs_exporter.toString()
        )

    def setup_buttons(self) -> None:
        self.ui.restoreShortcutsPushButton.setAutoDefault(False)
        self.ui.restoreShortcutsPushButton.clicked.connect(self.restore_defaults)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default shortcuts settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        self.ui.shortcutRecalcKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_recalc
        )
        self.ui.shortcutSettingsKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_settings
        )
        self.ui.shortcutBrowseReadyKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_browse_ready_same_unknown
        )
        self.ui.shortcutBrowseAllKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_browse_all_same_unknown
        )
        self.ui.shortcutBrowseReadyLemmaKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_browse_ready_same_unknown_lemma.toString()
        )
        self.ui.shortcutKnownAndSkipKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_set_known_and_skip
        )
        self.ui.shortcutLearnNowKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_learn_now
        )
        self.ui.shortcutViewMorphsKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_view_morphemes
        )
        self.ui.shortcutViewMorphsKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_view_morphemes.toString()
        )
        self.ui.shortcutKnownMorphsExporterKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_known_morphs_exporter.toString()
        )

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            "shortcut_recalc": self.ui.shortcutRecalcKeySequenceEdit.keySequence().toString(),
            "shortcut_settings": self.ui.shortcutSettingsKeySequenceEdit.keySequence().toString(),
            "shortcut_browse_ready_same_unknown": self.ui.shortcutBrowseReadyKeySequenceEdit.keySequence().toString(),
            "shortcut_browse_all_same_unknown": self.ui.shortcutBrowseAllKeySequenceEdit.keySequence().toString(),
            "shortcut_browse_ready_same_unknown_lemma": self.ui.shortcutBrowseReadyLemmaKeySequenceEdit.keySequence().toString(),
            "shortcut_set_known_and_skip": self.ui.shortcutKnownAndSkipKeySequenceEdit.keySequence().toString(),
            "shortcut_learn_now": self.ui.shortcutLearnNowKeySequenceEdit.keySequence().toString(),
            "shortcut_view_morphemes": self.ui.shortcutViewMorphsKeySequenceEdit.keySequence().toString(),
            "shortcut_generators": self.ui.shortcutGeneratorsKeySequenceEdit.keySequence().toString(),
            "shortcut_known_morphs_exporter": self.ui.shortcutKnownMorphsExporterKeySequenceEdit.keySequence().toString(),
        }
