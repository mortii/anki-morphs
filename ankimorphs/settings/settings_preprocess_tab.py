from __future__ import annotations

from aqt.qt import QCheckBox, QDialog  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class PreprocessTab(AbstractSettingsTab):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_checkbox: dict[str, QCheckBox] = {
            RawConfigKeys.PREPROCESS_IGNORE_BRACKET_CONTENTS: self.ui.preprocessIgnoreSquareCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_ROUND_BRACKET_CONTENTS: self.ui.preprocessIgnoreRoundCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_SLIM_ROUND_BRACKET_CONTENTS: self.ui.preprocessIgnoreSlimCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_NAMES_MORPHEMIZER: self.ui.preprocessIgnoreNamesMizerCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_NAMES_TEXTFILE: self.ui.preprocessIgnoreNamesFileCheckBox,
            RawConfigKeys.PREPROCESS_IGNORE_SUSPENDED_CARDS_CONTENT: self.ui.preprocessIgnoreSuspendedCheckBox,
        }

        self.populate()
        self.setup_buttons()
        self._previous_state = self.settings_to_dict()

    def populate(self) -> None:
        for config_attribute, checkbox in self._raw_config_key_to_checkbox.items():
            is_checked = getattr(self._config, config_attribute)
            checkbox.setChecked(is_checked)

    def setup_buttons(self) -> None:
        self.ui.restorePreprocessPushButton.setAutoDefault(False)
        self.ui.restorePreprocessPushButton.clicked.connect(self.restore_defaults)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default preprocess settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        for config_attribute, checkbox in self._raw_config_key_to_checkbox.items():
            is_checked = getattr(self._default_config, config_attribute)
            checkbox.setChecked(is_checked)

    def restore_to_config_state(self) -> None:
        assert self._previous_state is not None

        for config_key, checkbox in self._raw_config_key_to_checkbox.items():
            previous_check_state = self._previous_state[config_key]
            assert isinstance(previous_check_state, bool)
            checkbox.setChecked(previous_check_state)

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            config_key: checkbox.isChecked()
            for config_key, checkbox in self._raw_config_key_to_checkbox.items()
        }
