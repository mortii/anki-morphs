from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import aqt
from anki.models import NotetypeDict, NotetypeNameId
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QItemSelectionModel,
    QTableWidgetItem,
)
from aqt.utils import tooltip

from .. import (
    ankimorphs_globals,
    message_box_utils,
    morph_priority_utils,
    table_utils,
    tags_and_queue_utils,
)
from ..ankimorphs_config import (
    AnkiMorphsConfig,
    AnkiMorphsConfigFilter,
    FilterTypeAlias,
    RawConfigFilterKeys,
    RawConfigKeys,
)
from ..morphemizers.morphemizer_utils import get_all_morphemizers
from ..tag_selection_dialog import TagSelectionDialog
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .data_provider import DataProvider
from .settings_tab import SettingsTab


class NoteFiltersTab(  # pylint:disable=too-many-instance-attributes
    SettingsTab, DataProvider
):

    def __init__(  # pylint:disable=too-many-arguments
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        assert mw is not None

        SettingsTab.__init__(self, parent, ui, config, default_config)
        DataProvider.__init__(self)

        self.ui.note_filters_table.cellClicked.connect(self._tags_cell_clicked)

        # disables manual editing of note filter table
        self.ui.note_filters_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self._note_filter_note_type_column: int = 0
        self._note_filter_tags_column: int = 1
        self._note_filter_read_field_column: int = 2
        self._note_filter_modify_field_column: int = 3
        self._note_filter_morphemizer_column: int = 4
        self._note_filter_morph_priority_column: int = 5
        self._note_filter_read_column: int = 6
        self._note_filter_modify_column: int = 7

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

        self._previous_config_filters: dict[str, str | int | bool | object] | None = (
            None
        )

        # key = source combobox
        self.reset_tags_warning_shown = {
            "field": False,
            "note type": False,
            "morphemizer": False,
        }

        # Dynamically added widgets in the rows can be randomly garbage collected
        # if there are no persistent references to them outside the function that creates them.
        # This dict acts as a workaround to that problem.
        self.widget_references_by_row: list[tuple[Any, ...]] = []

        # needed to prevent garbage collection
        self.selection_model: QItemSelectionModel | None = None

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def notify_subscribers(self) -> None:
        assert self._subscriber is not None
        selected_note_types = self._get_selected_note_filters()
        self._subscriber.update(selected_note_types)

    def _get_selected_note_filters(self) -> list[str]:
        selected_note_types: list[str] = []
        for row in range(self.ui.note_filters_table.rowCount()):
            note_filter_note_type_widget: QComboBox = table_utils.get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_note_type_column
                )
            )
            note_type: str = note_filter_note_type_widget.itemText(
                note_filter_note_type_widget.currentIndex()
            )
            selected_note_types.append(note_type)
        return selected_note_types

    def _setup_note_filters_table(
        self, config_filters: list[AnkiMorphsConfigFilter]
    ) -> None:
        self.ui.note_filters_table.setColumnWidth(
            self._note_filter_note_type_column, 150
        )
        self.ui.note_filters_table.setColumnWidth(
            self._note_filter_read_field_column, 120
        )
        self.ui.note_filters_table.setColumnWidth(
            self._note_filter_modify_field_column, 120
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

    def populate(self, use_default_config: bool = False) -> None:
        filters: list[AnkiMorphsConfigFilter]

        if use_default_config:
            filters = self._default_config.filters
        else:
            filters = self._config.filters

        self._clear_note_filters_table()
        self._setup_note_filters_table(filters)

    def setup_buttons(self) -> None:
        self.ui.addNewRowPushButton.setAutoDefault(False)
        self.ui.deleteRowPushButton.setAutoDefault(False)
        self.ui.restoreNoteFiltersPushButton.setAutoDefault(False)

        self.ui.addNewRowPushButton.clicked.connect(self._add_new_row)
        self.ui.deleteRowPushButton.clicked.connect(self._delete_row)
        self.ui.restoreNoteFiltersPushButton.clicked.connect(self.restore_defaults)

        # disable while no rows are selected
        self._on_no_row_selected()

        self.selection_model = self.ui.note_filters_table.selectionModel()
        assert self.selection_model is not None
        self.selection_model.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self) -> None:
        assert self.selection_model is not None

        selected_rows = self.selection_model.selectedRows()
        selected_indexes = self.selection_model.selectedIndexes()

        if len(selected_indexes) == 1 or len(selected_rows) == 1:
            self._on_row_selected()
        else:
            self._on_no_row_selected()

    def _on_no_row_selected(self) -> None:
        self.ui.deleteRowPushButton.setDisabled(True)

    def _on_row_selected(self) -> None:
        self.ui.deleteRowPushButton.setEnabled(True)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = self.get_confirmation_text()
            confirmed = message_box_utils.show_warning_box(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        self._setup_note_filters_table(self._default_config.filters)
        self.notify_subscribers()

    def restore_to_config_state(self) -> None:
        self.populate()
        self.notify_subscribers()

    def get_filters(self) -> list[FilterTypeAlias]:
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
            read_field_cbox: QComboBox = table_utils.get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_read_field_column
                )
            )
            modify_field_cbox: QComboBox = table_utils.get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_modify_field_column
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

            _filter: FilterTypeAlias = {
                RawConfigFilterKeys.NOTE_TYPE: note_type_name,
                RawConfigFilterKeys.TAGS: json.loads(tags_widget.text()),
                RawConfigFilterKeys.READ_FIELD: read_field_cbox.itemText(
                    read_field_cbox.currentIndex()
                ),
                RawConfigFilterKeys.MODIFY_FIELD: modify_field_cbox.itemText(
                    modify_field_cbox.currentIndex()
                ),
                RawConfigFilterKeys.MORPHEMIZER_DESCRIPTION: morphemizer_widget.itemText(
                    morphemizer_widget.currentIndex()
                ),
                RawConfigFilterKeys.MORPH_PRIORITY_SELECTION: morph_priority_widget.itemText(
                    morph_priority_widget.currentIndex()
                ),
                RawConfigFilterKeys.READ: read_widget.isChecked(),
                RawConfigFilterKeys.MODIFY: modify_widget.isChecked(),
            }
            filters.append(_filter)
        return filters

    def _get_settings_dict_with_filters(self) -> dict[str, str | int | bool | object]:
        settings_dict_with_filters: dict[str, str | int | bool | object] = {
            RawConfigKeys.FILTERS: self.get_filters()
        }
        return settings_dict_with_filters

    def _add_new_row(self) -> None:
        self.ui.note_filters_table.setRowCount(
            self.ui.note_filters_table.rowCount() + 1
        )
        config_filter = self._default_config.filters[0]
        row = self.ui.note_filters_table.rowCount() - 1
        self._set_note_filters_table_row(row, config_filter)

    def _delete_row(self) -> None:
        title = "Confirmation"
        text = (
            "Are you sure you want to delete the selected row?<br>"
            "Note: This will also unselect the respective extra fields!"
        )
        confirmed = message_box_utils.show_warning_box(title, text, parent=self._parent)

        if confirmed:
            selected_row = self.ui.note_filters_table.currentRow()
            self.ui.note_filters_table.removeRow(selected_row)

            # prevents memory leaks
            del self.widget_references_by_row[selected_row]

            self.notify_subscribers()

    def _clear_note_filters_table(self) -> None:
        """
        Prevents Memory Leaks
        """
        self.widget_references_by_row.clear()
        self.ui.note_filters_table.clearContents()
        self.ui.note_filters_table.setRowCount(0)  # uses removeRows()

    def _set_note_filters_table_row(
        self, row: int, config_filter: AnkiMorphsConfigFilter
    ) -> None:
        assert mw is not None
        self.ui.note_filters_table.setRowHeight(row, 35)

        note_type_cbox = self._setup_note_type_cbox(config_filter)
        note_type_cbox.setProperty("previousIndex", note_type_cbox.currentIndex())
        selected_note_type: str = note_type_cbox.itemText(note_type_cbox.currentIndex())

        tags_filter_widget = QTableWidgetItem(json.dumps(config_filter.tags))

        read_field_cbox = self._setup_read_field_cbox(config_filter, selected_note_type)
        read_field_cbox.setProperty("previousIndex", read_field_cbox.currentIndex())
        read_field_cbox.currentIndexChanged.connect(
            lambda index: self._potentially_reset_tags(
                new_index=index,
                combo_box=read_field_cbox,
                reason_for_reset="field",
            )
        )

        modify_field_cbox = self._setup_modify_field_cbox(config_filter, selected_note_type)
        modify_field_cbox.setProperty("previousIndex", modify_field_cbox.currentIndex())
        modify_field_cbox.currentIndexChanged.connect(
            lambda index: self._potentially_reset_tags(
                new_index=index,
                combo_box=modify_field_cbox,
                reason_for_reset="field",
            )
        )

        # Fields are dependent on note-type
        note_type_cbox.currentIndexChanged.connect(
            lambda _: self._update_fields_cbox(read_field_cbox, note_type_cbox)
        )
        note_type_cbox.currentIndexChanged.connect(
            lambda _: self._update_fields_cbox(modify_field_cbox, note_type_cbox)
        )
        note_type_cbox.currentIndexChanged.connect(
            lambda index: self._potentially_reset_tags(
                new_index=index,
                combo_box=note_type_cbox,
                reason_for_reset="note type",
            )
        )
        note_type_cbox.currentIndexChanged.connect(self.notify_subscribers)

        morphemizer_cbox = self._setup_morphemizer_cbox(config_filter)
        morphemizer_cbox.setProperty("previousIndex", morphemizer_cbox.currentIndex())
        morphemizer_cbox.currentIndexChanged.connect(
            lambda index: self._potentially_reset_tags(
                new_index=index,
                combo_box=morphemizer_cbox,
                reason_for_reset="morphemizer",
            )
        )

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
            tags_filter_widget,
        )
        self.ui.note_filters_table.setCellWidget(
            row, self._note_filter_read_field_column, read_field_cbox
        )
        self.ui.note_filters_table.setCellWidget(
            row, self._note_filter_modify_field_column, modify_field_cbox
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

        # store widgets persistently to prevent garbage collection
        self.widget_references_by_row.append(
            (
                note_type_cbox,
                tags_filter_widget,
                read_field_cbox,
                modify_field_cbox,
                morphemizer_cbox,
                morph_priority_cbox,
                read_checkbox,
                modify_checkbox,
            )
        )

    def _potentially_reset_tags(
        self, new_index: int, combo_box: QComboBox, reason_for_reset: str
    ) -> None:
        """
        To prevent annoying the user, we only want to show the warning dialog once
        per combobox, per setting.
        """

        if not self.reset_tags_warning_shown.get(reason_for_reset, False):
            if new_index == 0:  # Ignore the "(none)" selection
                return

            previous_index = combo_box.property("previousIndex")
            if previous_index == 0:  # Skip if no change
                return

            if self._want_to_reset_am_tags(reason_for_reset):
                tags_and_queue_utils.reset_am_tags(parent=self._parent)

            self.reset_tags_warning_shown[reason_for_reset] = True
            combo_box.setProperty("previousIndex", new_index)

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

    def _setup_read_field_cbox(
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
            note_type_fields, config_filter.read_field
        )
        if field_cbox_index is not None:
            field_cbox.setCurrentIndex(field_cbox_index)
        return field_cbox

    def _setup_modify_field_cbox(
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
            note_type_fields, config_filter.modify_field
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
        priority_files: list[str] = [
            ankimorphs_globals.NONE_OPTION,
            ankimorphs_globals.COLLECTION_FREQUENCY_OPTION,
        ]
        priority_files += morph_priority_utils.get_priority_files()
        morph_priority_cbox.addItems(priority_files)
        morph_priority_cbox_index = table_utils.get_combobox_index(
            priority_files, config_filter.morph_priority_selection
        )
        if morph_priority_cbox_index is not None:
            morph_priority_cbox.setCurrentIndex(morph_priority_cbox_index)
        return morph_priority_cbox

    def _update_fields_cbox(
        self, field_cbox: QComboBox, note_type_cbox: QComboBox
    ) -> None:
        """
        When the note type selection changes we repopulate the fields list,
        and we set the selected field to (none)
        """
        assert mw

        field_cbox.blockSignals(True)  # prevent currentIndexChanged signals

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

        field_cbox.blockSignals(False)  # prevent currentIndexChanged signals

    def _tags_cell_clicked(self, row: int, column: int) -> None:
        if column != self._note_filter_tags_column:
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

    def get_confirmation_text(self) -> str:
        return (
            "Are you sure you want to restore default note filter settings?<br>"
            "Note: This will also unselect the respective extra fields!"
        )

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {}

    def get_data(self) -> Any:
        return self.get_filters()

    def update_previous_state(self) -> None:
        self._previous_config_filters = self._get_settings_dict_with_filters()

    def contains_unsaved_changes(self) -> bool:
        assert self._previous_config_filters is not None

        current_state = self._get_settings_dict_with_filters()
        if current_state != self._previous_config_filters:
            return True

        return False
