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

        self._default_config_to_line_edit: dict[str, QLineEdit] = {
            self._default_config.tag_ready: self.ui.tagReadyLineEdit,
            self._default_config.tag_not_ready: self.ui.tagNotReadyLineEdit,
            self._default_config.tag_known_automatically: self.ui.tagKnownAutomaticallyLineEdit,
            self._default_config.tag_known_manually: self.ui.tagKnownManuallyLineEdit,
            self._default_config.tag_learn_card_now: self.ui.tagLearnCardNowLineEdit,
        }

        self._config_to_line_edit: dict[str, QLineEdit] = {
            self._config.tag_ready: self.ui.tagReadyLineEdit,
            self._config.tag_not_ready: self.ui.tagNotReadyLineEdit,
            self._config.tag_known_automatically: self.ui.tagKnownAutomaticallyLineEdit,
            self._config.tag_known_manually: self.ui.tagKnownManuallyLineEdit,
            self._config.tag_learn_card_now: self.ui.tagLearnCardNowLineEdit,
        }

        self.populate()
        self.setup_buttons()
        self._previous_state = self.settings_to_dict()

    def populate(self) -> None:
        for tag, line_edit in self._config_to_line_edit.items():
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

        for tag, line_edit in self._default_config_to_line_edit.items():
            line_edit.setText(tag)

    def restore_to_config_state(self) -> None:
        assert self._previous_state is not None

        for tag, line_edit in self._raw_config_key_to_line_edit.items():
            initial_tag = self._previous_state[tag]
            assert isinstance(initial_tag, str)
            line_edit.setText(initial_tag)

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            config_key: line_edit.text()
            for config_key, line_edit in self._raw_config_key_to_line_edit.items()
        }
