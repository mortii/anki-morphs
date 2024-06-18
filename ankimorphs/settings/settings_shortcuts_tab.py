from __future__ import annotations

from aqt.qt import QDialog, QKeySequenceEdit  # pylint:disable=no-name-in-module

from .. import message_box_utils
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
        self._previous_state = self.settings_to_dict()

    def populate(self) -> None:
        for config_attribute, checkbox in self._raw_config_key_to_key_sequence.items():
            key_sequence = getattr(self._config, config_attribute)
            checkbox.setKeySequence(key_sequence)

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

        for config_attribute, checkbox in self._raw_config_key_to_key_sequence.items():
            key_sequence = getattr(self._default_config, config_attribute)
            checkbox.setKeySequence(key_sequence)

    def restore_to_config_state(self) -> None:
        assert self._previous_state is not None

        for (
            config_key,
            key_sequence_edit,
        ) in self._raw_config_key_to_key_sequence.items():
            previous_key_sequence = self._previous_state[config_key]
            assert isinstance(previous_key_sequence, str)
            key_sequence_edit.setKeySequence(previous_key_sequence)

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            config_key: key_sequence.keySequence().toString()
            for config_key, key_sequence in self._raw_config_key_to_key_sequence.items()
        }
