from __future__ import annotations

import functools
import json
import pprint
from typing import Callable

import aqt
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QComboBox,
    QDialog,
    QStyle,
    Qt,
    QTableWidgetItem,
    QTreeWidgetItem,
)
from aqt.utils import tooltip

from .. import ankimorphs_config, ankimorphs_globals, message_box_utils, table_utils
from ..ankimorphs_config import AnkiMorphsConfig, FilterTypeAlias
from ..ui.settings_dialog_ui import Ui_SettingsDialog
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

        self._note_filter_note_type_column: int = 0
        self._note_filter_tags_column: int = 1
        self._note_filter_field_column: int = 2
        self._note_filter_morphemizer_column: int = 3
        self._note_filter_morph_priority_column: int = 4
        self._note_filter_read_column: int = 5
        self._note_filter_modify_column: int = 6

        self._config = AnkiMorphsConfig()
        self._default_config = AnkiMorphsConfig(is_default=True)

        self._general_tab = GeneralTab(
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
        )

        self._general_tab.populate()
        self._note_filters_tab.populate()
        self._extra_fields_tab.populate()
        self._tags_tab.populate()
        self._preprocess_tab.populate()
        self._card_handling_tab.populate()
        self._algorithm_tab.populate()
        self._shortcut_tab.populate()

        self._setup_buttons()
        self.ui.tabWidget.currentChanged.connect(self._on_tab_changed)

        self.ui.ankimorphs_version_label.setText(
            f"AnkiMorphs version: {ankimorphs_globals.__version__}"
        )

        self.show()

    def _restore_all_defaults(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to restore <b>all</b> default settings?"
        confirmed = message_box_utils.warning_dialog(title, text, parent=self)

        if confirmed:
            # default_filters = self._default_config.filters
            # self._setup_note_filters_table(default_filters)
            # self._setup_extra_fields_tree_widget(default_filters)
            self._note_filters_tab.restore_defaults(skip_confirmation=True)
            self._extra_fields_tab.restore_defaults(skip_confirmation=True)
            self._general_tab.restore_defaults(skip_confirmation=True)
            self._tags_tab.restore_defaults(skip_confirmation=True)
            self._preprocess_tab.restore_defaults(skip_confirmation=True)
            self._card_handling_tab.restore_defaults(skip_confirmation=True)
            self._algorithm_tab.restore_defaults(skip_confirmation=True)
            self._shortcut_tab.restore_defaults(skip_confirmation=True)

    def _setup_buttons(self) -> None:
        style: QStyle | None = self.style()
        assert style is not None

        save_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        self.ui.savePushButton.setIcon(save_icon)

        cancel_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        self.ui.cancelPushButton.setIcon(cancel_icon)

        self.ui.savePushButton.setAutoDefault(False)
        self.ui.cancelPushButton.setAutoDefault(False)
        self.ui.restoreAllDefaultsPushButton.setAutoDefault(False)

        self.ui.savePushButton.clicked.connect(self._save_to_config)
        self.ui.cancelPushButton.clicked.connect(self.close)
        self.ui.restoreAllDefaultsPushButton.clicked.connect(self._restore_all_defaults)

        ###############################################################
        self._general_tab.setup_buttons()
        self._note_filters_tab.setup_buttons()
        self._extra_fields_tab.setup_buttons()
        self._algorithm_tab.setup_buttons()
        self._tags_tab.setup_buttons()
        self._preprocess_tab.setup_buttons()
        self._shortcut_tab.setup_buttons()
        self._card_handling_tab.setup_buttons()

    def _save_to_config(self) -> None:  # pylint:disable=too-many-locals
        new_config: dict[str, str | int | bool | object] = (
            self._tags_tab.settings_to_dict()
            | self._algorithm_tab.settings_to_dict()
            | self._shortcut_tab.settings_to_dict()
            | self._card_handling_tab.settings_to_dict()
            | self._preprocess_tab.settings_to_dict()
            | self._general_tab.settings_to_dict()
            | self._extra_fields_tab.settings_to_dict()
        )
        print("new_config:")
        pprint.pp(new_config)

        filters: list[FilterTypeAlias] = []
        for row in range(self.ui.note_filters_table.rowCount()):
            note_type_cbox: QComboBox = table_utils.get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_note_type_column
                )
            )
            tags_widget: QTableWidgetItem = table_utils.get_table_item(
                self.ui.note_filters_table.item(row, self._note_filter_tags_column)
            )
            field_cbox: QComboBox = table_utils.get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_field_column
                )
            )
            morphemizer_widget: QComboBox = table_utils.get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_morphemizer_column
                )
            )
            morph_priority_widget: QComboBox = table_utils.get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_morph_priority_column
                )
            )
            read_widget: QCheckBox = table_utils.get_checkbox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_read_column
                )
            )
            modify_widget: QCheckBox = table_utils.get_checkbox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_modify_column
                )
            )

            note_type_name: str = note_type_cbox.itemText(note_type_cbox.currentIndex())

            selected_extra_fields: set[str] = self._get_selected_extra_fields(
                note_type_name
            )
            extra_score = ankimorphs_globals.EXTRA_FIELD_SCORE in selected_extra_fields
            extra_score_terms = (
                ankimorphs_globals.EXTRA_FIELD_SCORE_TERMS in selected_extra_fields
            )
            extra_highlighted = (
                ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED in selected_extra_fields
            )
            extra_unknowns = (
                ankimorphs_globals.EXTRA_FIELD_UNKNOWNS in selected_extra_fields
            )
            extra_unknowns_count = (
                ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT in selected_extra_fields
            )

            _filter: FilterTypeAlias = {
                "note_type": note_type_name,
                "tags": json.loads(tags_widget.text()),
                "field": field_cbox.itemText(field_cbox.currentIndex()),
                "morphemizer_description": morphemizer_widget.itemText(
                    morphemizer_widget.currentIndex()
                ),
                "morph_priority": morph_priority_widget.itemText(
                    morph_priority_widget.currentIndex()
                ),
                "read": read_widget.isChecked(),
                "modify": modify_widget.isChecked(),
                "extra_score": extra_score,
                "extra_score_terms": extra_score_terms,
                "extra_highlighted": extra_highlighted,
                "extra_unknowns": extra_unknowns,
                "extra_unknowns_count": extra_unknowns_count,
            }
            filters.append(_filter)

        new_config["filters"] = filters
        ankimorphs_config.update_configs(new_config)
        self._config = AnkiMorphsConfig()

        # delete cache between saving because it might have been updated
        self._get_selected_extra_fields.cache_clear()

        tooltip("Please recalc to avoid unexpected behaviour", parent=self)

    # the cache needs to have a max size to maintain garbage collection
    @functools.lru_cache(maxsize=131072)
    def _get_selected_extra_fields(self, note_type_name: str) -> set[str]:
        selected_fields: set[str] = set()
        for top_node_index in range(self.ui.extraFieldsTreeWidget.topLevelItemCount()):
            top_node: QTreeWidgetItem | None = (
                self.ui.extraFieldsTreeWidget.topLevelItem(top_node_index)
            )
            assert top_node is not None
            if top_node.text(0) == note_type_name:
                for child_index in range(top_node.childCount()):
                    child = top_node.child(child_index)
                    assert child is not None
                    if child.checkState(0) == Qt.CheckState.Checked:
                        selected_fields.add(child.text(0))
                break
        return selected_fields

    def _on_tab_changed(self, index: int) -> None:
        # The extra fields settings are dependent on the note filters, so
        # every time the extra fields tab is opened we just re-populate it
        # in case the note filters have changed.
        if index == 1:
            # self._setup_extra_fields_tree_widget(self._config.filters)
            # todo: setup
            pass

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
