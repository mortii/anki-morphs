from __future__ import annotations

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

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
        self.populate()
        self.setup_buttons()
        self._initial_state = self.settings_to_dict()

    def populate(self) -> None:
        self.ui.tagReadyLineEdit.setText(self._config.tag_ready)
        self.ui.tagNotReadyLineEdit.setText(self._config.tag_not_ready)
        self.ui.tagKnownAutomaticallyLineEdit.setText(
            self._config.tag_known_automatically
        )
        self.ui.tagKnownManuallyLineEdit.setText(self._config.tag_known_manually)
        self.ui.tagLearnCardNowLineEdit.setText(self._config.tag_learn_card_now)

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

        self.ui.tagReadyLineEdit.setText(self._default_config.tag_ready)
        self.ui.tagNotReadyLineEdit.setText(self._default_config.tag_not_ready)
        self.ui.tagKnownAutomaticallyLineEdit.setText(
            self._default_config.tag_known_automatically
        )
        self.ui.tagKnownManuallyLineEdit.setText(
            self._default_config.tag_known_manually
        )
        self.ui.tagLearnCardNowLineEdit.setText(self._default_config.tag_learn_card_now)

    def restore_to_config_state(self) -> None:
        assert self._initial_state is not None

        initial_ready_tag = self._initial_state[RawConfigKeys.TAG_READY]
        assert isinstance(initial_ready_tag, str)

        initial_not_ready_tag = self._initial_state[RawConfigKeys.TAG_NOT_READY]
        assert isinstance(initial_not_ready_tag, str)

        initial_known_automatically_tag = self._initial_state[
            RawConfigKeys.TAG_KNOWN_AUTOMATICALLY
        ]
        assert isinstance(initial_known_automatically_tag, str)

        initial_known_manually_tag = self._initial_state[
            RawConfigKeys.TAG_KNOWN_MANUALLY
        ]
        assert isinstance(initial_known_manually_tag, str)

        initial_learn_now_tag = self._initial_state[RawConfigKeys.TAG_LEARN_CARD_NOW]
        assert isinstance(initial_learn_now_tag, str)

        self.ui.tagReadyLineEdit.setText(initial_ready_tag)
        self.ui.tagNotReadyLineEdit.setText(initial_not_ready_tag)
        self.ui.tagKnownAutomaticallyLineEdit.setText(initial_known_automatically_tag)
        self.ui.tagKnownManuallyLineEdit.setText(initial_known_manually_tag)
        self.ui.tagLearnCardNowLineEdit.setText(initial_learn_now_tag)

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            "tag_ready": self.ui.tagReadyLineEdit.text(),
            "tag_not_ready": self.ui.tagNotReadyLineEdit.text(),
            "tag_known_automatically": self.ui.tagKnownAutomaticallyLineEdit.text(),
            "tag_known_manually": self.ui.tagKnownManuallyLineEdit.text(),
            "tag_learn_card_now": self.ui.tagLearnCardNowLineEdit.text(),
        }
