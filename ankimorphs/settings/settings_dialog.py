from __future__ import annotations

import pprint
from typing import Callable

import aqt
from aqt import mw
from aqt.qt import QDialog, QStyle  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from .. import ankimorphs_config, ankimorphs_globals, message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig, FilterTypeAlias
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab
from .settings_algorithm_tab import AlgorithmTab
from .settings_card_handling_tab import CardHandlingTab
from .settings_extra_fields_tab import ExtraFieldsTab
from .settings_general_tab import GeneralTab
from .settings_note_filters_tab import NoteFiltersTab
from .settings_preprocess_tab import PreprocessTab
from .settings_shortcuts_tab import ShortcutTab
from .settings_tags_tab import TagsTab


class SettingsDialog(QDialog):  # pylint:disable=too-many-instance-attributes
    # The UI comes from ankimorphs/ui/settings_dialog.ui which is used in Qt Designer,
    # which is then converted to ankimorphs/ui/settings_dialog_ui.py,
    # which is then imported here.
    #
    # Here we make the final adjustments that can't be made (or are hard to make) in
    # Qt Designer, like setting up tables and widget-connections.

    def __init__(self) -> None:
        super().__init__(parent=None)  # no parent makes the dialog modeless
        assert mw is not None

        self.ui = Ui_SettingsDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        self._config = AnkiMorphsConfig()
        self._default_config = AnkiMorphsConfig(is_default=True)

        self._general_tab = GeneralTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
        )

        self._extra_fields_tab = ExtraFieldsTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
        )

        self._note_filters_tab = NoteFiltersTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
            observer=self._extra_fields_tab,
        )

        self._shortcut_tab = ShortcutTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
        )

        self._algorithm_tab = AlgorithmTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
        )

        self._card_handling_tab = CardHandlingTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
        )

        self._preprocess_tab = PreprocessTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
        )

        self._tags_tab = TagsTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
        )

        self._all_tabs: list[AbstractSettingsTab] = [
            self._general_tab,
            self._extra_fields_tab,
            self._note_filters_tab,
            self._shortcut_tab,
            self._algorithm_tab,
            self._card_handling_tab,
            self._preprocess_tab,
            self._tags_tab,
        ]

        for _tab in self._all_tabs:
            _tab.populate()
            _tab.setup_buttons()

        self._setup_buttons()

        self.ui.ankimorphs_version_label.setText(
            f"AnkiMorphs version: {ankimorphs_globals.__version__}"
        )

        self.show()

    def _restore_all_defaults(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to restore <b>all</b> default settings?"
        confirmed = message_box_utils.warning_dialog(title, text, parent=self)

        if confirmed:
            for _tab in self._all_tabs:
                _tab.restore_defaults(skip_confirmation=True)

    def _setup_buttons(self) -> None:
        style: QStyle | None = self.style()
        assert style is not None

        self.ui.okPushButton.setAutoDefault(False)
        self.ui.applyPushButton.setAutoDefault(False)
        self.ui.cancelPushButton.setAutoDefault(False)
        self.ui.restoreAllDefaultsPushButton.setAutoDefault(False)

        self.ui.okPushButton.clicked.connect(self._save_and_close)
        self.ui.applyPushButton.clicked.connect(self._save_to_config)
        self.ui.cancelPushButton.clicked.connect(self.close)
        self.ui.restoreAllDefaultsPushButton.clicked.connect(self._restore_all_defaults)

    def _save_to_config(self, tooltip_mw: bool = False) -> None:
        new_config: dict[str, str | int | bool | object] = {}
        for _tab in self._all_tabs:
            new_config.update(_tab.settings_to_dict())

        print("new_config:")
        pprint.pp(new_config)

        filters: list[FilterTypeAlias] = self._note_filters_tab.get_filters()
        for _filter in filters:
            note_type_name = _filter["note_type"]
            assert isinstance(note_type_name, str)
            extra_fields_dict: dict[str, bool] = (
                self._extra_fields_tab.get_selected_extra_fields(
                    note_type_name=note_type_name
                )
            )
            _filter.update(extra_fields_dict)

        print("post filters:")
        pprint.pp(filters)

        new_config["filters"] = filters
        ankimorphs_config.update_configs(new_config)

        self._refresh_on_save()

        if tooltip_mw:
            tooltip("Please recalc to avoid unexpected behaviour", parent=mw)
        else:
            tooltip("Please recalc to avoid unexpected behaviour", parent=self)

    def _save_and_close(self) -> None:
        self._save_to_config(tooltip_mw=True)
        self.close()

    def _refresh_on_save(self) -> None:
        self._config = AnkiMorphsConfig()

        # delete caches that uses config data
        self._extra_fields_tab.get_selected_extra_fields_from_config.cache_clear()

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.close()
        aqt.dialogs.markClosed(ankimorphs_globals.SETTINGS_DIALOG_NAME)
        callback()

    def reopen(self) -> None:
        # This is used by the Anki dialog manager
        self.show()
