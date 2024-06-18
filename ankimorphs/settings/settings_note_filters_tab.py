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
    QItemSelectionModel,
    QTableWidgetItem,
)
from aqt.utils import tooltip

from .. import ankimorphs_globals, message_box_utils, table_utils
from ..ankimorphs_config import (
    AnkiMorphsConfig,
    AnkiMorphsConfigFilter,
    FilterTypeAlias,
)
from ..morphemizers.morphemizer import get_all_morphemizers
from ..tag_selection_dialog import TagSelectionDialog
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab
from .settings_extra_fields_tab import ExtraFieldsTab


class NoteFiltersTab(  # pylint:disable=too-many-instance-attributes
    AbstractSettingsTab
):

    def __init__(  # pylint:disable=too-many-arguments
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
        observer: ExtraFieldsTab,
    ) -> None:
        assert mw is not None

        super().__init__(parent, ui, config, default_config)

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

        self._observer: ExtraFieldsTab = observer

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def notify_observers(self) -> None:
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

        self._observer.update(selected_note_types)

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
        self.ui.restoreNoteFiltersPushButton.setAutoDefault(False)

        self.ui.addNewRowPushButton.clicked.connect(self._add_new_row)
        self.ui.deleteRowPushButton.clicked.connect(self._delete_row)
        self.ui.restoreNoteFiltersPushButton.clicked.connect(self.restore_defaults)

        # disable while no rows are selected
        self._on_no_row_selected()

        selection_model = self.ui.note_filters_table.selectionModel()
        assert selection_model is not None

        selection_model.selectionChanged.connect(
            lambda: self._on_selection_changed(selection_model)
        )

    def _on_selection_changed(self, selection_model: QItemSelectionModel) -> None:
        selected_rows = selection_model.selectedRows()
        selected_indexes = selection_model.selectedIndexes()

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
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        self._setup_note_filters_table(self._default_config.filters)
        self.notify_observers()

    def restore_to_config_state(self) -> None:
        # todo...
        pass

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
            }
            filters.append(_filter)
        return filters

    def _add_new_row(self) -> None:
        print("add new row")
        self.ui.note_filters_table.setRowCount(
            self.ui.note_filters_table.rowCount() + 1
        )
        config_filter = self._default_config.filters[0]
        row = self.ui.note_filters_table.rowCount() - 1
        self._set_note_filters_table_row(row, config_filter)

    def _delete_row(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to delete the selected row?\n\nNote: This will also unselect the respective extra fields!"
        confirmed = message_box_utils.warning_dialog(title, text, parent=self._parent)

        if confirmed:
            selected_row = self.ui.note_filters_table.currentRow()
            self.ui.note_filters_table.removeRow(selected_row)
            self.notify_observers()

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
        note_type_cbox.currentIndexChanged.connect(self.notify_observers)

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

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default note filter settings?\n\nNote: This will also unselect the respective extra fields!"
