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
    ):
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
        self.ui.unknownsFieldShowsInflectionsRadioButton.setChecked(
            self._config.recalc_unknowns_field_shows_inflections
        )
        self.ui.unknownsFieldShowsLemmasRadioButton.setChecked(
            self._config.recalc_unknowns_field_shows_lemmas
        )

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
        self.ui.unknownsFieldShowsInflectionsRadioButton.setChecked(
            self._default_config.recalc_unknowns_field_shows_inflections
        )
        self.ui.unknownsFieldShowsLemmasRadioButton.setChecked(
            self._default_config.recalc_unknowns_field_shows_lemmas
        )
