from __future__ import annotations

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

from .. import message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class GeneralTab(AbstractSettingsTab):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        self._parent = parent
        self.ui = ui
        self._config = config
        self._default_config = default_config

    def populate(self) -> None:
        self.ui.priorityLemmaRadioButton.setChecked(self._config.evaluate_morph_lemma)
        self.ui.priorityInflectionRadioButton.setChecked(
            self._config.evaluate_morph_inflection
        )
        self.ui.toolbarStatsUseSeenRadioButton.setChecked(
            self._config.recalc_toolbar_stats_use_seen
        )
        self.ui.toolbarStatsUseKnownRadioButton.setChecked(
            self._config.recalc_toolbar_stats_use_known
        )
        self.ui.recalcBeforeSyncCheckBox.setChecked(self._config.recalc_on_sync)
        self.ui.recalcReadKnownMorphsFolderCheckBox.setChecked(
            self._config.recalc_read_known_morphs_folder
        )
        self.ui.recalcIntervalSpinBox.setValue(self._config.recalc_interval_for_known)

    def setup_buttons(self) -> None:
        self.ui.restoreGeneralPushButton.setAutoDefault(False)
        self.ui.restoreGeneralPushButton.clicked.connect(self.restore_defaults)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default general settings?"
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        self.ui.priorityLemmaRadioButton.setChecked(
            self._default_config.evaluate_morph_lemma
        )
        self.ui.priorityInflectionRadioButton.setChecked(
            self._default_config.evaluate_morph_lemma
        )
        self.ui.toolbarStatsUseSeenRadioButton.setChecked(
            self._default_config.recalc_toolbar_stats_use_seen
        )
        self.ui.toolbarStatsUseKnownRadioButton.setChecked(
            self._default_config.recalc_toolbar_stats_use_known
        )
        self.ui.recalcBeforeSyncCheckBox.setChecked(self._default_config.recalc_on_sync)
        self.ui.recalcReadKnownMorphsFolderCheckBox.setChecked(
            self._default_config.recalc_read_known_morphs_folder
        )
        self.ui.recalcIntervalSpinBox.setValue(
            self._default_config.recalc_interval_for_known
        )

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            "evaluate_morph_lemma": self.ui.priorityLemmaRadioButton.isChecked(),
            "evaluate_morph_inflection": self.ui.priorityInflectionRadioButton.isChecked(),
            "recalc_toolbar_stats_use_seen": self.ui.toolbarStatsUseSeenRadioButton.isChecked(),
            "recalc_toolbar_stats_use_known": self.ui.toolbarStatsUseKnownRadioButton.isChecked(),
            "recalc_on_sync": self.ui.recalcBeforeSyncCheckBox.isChecked(),
            "recalc_interval_for_known": self.ui.recalcIntervalSpinBox.value(),
            "recalc_read_known_morphs_folder": self.ui.recalcReadKnownMorphsFolderCheckBox.isChecked(),
        }
