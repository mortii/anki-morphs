from __future__ import annotations

import json
from collections.abc import Sequence
from functools import partial
from pathlib import Path

import aqt
from anki.models import NotetypeDict, NotetypeNameId
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QTableWidgetItem,
)
from aqt.utils import tooltip

from .settings_extra_fields_tab import ExtraFieldsTab
from .. import ankimorphs_globals, message_box_utils, table_utils
from ..ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from ..morphemizers.morphemizer import get_all_morphemizers
from ..tag_selection_dialog import TagSelectionDialog
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class NoteFiltersTab(  # pylint:disable=too-many-instance-attributes
    AbstractSettingsTab
):
    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        assert mw is not None

        self._parent = parent
        self.ui = ui
        self._config = config
        self._default_config = default_config

        self.ui.note_filters_table.cellClicked.connect(self._tags_cell_clicked)

        # disables manual editing of note filter table
        self.ui.note_filters_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self._note_filter_note_type_column: int = 0
        self._note_filter_tags_column: int = 1
        self._note_filter_field_column: int = 2
        self._note_filter_morphemizer_column: int = 3
        self._note_filter_morph_priority_column: int = 4
        self._note_filter_read_column: int = 5
        self._note_filter_modify_column: int = 6

        self._morphemizers = get_all_morphemizers()
        self._note_type_models: Sequence[NotetypeNameId] = (
            mw.col.models.all_names_and_ids()
        )

        # the tag selector dialog is spawned from the settings dialog,
        # so it makes the most sense to store it here instead of __init__.py
        self.tag_selector = TagSelectionDialog()
        self.tag_selector.ui.applyButton.clicked.connect(self._update_note_filter_tags)
        # close the tag selector dialog when the settings dialog closes
        self._parent.finished.connect(self.tag_selector.close)

        # Have the Anki dialog manager handle the tag selector dialog
        aqt.dialogs.register_dialog(
            name=ankimorphs_globals.TAG_SELECTOR_DIALOG_NAME,
            creator=self.tag_selector.show,
        )

        self._observer: ExtraFieldsTab | None = None

        # self._extra_fields_tab: ExtraFieldsTab | None = None

    def register_observer(self, observer: ExtraFieldsTab):
        self._observer = observer

    def notify_observers(self, note_type_cbox: QComboBox):
        selected_note_type: str = note_type_cbox.itemText(note_type_cbox.currentIndex())
        self._observer.update(selected_note_type)

    def _setup_note_filters_table(
        self, config_filters: list[AnkiMorphsConfigFilter]
    ) -> None:
        self.ui.note_filters_table.setColumnWidth(
            self._note_filter_note_type_column, 150
        )
        self.ui.note_filters_table.setColumnWidth(
            self._note_filter_morphemizer_column, 150
        )
        self.ui.note_filters_table.setColumnWidth(
            self._note_filter_morph_priority_column, 150
        )
        self.ui.note_filters_table.setRowCount(len(config_filters))
        self.ui.note_filters_table.setAlternatingRowColors(True)

        for row, am_filter in enumerate(config_filters):
            self._set_note_filters_table_row(row, am_filter)

    def populate(self) -> None:
        self._setup_note_filters_table(self._config.filters)

    def setup_buttons(self) -> None:
        self.ui.addNewRowPushButton.setAutoDefault(False)
        self.ui.deleteRowPushButton.setAutoDefault(False)
        self.ui.addNewRowPushButton.clicked.connect(self._add_new_row)
        self.ui.deleteRowPushButton.clicked.connect(self._delete_row)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        self._setup_note_filters_table(self._default_config.filters)

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {}

    def _add_new_row(self) -> None:
        print("add new row")
        self.ui.note_filters_table.setRowCount(
            self.ui.note_filters_table.rowCount() + 1
        )
        config_filter = self._default_config.filters[0]
        row = self.ui.note_filters_table.rowCount() - 1
        self._set_note_filters_table_row(row, config_filter)
        # total_filters = self._config.filters + [config_filter]
        # self._setup_extra_fields_tree_widget(total_filters)
        # todo signal to extra fields

    def _delete_row(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to delete the selected row?"
        confirmed = message_box_utils.warning_dialog(title, text, parent=self._parent)

        if confirmed:
            selected_row = self.ui.note_filters_table.currentRow()
            self.ui.note_filters_table.removeRow(selected_row)
            # we don't have to update the extra fields tree here
            # since filters are created based on note filter table,
            # so any obsolete extra fields configs are not used anyway

    def _set_note_filters_table_row(
        self, row: int, config_filter: AnkiMorphsConfigFilter
    ) -> None:
        assert mw is not None
        self.ui.note_filters_table.setRowHeight(row, 35)

        note_type_cbox = self._setup_note_type_cbox(config_filter)
        selected_note_type: str = note_type_cbox.itemText(note_type_cbox.currentIndex())
        field_cbox = self._setup_fields_cbox(config_filter, selected_note_type)

        # Fields are dependent on note-type
        note_type_cbox.currentIndexChanged.connect(
            partial(self._update_fields_cbox, field_cbox, note_type_cbox)
        )
        note_type_cbox.currentIndexChanged.connect(
            partial(self.notify_observers, note_type_cbox)
        )

        morphemizer_cbox = self._setup_morphemizer_cbox(config_filter)
        morph_priority_cbox = self._setup_morph_priority_cbox(config_filter)

        read_checkbox = QCheckBox()
        read_checkbox.setChecked(config_filter.read)
        read_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

        modify_checkbox = QCheckBox()
        modify_checkbox.setChecked(config_filter.modify)
        modify_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

        self.ui.note_filters_table.setCellWidget(
            row, self._note_filter_note_type_column, note_type_cbox
        )
        self.ui.note_filters_table.setItem(
            row,
            self._note_filter_tags_column,
            QTableWidgetItem(json.dumps(config_filter.tags)),
        )
        self.ui.note_filters_table.setCellWidget(
            row, self._note_filter_field_column, field_cbox
        )
        self.ui.note_filters_table.setCellWidget(
            row, self._note_filter_morphemizer_column, morphemizer_cbox
        )
        self.ui.note_filters_table.setCellWidget(
            row, self._note_filter_morph_priority_column, morph_priority_cbox
        )
        self.ui.note_filters_table.setCellWidget(
            row, self._note_filter_read_column, read_checkbox
        )
        self.ui.note_filters_table.setCellWidget(
            row, self._note_filter_modify_column, modify_checkbox
        )

    def _setup_note_type_cbox(self, config_filter: AnkiMorphsConfigFilter) -> QComboBox:
        note_type_cbox = QComboBox(self.ui.note_filters_table)
        note_types_string: list[str] = [ankimorphs_globals.NONE_OPTION] + [
            model.name for model in self._note_type_models
        ]
        note_type_cbox.addItems(note_types_string)
        note_type_name_index = table_utils.get_combobox_index(
            note_types_string, config_filter.note_type
        )
        note_type_cbox.setCurrentIndex(note_type_name_index)
        return note_type_cbox

    def _setup_fields_cbox(
        self, config_filter: AnkiMorphsConfigFilter, selected_note_type: str
    ) -> QComboBox:
        assert mw is not None

        note_type_dict: NotetypeDict | None = mw.col.models.by_name(
            name=selected_note_type
        )
        note_type_fields: list[str] = [ankimorphs_globals.NONE_OPTION]

        if note_type_dict is not None:
            note_type_fields += mw.col.models.field_map(note_type_dict)

        field_cbox = QComboBox(self.ui.note_filters_table)
        field_cbox.addItems(note_type_fields)
        field_cbox_index = table_utils.get_combobox_index(
            note_type_fields, config_filter.field
        )
        if field_cbox_index is not None:
            field_cbox.setCurrentIndex(field_cbox_index)
        return field_cbox

    def _setup_morphemizer_cbox(
        self, config_filter: AnkiMorphsConfigFilter
    ) -> QComboBox:
        morphemizer_cbox = QComboBox(self.ui.note_filters_table)
        morphemizers: list[str] = [ankimorphs_globals.NONE_OPTION] + [
            mizer.get_description() for mizer in self._morphemizers
        ]
        morphemizer_cbox.addItems(morphemizers)
        morphemizer_cbox_index = table_utils.get_combobox_index(
            morphemizers, config_filter.morphemizer_description
        )
        if morphemizer_cbox_index is not None:
            morphemizer_cbox.setCurrentIndex(morphemizer_cbox_index)
        return morphemizer_cbox

    def _setup_morph_priority_cbox(
        self, config_filter: AnkiMorphsConfigFilter
    ) -> QComboBox:
        morph_priority_cbox = QComboBox(self.ui.note_filters_table)
        frequency_files: list[str] = [
            ankimorphs_globals.NONE_OPTION,
            ankimorphs_globals.COLLECTION_FREQUENCY_OPTION,
        ]
        frequency_files += self._get_frequency_files()
        morph_priority_cbox.addItems(frequency_files)
        morph_priority_cbox_index = table_utils.get_combobox_index(
            frequency_files, config_filter.morph_priority_selection
        )
        if morph_priority_cbox_index is not None:
            morph_priority_cbox.setCurrentIndex(morph_priority_cbox_index)
        return morph_priority_cbox

    @staticmethod
    def _get_frequency_files() -> list[str]:
        assert mw is not None
        path_generator = Path(
            mw.pm.profileFolder(), ankimorphs_globals.FREQUENCY_FILES_DIR_NAME
        ).glob("*.csv")
        frequency_files = [file.name for file in path_generator if file.is_file()]
        return frequency_files

    @staticmethod
    def _update_fields_cbox(field_cbox: QComboBox, note_type_cbox: QComboBox) -> None:
        """
        When the note type selection changes we repopulate the fields list,
        and we set the selected field to (none)
        """
        assert mw

        field_cbox.clear()
        note_type_fields: list[str] = [ankimorphs_globals.NONE_OPTION]

        selected_note_type: str = note_type_cbox.itemText(note_type_cbox.currentIndex())
        note_type_dict: NotetypeDict | None = mw.col.models.by_name(
            name=selected_note_type
        )

        if note_type_dict is not None:
            note_type_fields += mw.col.models.field_map(note_type_dict)

        field_cbox.addItems(note_type_fields)
        field_cbox.setCurrentIndex(0)

    def _tags_cell_clicked(self, row: int, column: int) -> None:
        if column != 1:
            # tags cells are in column 1
            return

        tags_widget: QTableWidgetItem = table_utils.get_table_item(
            self.ui.note_filters_table.item(row, 1)
        )
        self.tag_selector.set_selected_tags_and_row(
            selected_tags=tags_widget.text(), row=row
        )
        aqt.dialogs.open(
            name=ankimorphs_globals.TAG_SELECTOR_DIALOG_NAME,
        )

    def _update_note_filter_tags(self) -> None:
        self.ui.note_filters_table.setItem(
            self.tag_selector.current_note_filter_row,
            1,
            QTableWidgetItem(self.tag_selector.selected_tags),
        )
        self.tag_selector.ui.tableWidget.clearContents()
        tooltip("Remember to save!", parent=self._parent)
