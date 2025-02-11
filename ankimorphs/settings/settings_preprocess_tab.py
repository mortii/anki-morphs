from __future__ import annotations

from aqt.qt import QCheckBox, QDialog, QLineEdit, Qt  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_tab import SettingsTab


class PreprocessTab(SettingsTab):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_check_box: dict[str, QCheckBox] = {
            RawConfigKeys.PREPROCESS_IGNORE_BRACKET_CONTENTS: self.ui.preprocessIgnoreSquareCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_ROUND_BRACKET_CONTENTS: self.ui.preprocessIgnoreRoundCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_SLIM_ROUND_BRACKET_CONTENTS: self.ui.preprocessIgnoreSlimCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_NAMES_MORPHEMIZER: self.ui.preprocessIgnoreNamesMizerCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_NAMES_TEXTFILE: self.ui.preprocessIgnoreNamesFileCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_NUMBERS: self.ui.preprocessIgnoreNumbersCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_SUSPENDED_CARDS_CONTENT: self.ui.preprocessIgnoreSuspendedCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_CUSTOM_CHARACTERS: self.ui.preprocessIgnoreCustomCharactersCheckBox,
        }

        self._raw_config_key_to_line_edit: dict[str, QLineEdit] = {
            RawConfigKeys.PREPROCESS_CUSTOM_CHARACTERS_TO_IGNORE: self.ui.preprocessCustomCharactersLineEdit,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def populate(self, use_default_config: bool = False) -> None:
        super().populate(use_default_config)
        self._toggle_disable_custom_characters_line_edit()

    def setup_buttons(self) -> None:
        self.ui.restorePreprocessPushButton.setAutoDefault(False)
        self.ui.restorePreprocessPushButton.clicked.connect(self.restore_defaults)

        self.ui.preprocessIgnoreCustomCharactersCheckBox.stateChanged.connect(
            self._toggle_disable_custom_characters_line_edit
        )

    def _toggle_disable_custom_characters_line_edit(self) -> None:
        if (
            self.ui.preprocessIgnoreCustomCharactersCheckBox.checkState()
            == Qt.CheckState.Unchecked
        ):
            self.ui.preprocessCustomCharactersLineEdit.setDisabled(True)
        else:
            self.ui.preprocessCustomCharactersLineEdit.setEnabled(True)

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default preprocess settings?"
