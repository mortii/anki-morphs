from __future__ import annotations

from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QDialog,
    QRadioButton,
    QSpinBox,
)

from ..ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_tab import SettingsTab


class GeneralTab(SettingsTab):
    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_radio_button: dict[str, QRadioButton] = {
            RawConfigKeys.EVALUATE_MORPH_LEMMA: self.ui.priorityLemmaRadioButton,
            RawConfigKeys.EVALUATE_MORPH_INFLECTION: self.ui.priorityInflectionRadioButton,
        }

        self._raw_config_key_to_check_box: dict[str, QCheckBox] = {
            RawConfigKeys.RECALC_ON_SYNC: self.ui.recalcBeforeSyncCheckBox,
            RawConfigKeys.RECALC_READ_KNOWN_MORPHS_FOLDER: self.ui.recalcReadKnownMorphsFolderCheckBox,
        }

        self._raw_config_key_to_spin_box: dict[str, QSpinBox] = {
            RawConfigKeys.RECALC_INTERVAL_FOR_KNOWN: self.ui.recalcIntervalSpinBox,
        }

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def setup_buttons(self) -> None:
        self.ui.restoreGeneralPushButton.setAutoDefault(False)
        self.ui.restoreGeneralPushButton.clicked.connect(self.restore_defaults)

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default general settings?"
