from __future__ import annotations

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class RecalcTab(AbstractSettingsTab):

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
        self.ui.recalcBeforeSyncCheckBox.setChecked(self._config.recalc_on_sync)
        self.ui.recalcReadKnownMorphsFolderCheckBox.setChecked(
            self._config.recalc_read_known_morphs_folder
        )
        self.ui.recalcIntervalSpinBox.setValue(self._config.recalc_interval_for_known)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default recalc settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        self.ui.recalcBeforeSyncCheckBox.setChecked(self._default_config.recalc_on_sync)
        self.ui.recalcReadKnownMorphsFolderCheckBox.setChecked(
            self._default_config.recalc_read_known_morphs_folder
        )
        self.ui.recalcIntervalSpinBox.setValue(
            self._default_config.recalc_interval_for_known
        )
