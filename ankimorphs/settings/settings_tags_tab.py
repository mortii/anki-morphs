from __future__ import annotations

from aqt.qt import QDialog, QLineEdit  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class TagsTab(AbstractSettingsTab):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_line_edit: dict[str, QLineEdit] = {
            RawConfigKeys.TAG_READY: self.ui.tagReadyLineEdit,
            RawConfigKeys.TAG_NOT_READY: self.ui.tagNotReadyLineEdit,
            RawConfigKeys.TAG_KNOWN_AUTOMATICALLY: self.ui.tagKnownAutomaticallyLineEdit,
            RawConfigKeys.TAG_KNOWN_MANUALLY: self.ui.tagKnownManuallyLineEdit,
            RawConfigKeys.TAG_LEARN_CARD_NOW: self.ui.tagLearnCardNowLineEdit,
        }

        self.populate()
        self.setup_buttons()
        self._previous_state = self.settings_to_dict()

    def populate(self) -> None:
        for config_attribute, line_edit in self._raw_config_key_to_line_edit.items():
            tag = getattr(self._config, config_attribute)
            line_edit.setText(tag)

    def setup_buttons(self) -> None:
        self.ui.restoreTagsPushButton.setAutoDefault(False)
        self.ui.restoreTagsPushButton.clicked.connect(self.restore_defaults)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default tags settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        for config_attribute, line_edit in self._raw_config_key_to_line_edit.items():
            tag = getattr(self._default_config, config_attribute)
            line_edit.setText(tag)

    def restore_to_config_state(self) -> None:
        assert self._previous_state is not None

        for config_key, line_edit in self._raw_config_key_to_line_edit.items():
            previous_tag = self._previous_state[config_key]
            assert isinstance(previous_tag, str)
            line_edit.setText(previous_tag)

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            config_key: line_edit.text()
            for config_key, line_edit in self._raw_config_key_to_line_edit.items()
        }
