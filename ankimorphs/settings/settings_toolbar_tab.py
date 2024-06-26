from __future__ import annotations

from aqt.qt import QCheckBox, QDialog, QRadioButton  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_tab import SettingsTab


class ToolbarTab(SettingsTab):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_radio_button: dict[str, QRadioButton] = {
            RawConfigKeys.TOOLBAR_STATS_USE_SEEN: self.ui.toolbarStatsUseSeenRadioButton,
            RawConfigKeys.TOOLBAR_STATS_USE_KNOWN: self.ui.toolbarStatsUseKnownRadioButton,
        }

        self._raw_config_key_to_check_box: dict[str, QCheckBox] = {
            RawConfigKeys.HIDE_RECALC_TOOLBAR: self.ui.hideRecalcCheckBox,
            RawConfigKeys.HIDE_LEMMA_TOOLBAR: self.ui.hideLemmaCheckBox,
            RawConfigKeys.HIDE_INFLECTION_TOOLBAR: self.ui.hideInflectionCheckBox,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def setup_buttons(self) -> None:
        self.ui.restoreToolbarPushButton.setAutoDefault(False)
        self.ui.restoreToolbarPushButton.clicked.connect(self.restore_defaults)

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default toolbar settings?"
