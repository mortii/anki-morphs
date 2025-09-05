from __future__ import annotations

from typing import Any, Callable

import aqt
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QDialog, QSizePolicy, QWidget  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from .. import (
    ankimorphs_config,
    ankimorphs_globals,
    message_box_utils,
    text_preprocessing,
)
from ..ankimorphs_config import AnkiMorphsConfig
from ..extra_settings import extra_settings_keys
from ..extra_settings.ankimorphs_extra_settings import AnkiMorphsExtraSettings
from ..morphemizers import morphemizer_utils
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_algorithm_tab import AlgorithmTab
from .settings_card_handling_tab import CardHandlingTab
from .settings_extra_fields_tab import ExtraFieldsTab
from .settings_general_tab import GeneralTab
from .settings_note_filters_tab import NoteFiltersTab
from .settings_preprocess_tab import PreprocessTab
from .settings_shortcuts_tab import ShortcutTab
from .settings_tab import SettingsTab
from .settings_tags_tab import TagsTab


class SettingsDialog(QDialog):  # pylint:disable=too-many-instance-attributes
    def __init__(self) -> None:
        super().__init__(parent=None)  # no parent makes the dialog modeless

        tooltip(msg="Preparing settings window, this might take a while...", parent=mw)
        mw.progress.start(label="Gathering available morphemizers...")

        def _background_gather_resources() -> None:
            # this can be really slow, especially on windows and macOS,
            # so we do this on a background thread to prevent anki from
            # freezing.
            morphemizer_utils.get_all_morphemizers()

        def _on_failure(_error: Exception) -> None:
            # This function runs on the main thread.
            assert mw is not None
            assert mw.progress is not None
            mw.progress.finish()
            message_box_utils.show_error_box(
                title="AnkiMorphs Error",
                body="Something went horribly wrong when gathering morphemizers",
                parent=mw,
            )

        operation = QueryOp(
            parent=mw,
            op=lambda _: _background_gather_resources(),
            success=lambda _: self._init_ui(),
        )
        operation.failure(_on_failure)
        operation.with_progress().run_in_background()

    def _init_ui(self) -> None:
        # The UI comes from ankimorphs/ui/settings_dialog.ui which is used in Qt Designer,
        # which is then converted to ankimorphs/ui/settings_dialog_ui.py,
        # which is then imported here.
        #
        # Here we make the final adjustments that can't be made (or are hard to make) in
        # Qt Designer, like setting up tables and widget-connections.

        assert mw is not None
        assert mw.progress is not None
        mw.progress.finish()

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
        self._note_filters_tab = NoteFiltersTab(
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
        self._tags_tab = TagsTab(
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
        self._card_handling_tab = CardHandlingTab(
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
        self._shortcut_tab = ShortcutTab(
            parent=self,
            ui=self.ui,
            config=self._config,
            default_config=self._default_config,
        )

        self._note_filters_tab.add_subscriber(self._extra_fields_tab)
        self._extra_fields_tab.add_data_provider(self._note_filters_tab)

        self._all_tabs: list[SettingsTab] = [
            self._general_tab,
            self._note_filters_tab,
            self._extra_fields_tab,
            self._tags_tab,
            self._preprocess_tab,
            self._card_handling_tab,
            self._algorithm_tab,
            self._shortcut_tab,
        ]

        self._setup_buttons()

        self.ui.ankimorphs_version_label.setText(
            f"AnkiMorphs version: {ankimorphs_globals.__version__}"
        )

        # change the minimum size of the window depending on the current tab layout
        self.ui.tabWidget.currentChanged.connect(self._update_size_policies)

        # apply the size policy to the initial tab
        self._update_size_policies(index=0)

        self.am_extra_settings = AnkiMorphsExtraSettings()
        self.am_extra_settings.beginGroup(extra_settings_keys.Dialogs.SETTINGS_DIALOG)
        self._setup_geometry()
        self.am_extra_settings.endGroup()

        self.show()

    def _restore_all_defaults(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to restore <b>all</b> default settings?"
        confirmed = message_box_utils.show_warning_box(title, text, parent=self)

        if confirmed:
            for _tab in self._all_tabs:
                _tab.restore_defaults(skip_confirmation=True)

    def _setup_buttons(self) -> None:
        self.ui.okPushButton.setAutoDefault(False)
        self.ui.applyPushButton.setAutoDefault(False)
        self.ui.cancelPushButton.setAutoDefault(False)
        self.ui.restoreAllDefaultsPushButton.setAutoDefault(False)

        self.ui.okPushButton.clicked.connect(
            lambda: self._save(close_window=True, tooltip_mw=True)
        )
        self.ui.applyPushButton.clicked.connect(self._save)
        self.ui.cancelPushButton.clicked.connect(self._discard_and_close)
        self.ui.restoreAllDefaultsPushButton.clicked.connect(self._restore_all_defaults)

    def _setup_geometry(self) -> None:
        stored_geometry = self.am_extra_settings.value(
            extra_settings_keys.SettingsDialogKeys.WINDOW_GEOMETRY
        )
        if stored_geometry is not None:
            self.restoreGeometry(stored_geometry)

    def _update_config(
        self, show_tooltip: bool = True, tooltip_mw: bool = False
    ) -> None:
        assert mw is not None

        new_config: dict[str, str | int | float | bool | object] = {}
        for _tab in self._all_tabs:
            new_config.update(_tab.settings_to_dict())

        ankimorphs_config.update_configs(new_config)
        self._config.update()

        for _tab in self._all_tabs:
            _tab.update_previous_state()

        if show_tooltip:
            tooltip_parent: QWidget
            if tooltip_mw:
                tooltip_parent = mw
            else:
                tooltip_parent = self
            tooltip(
                "Please recalc to avoid unexpected behaviour", parent=tooltip_parent
            )

    def _save(self, close_window: bool = False, tooltip_mw: bool = False) -> None:
        show_tooltip = bool(self._tabs_have_unsaved_changes())
        self._update_config(show_tooltip=show_tooltip, tooltip_mw=tooltip_mw)
        text_preprocessing.update_translation_table()
        if close_window:
            self.close()

    def _tabs_have_unsaved_changes(self) -> bool:
        for _tab in self._all_tabs:
            if _tab.contains_unsaved_changes():
                return True
        return False

    def _discard_and_close(self) -> None:
        for _tab in self._all_tabs:
            _tab.restore_to_config_state()
        self.close()

    def _update_size_policies(self, index: int) -> None:
        tab_widget = self.ui.tabWidget

        # Set size policy to Ignored for all tabs except the selected one
        for i in range(tab_widget.count()):
            widget = tab_widget.widget(i)
            assert widget is not None

            if i != index:
                widget.setSizePolicy(
                    QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
                )

        # Set size policy to Preferred for the selected tab and adjust its size
        selected_widget = tab_widget.widget(index)
        assert selected_widget is not None

        selected_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        selected_widget.resize(selected_widget.minimumSizeHint())
        selected_widget.adjustSize()

    def closeEvent(self, event: Any) -> None:  # pylint:disable=invalid-name
        # overriding the QDialog close event function

        if self._tabs_have_unsaved_changes():
            title = "Unsaved changes"
            text = "Discard unsaved changes?"
            confirmed = message_box_utils.show_discard_message_box(
                title, text, parent=self
            )

            if confirmed:
                for _tab in self._all_tabs:
                    _tab.restore_to_config_state()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.am_extra_settings.save_settings_dialog_settings(
            geometry=self.saveGeometry()
        )
        self.close()
        aqt.dialogs.markClosed(ankimorphs_globals.SETTINGS_DIALOG_NAME)
        callback()

    def reopen(self) -> None:
        # This is used by the Anki dialog manager
        self.show()
