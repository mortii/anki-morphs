from __future__ import annotations

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class PreprocessTab(AbstractSettingsTab):

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
        self.ui.preprocessIgnoreSquareCheckBox.setChecked(
            self._config.preprocess_ignore_bracket_contents
        )
        self.ui.preprocessIgnoreRoundCheckBox.setChecked(
            self._config.preprocess_ignore_round_bracket_contents
        )
        self.ui.preprocessIgnoreSlimCheckBox.setChecked(
            self._config.preprocess_ignore_slim_round_bracket_contents
        )
        self.ui.preprocessIgnoreNamesMizerCheckBox.setChecked(
            self._config.preprocess_ignore_names_morphemizer
        )
        self.ui.preprocessIgnoreNamesFileCheckBox.setChecked(
            self._config.preprocess_ignore_names_textfile
        )
        self.ui.preprocessIgnoreSuspendedCheckBox.setChecked(
            self._config.preprocess_ignore_suspended_cards_content
        )

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default preprocess settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        self.ui.preprocessIgnoreSquareCheckBox.setChecked(
            self._default_config.preprocess_ignore_bracket_contents
        )
        self.ui.preprocessIgnoreRoundCheckBox.setChecked(
            self._default_config.preprocess_ignore_round_bracket_contents
        )
        self.ui.preprocessIgnoreSlimCheckBox.setChecked(
            self._default_config.preprocess_ignore_slim_round_bracket_contents
        )
        self.ui.preprocessIgnoreNamesMizerCheckBox.setChecked(
            self._default_config.preprocess_ignore_names_morphemizer
        )
        self.ui.preprocessIgnoreNamesFileCheckBox.setChecked(
            self._default_config.preprocess_ignore_names_textfile
        )
        self.ui.preprocessIgnoreSuspendedCheckBox.setChecked(
            self._default_config.preprocess_ignore_suspended_cards_content
        )
