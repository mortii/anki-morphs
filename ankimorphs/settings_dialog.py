from collections.abc import Iterable, Sequence
from functools import partial
from pathlib import Path
from typing import Optional

from anki.models import FieldDict, NotetypeId, NotetypeNameId
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QComboBox,
    QDialog,
    QMainWindow,
    QMessageBox,
    Qt,
    QTableWidgetItem,
    QWidget,
)
from aqt.utils import tooltip

from .config import (
    AnkiMorphsConfig,
    AnkiMorphsConfigFilter,
    FilterTypeAlias,
    update_configs,
)
from .morphemizer import get_all_morphemizers
from .ui.settings_dialog_ui import Ui_SettingsDialog


def main() -> None:
    mw.ankimorphs_settings_dialog = SettingsDialog(mw)  # type: ignore[union-attr]
    mw.ankimorphs_settings_dialog.exec()  # type: ignore[union-attr]


class SettingsDialog(QDialog):
    # The UI comes from ankimorphs/ui/settings_dialog.ui which is used in Qt Designer,
    # which is then converted to ankimorphs/ui/settings_dialog_ui.py,
    # which is then imported here.
    #
    # Here we make the final adjustments that can't be made (or are hard to make) in
    # Qt Designer, like setting up tables and widget-connections.

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(parent)
        assert mw
        self.mw = parent  # pylint:disable=invalid-name
        self.models: Sequence[NotetypeNameId] = mw.col.models.all_names_and_ids()
        self.ui = Ui_SettingsDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.config = AnkiMorphsConfig()
        self._morphemizers = get_all_morphemizers()
        self._default_config = AnkiMorphsConfig(is_default=True)
        self._setup_note_filters_table(self.config.filters)
        self._setup_extra_fields_table(self.config.filters)
        self._populate_tags_tab()
        self._populate_parse_tab()
        self._populate_skip_tab()
        self._populate_shortcuts_tab()
        self._populate_recalc_tab()
        self._setup_buttons()
        self.ui.tabWidget.currentChanged.connect(self.tab_change)

        # Semantic Versioning https://semver.org/
        self.ui.ankimorphs_version_label.setText("AnkiMorphs version: 0.6.4-alpha")

    def _setup_note_filters_table(
        self, config_filters: list[AnkiMorphsConfigFilter]
    ) -> None:
        self.ui.note_filters_table.setColumnWidth(0, 150)  # note type column
        self.ui.note_filters_table.setColumnWidth(3, 150)  # morphemizer column
        self.ui.note_filters_table.setColumnWidth(4, 150)  # prioritizing column
        self.ui.note_filters_table.setRowCount(len(config_filters))
        self.ui.note_filters_table.setAlternatingRowColors(True)

        for row, am_filter in enumerate(config_filters):
            self.set_note_filters_table_row(row, am_filter)

    def set_note_filters_table_row(  # pylint:disable=too-many-locals
        self, row: int, config_filter: AnkiMorphsConfigFilter
    ) -> None:
        assert mw
        self.ui.note_filters_table.setRowHeight(row, 35)

        note_type_cbox = QComboBox(self.ui.note_filters_table)
        note_type_cbox.addItems([model.name for model in self.models])
        note_type_name_index = _get_model_cbox_index(
            self.models, config_filter.note_type
        )
        if note_type_name_index is not None:
            note_type_cbox.setCurrentIndex(note_type_name_index)

        current_model_id = self.models[note_type_cbox.currentIndex()].id
        note_type = mw.col.models.get(NotetypeId(int(current_model_id)))
        assert note_type

        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)
        field_cbox = QComboBox(self.ui.note_filters_table)
        field_cbox.addItems(fields)
        field_cbox_index = _get_cbox_index(fields, config_filter.field)
        if field_cbox_index is not None:
            field_cbox.setCurrentIndex(field_cbox_index)

        # Fields are dependent on note-type
        note_type_cbox.currentIndexChanged.connect(
            partial(self.update_fields_cbox, field_cbox, note_type_cbox)
        )

        morphemizer_cbox = QComboBox(self.ui.note_filters_table)
        morphemizers = [mizer.get_description() for mizer in self._morphemizers]
        morphemizer_cbox.addItems(morphemizers)
        morphemizer_cbox_index = _get_cbox_index(
            morphemizers, config_filter.morphemizer_description
        )
        if morphemizer_cbox_index is not None:
            morphemizer_cbox.setCurrentIndex(morphemizer_cbox_index)

        morph_priority_cbox = QComboBox(self.ui.note_filters_table)
        frequency_files: list[str] = _get_frequency_files()
        morph_priority_cbox.addItems(["Collection frequency"])
        morph_priority_cbox.addItems(frequency_files)
        morph_priority_cbox_index = _get_cbox_index(
            frequency_files, config_filter.morph_priority
        )
        if morph_priority_cbox_index is not None:
            morph_priority_cbox_index += 1  # to offset the added "Collection frequency"
            morph_priority_cbox.setCurrentIndex(morph_priority_cbox_index)

        read_checkbox = QCheckBox()
        read_checkbox.setChecked(config_filter.read)
        read_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

        modify_checkbox = QCheckBox()
        modify_checkbox.setChecked(config_filter.modify)
        modify_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

        tags = ", ".join(config_filter.tags)

        self.ui.note_filters_table.setCellWidget(row, 0, note_type_cbox)
        self.ui.note_filters_table.setItem(row, 1, QTableWidgetItem(tags))
        self.ui.note_filters_table.setCellWidget(row, 2, field_cbox)
        self.ui.note_filters_table.setCellWidget(row, 3, morphemizer_cbox)
        self.ui.note_filters_table.setCellWidget(row, 4, morph_priority_cbox)
        self.ui.note_filters_table.setCellWidget(row, 5, read_checkbox)
        self.ui.note_filters_table.setCellWidget(row, 6, modify_checkbox)

    def _setup_extra_fields_table(
        self, config_filters: list[AnkiMorphsConfigFilter]
    ) -> None:
        self.ui.extra_fields_table.setColumnWidth(0, 150)
        self.ui.extra_fields_table.setColumnWidth(1, 120)
        self.ui.extra_fields_table.setColumnWidth(2, 120)
        self.ui.extra_fields_table.setAlternatingRowColors(True)

        note_filters_table_rows = self.ui.note_filters_table.rowCount()
        self.ui.extra_fields_table.setRowCount(note_filters_table_rows)

        for row in range(note_filters_table_rows):
            self.set_extra_fields_table_row(row, config_filters)

    def set_extra_fields_table_row(  # pylint:disable=too-many-locals
        self, row: int, config_filters: list[AnkiMorphsConfigFilter]
    ) -> None:
        assert mw

        self.ui.extra_fields_table.setRowHeight(row, 35)

        note_type_general_widget: Optional[
            QWidget
        ] = self.ui.note_filters_table.cellWidget(row, 0)
        assert isinstance(note_type_general_widget, QComboBox)
        note_type_widget: QComboBox = note_type_general_widget
        note_type_text = note_type_widget.itemText(note_type_widget.currentIndex())
        current_model_id = self.models[note_type_widget.currentIndex()].id
        note_type = mw.col.models.get(NotetypeId(int(current_model_id)))
        assert note_type is not None
        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)

        matching_filter = None
        for config_filter in config_filters:
            if note_type_text == config_filter.note_type:
                matching_filter = config_filter
                break

        unknowns_cbox = QComboBox(self.ui.extra_fields_table)
        unknowns_cbox.addItems(["(none)"])
        unknowns_cbox.addItems(fields)

        if matching_filter is not None:
            unknowns_cbox_index = _get_cbox_index(
                fields, matching_filter.unknowns_field
            )
            if unknowns_cbox_index is not None:
                unknowns_cbox_index += 1  # to offset the added (none) item
                unknowns_cbox.setCurrentIndex(unknowns_cbox_index)

        highlighted_cbox = QComboBox(self.ui.extra_fields_table)
        highlighted_cbox.addItems(["(none)"])
        highlighted_cbox.addItems(fields)

        if matching_filter is not None:
            highlighted_cbox_cbox_index = _get_cbox_index(
                fields, matching_filter.highlighted_field
            )
            if highlighted_cbox_cbox_index is not None:
                highlighted_cbox_cbox_index += 1  # to offset the added (none) item
                highlighted_cbox.setCurrentIndex(highlighted_cbox_cbox_index)

        difficulty_cbox = QComboBox(self.ui.extra_fields_table)
        difficulty_cbox.addItems(["(none)"])
        difficulty_cbox.addItems(fields)

        if matching_filter is not None:
            difficulty_cbox_cbox_index = _get_cbox_index(
                fields, matching_filter.difficulty_field
            )
            if difficulty_cbox_cbox_index is not None:
                difficulty_cbox_cbox_index += 1  # to offset the added (none) item
                difficulty_cbox.setCurrentIndex(difficulty_cbox_cbox_index)

        self.ui.extra_fields_table.setItem(row, 0, QTableWidgetItem(note_type_text))
        self.ui.extra_fields_table.setCellWidget(row, 1, unknowns_cbox)
        self.ui.extra_fields_table.setCellWidget(row, 2, highlighted_cbox)
        self.ui.extra_fields_table.setCellWidget(row, 3, difficulty_cbox)

    def _populate_tags_tab(self) -> None:
        self.ui.ready_tag_input.setText(self.config.tag_ready)
        self.ui.not_read_tag_input.setText(self.config.tag_not_ready)
        self.ui.known_tag_input.setText(self.config.tag_known)

    def restore_tags_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default tags settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.ready_tag_input.setText(self._default_config.tag_ready)
        self.ui.not_read_tag_input.setText(self._default_config.tag_not_ready)
        self.ui.known_tag_input.setText(self._default_config.tag_known)

    def _populate_parse_tab(self) -> None:
        self.ui.parse_ignore_bracket_contents_input.setChecked(
            self.config.parse_ignore_bracket_contents
        )
        self.ui.parse_ignore_round_bracket_contents_input.setChecked(
            self.config.parse_ignore_round_bracket_contents
        )
        self.ui.parse_ignore_slim_round_bracket_contents_input.setChecked(
            self.config.parse_ignore_slim_round_bracket_contents
        )
        self.ui.parse_ignore_names_morphemizer_input.setChecked(
            self.config.parse_ignore_names_morphemizer
        )
        self.ui.parse_ignore_names_textfile_input.setChecked(
            self.config.parse_ignore_names_textfile
        )
        self.ui.parse_ignore_suspended_cards_content_input.setChecked(
            self.config.parse_ignore_suspended_cards_content
        )

    def _populate_shortcuts_tab(self) -> None:
        self.ui.shortcut_recalc_input.setKeySequence(self.config.shortcut_recalc)
        self.ui.shortcut_settings_input.setKeySequence(self.config.shortcut_settings)
        self.ui.shortcut_browse_ready_same_unknown_input.setKeySequence(
            self.config.shortcut_browse_ready_same_unknown.toString()
        )
        self.ui.shortcut_browse_all_same_unknown_input.setKeySequence(
            self.config.shortcut_browse_all_same_unknown.toString()
        )
        self.ui.shortcut_known_and_skip_input.setKeySequence(
            self.config.shortcut_set_known_and_skip.toString()
        )
        self.ui.shortcut_learn_now_input.setKeySequence(
            self.config.shortcut_learn_now.toString()
        )
        self.ui.shortcut_view_morphs_input.setKeySequence(
            self.config.shortcut_view_morphemes.toString()
        )

    def restore_parse_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default parse settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.parse_ignore_bracket_contents_input.setChecked(
            self._default_config.parse_ignore_bracket_contents
        )
        self.ui.parse_ignore_round_bracket_contents_input.setChecked(
            self._default_config.parse_ignore_round_bracket_contents
        )
        self.ui.parse_ignore_slim_round_bracket_contents_input.setChecked(
            self._default_config.parse_ignore_slim_round_bracket_contents
        )
        self.ui.parse_ignore_names_morphemizer_input.setChecked(
            self._default_config.parse_ignore_names_morphemizer
        )
        self.ui.parse_ignore_names_textfile_input.setChecked(
            self._default_config.parse_ignore_names_textfile
        )
        self.ui.parse_ignore_suspended_cards_content_input.setChecked(
            self._default_config.parse_ignore_suspended_cards_content
        )

    def restore_shortcuts_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default shortcuts settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.shortcut_recalc_input.setKeySequence(
            self._default_config.shortcut_recalc
        )
        self.ui.shortcut_settings_input.setKeySequence(
            self._default_config.shortcut_settings
        )
        self.ui.shortcut_browse_ready_same_unknown_input.setKeySequence(
            self._default_config.shortcut_browse_ready_same_unknown
        )
        self.ui.shortcut_browse_all_same_unknown_input.setKeySequence(
            self._default_config.shortcut_browse_all_same_unknown
        )
        self.ui.shortcut_known_and_skip_input.setKeySequence(
            self._default_config.shortcut_set_known_and_skip
        )
        self.ui.shortcut_learn_now_input.setKeySequence(
            self._default_config.shortcut_learn_now
        )
        self.ui.shortcut_view_morphs_input.setKeySequence(
            self._default_config.shortcut_view_morphemes
        )

    def _populate_recalc_tab(self) -> None:
        self.ui.recalc_interval_known_input.setValue(
            self.config.recalc_interval_for_known
        )
        self.ui.recalc_on_sync_input.setChecked(self.config.recalc_on_sync)

    #     self._populate_frequency_lists()
    #

    def restore_recalc_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default recalc settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.recalc_interval_known_input.setValue(
            self._default_config.recalc_interval_for_known
        )
        self.ui.recalc_on_sync_input.setChecked(self._default_config.recalc_on_sync)

    def _populate_skip_tab(self) -> None:
        self.ui.skip_only_known_morphs_cards_input.setChecked(
            self.config.skip_only_known_morphs_cards
        )
        self.ui.skip_unknown_morph_seen_today_cards_input.setChecked(
            self.config.skip_unknown_morph_seen_today_cards
        )
        self.ui.skip_show_num_of_skipped_cards_input.setChecked(
            self.config.skip_show_num_of_skipped_cards
        )

    def restore_skip_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default skip settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.skip_only_known_morphs_cards_input.setChecked(
            self._default_config.skip_only_known_morphs_cards
        )
        self.ui.skip_unknown_morph_seen_today_cards_input.setChecked(
            self._default_config.skip_unknown_morph_seen_today_cards
        )
        self.ui.skip_show_num_of_skipped_cards_input.setChecked(
            self._default_config.skip_show_num_of_skipped_cards
        )

    def restore_all_defaults(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to restore <b>all</b> default settings?"
        confirmed = self.warning_dialog(title, text)

        if confirmed:
            default_filters = self._default_config.filters
            self._setup_note_filters_table(default_filters)
            self._setup_extra_fields_table(default_filters)
            self.restore_tags_defaults(skip_confirmation=True)
            self.restore_parse_defaults(skip_confirmation=True)
            self.restore_skip_defaults(skip_confirmation=True)
            self.restore_recalc_defaults(skip_confirmation=True)
            self.restore_shortcuts_defaults(skip_confirmation=True)

    def _setup_buttons(self) -> None:
        self.ui.save_button.clicked.connect(self.save_to_config)
        self.ui.cancel_button.clicked.connect(self.close)
        self.ui.add_new_row_button.clicked.connect(self.add_new_row)
        self.ui.delete_row_button.clicked.connect(self.delete_row)
        self.ui.restore_tags_defaults_button.clicked.connect(self.restore_tags_defaults)
        self.ui.restore_recalc_defaults_button.clicked.connect(
            self.restore_recalc_defaults
        )
        self.ui.restore_shortcut_defaults_button.clicked.connect(
            self.restore_shortcuts_defaults
        )
        self.ui.restore_parse_defaults_button.clicked.connect(
            self.restore_parse_defaults
        )
        self.ui.restore_skip_defaults_button.clicked.connect(self.restore_skip_defaults)
        self.ui.restore_all_defaults_button.clicked.connect(self.restore_all_defaults)

    def delete_row(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to delete the selected row?"
        confirmed = self.warning_dialog(title, text)
        if confirmed:
            selected_row = self.ui.note_filters_table.currentRow()
            self.ui.note_filters_table.removeRow(selected_row)

    def add_new_row(self) -> None:
        self.ui.note_filters_table.setRowCount(
            self.ui.note_filters_table.rowCount() + 1
        )
        config_filter = self._default_config.filters[0]
        row = self.ui.note_filters_table.rowCount() - 1
        self.set_note_filters_table_row(row, config_filter)
        self._setup_extra_fields_table(self.config.filters)

    def save_to_config(self) -> None:  # pylint:disable=too-many-locals
        new_config = {
            "tag_ready": self.ui.ready_tag_input.text(),
            "tag_not_ready": self.ui.not_read_tag_input.text(),
            "tag_known": self.ui.known_tag_input.text(),
            "shortcut_browse_ready_same_unknown": self.ui.shortcut_browse_ready_same_unknown_input.keySequence().toString(),
            "shortcut_browse_all_same_unknown": self.ui.shortcut_browse_all_same_unknown_input.keySequence().toString(),
            "shortcut_set_known_and_skip": self.ui.shortcut_known_and_skip_input.keySequence().toString(),
            "shortcut_learn_now": self.ui.shortcut_learn_now_input.keySequence().toString(),
            "shortcut_view_morphemes": self.ui.shortcut_view_morphs_input.keySequence().toString(),
            "recalc_interval_for_known": self.ui.recalc_interval_known_input.value(),
            "recalc_on_sync": self.ui.recalc_on_sync_input.isChecked(),
            "parse_ignore_bracket_contents": self.ui.parse_ignore_bracket_contents_input.isChecked(),
            "parse_ignore_round_bracket_contents": self.ui.parse_ignore_round_bracket_contents_input.isChecked(),
            "parse_ignore_slim_round_bracket_contents": self.ui.parse_ignore_slim_round_bracket_contents_input.isChecked(),
            "parse_ignore_names_morphemizer": self.ui.parse_ignore_names_morphemizer_input.isChecked(),
            "parse_ignore_names_textfile": self.ui.parse_ignore_names_textfile_input.isChecked(),
            "parse_ignore_suspended_cards_content": self.ui.parse_ignore_suspended_cards_content_input.isChecked(),
            "skip_only_known_morphs_cards": self.ui.skip_only_known_morphs_cards_input.isChecked(),
            "skip_unknown_morph_seen_today_cards": self.ui.skip_unknown_morph_seen_today_cards_input.isChecked(),
            "skip_show_num_of_skipped_cards": self.ui.skip_show_num_of_skipped_cards_input.isChecked(),
        }

        filters: list[FilterTypeAlias] = []
        rows = self.ui.note_filters_table.rowCount()
        for row in range(rows):
            note_type_cbox: QComboBox = _get_cbox_widget(
                self.ui.note_filters_table.cellWidget(row, 0)
            )

            tags_widget: Optional[QTableWidgetItem] = self.ui.note_filters_table.item(
                row, 1
            )
            assert tags_widget
            tags = tags_widget.text().split(",")
            tags = [tag.strip() for tag in tags]

            field_cbox: QComboBox = _get_cbox_widget(
                self.ui.note_filters_table.cellWidget(row, 2)
            )
            morphemizer_widget: QComboBox = _get_cbox_widget(
                self.ui.note_filters_table.cellWidget(row, 3)
            )
            morph_priority_widget: QComboBox = _get_cbox_widget(
                self.ui.note_filters_table.cellWidget(row, 4)
            )
            read_widget: QCheckBox = _get_checkbox_widget(
                self.ui.note_filters_table.cellWidget(row, 5)
            )
            modify_widget: QCheckBox = _get_checkbox_widget(
                self.ui.note_filters_table.cellWidget(row, 6)
            )
            unknowns_widget: QComboBox = _get_cbox_widget(
                self.ui.extra_fields_table.cellWidget(row, 1)
            )
            highlighted_widget: QComboBox = _get_cbox_widget(
                self.ui.extra_fields_table.cellWidget(row, 2)
            )
            difficulty_widget: QComboBox = _get_cbox_widget(
                self.ui.extra_fields_table.cellWidget(row, 3)
            )

            _filter: FilterTypeAlias = {
                "note_type": note_type_cbox.itemText(note_type_cbox.currentIndex()),
                "note_type_id": self.models[note_type_cbox.currentIndex()].id,
                "tags": tags,
                "field": field_cbox.itemText(field_cbox.currentIndex()),
                "field_index": field_cbox.currentIndex(),
                "morphemizer_description": morphemizer_widget.itemText(
                    morphemizer_widget.currentIndex()
                ),
                "morphemizer_name": self._morphemizers[
                    morphemizer_widget.currentIndex()
                ].get_name(),
                "morph_priority": morph_priority_widget.itemText(
                    morph_priority_widget.currentIndex()
                ),
                "morph_priority_index": morph_priority_widget.currentIndex(),
                "read": read_widget.isChecked(),
                "modify": modify_widget.isChecked(),
                "unknowns_field": unknowns_widget.itemText(
                    unknowns_widget.currentIndex()
                ),
                "unknowns_field_index": unknowns_widget.currentIndex(),
                "highlighted_field": highlighted_widget.itemText(
                    highlighted_widget.currentIndex()
                ),
                "highlighted_field_index": highlighted_widget.currentIndex(),
                "difficulty_field": difficulty_widget.itemText(
                    difficulty_widget.currentIndex()
                ),
                "difficulty_field_index": difficulty_widget.currentIndex(),
            }
            filters.append(_filter)
        new_config["filters"] = filters

        if self.extra_fields_changed(filters):
            _title = "AnkiMorphs Warning"
            _text = (
                "You have changed your **Extra Fields** settings.\n"
                "This can potentially destroy your cards.\n\n"
                "Before saving, make sure you have done the following:\n"
                "- Read and understood the <a href='https://mortii.github.io/anki-morphs/user_guide/setup/settings/extra-fields.html'>guide</a>\n"
                "- Created a backup of your cards.\n\n"
                "Are you sure you want to save the settings?"
            )
            accepted = self.warning_dialog(
                title=_title, text=_text, display_tooltip=False
            )
            if not accepted:
                return

        update_configs(new_config)
        self.config = AnkiMorphsConfig()
        tooltip("Please recalc to avoid unexpected behaviour", parent=mw)

    def extra_fields_changed(self, new_filters: list[FilterTypeAlias]) -> bool:
        extra_fields: list[str] = [
            "unknowns_field",
            "highlighted_field",
            "difficulty_field",
        ]
        extra_fields_changed = False

        for _filter in new_filters:
            for field in extra_fields:
                if _filter[field] != "(none)":
                    extra_fields_changed = True

        if not extra_fields_changed:
            return False

        for index, old_filter in enumerate(self.config.filters):
            if index > len(new_filters) - 1:
                break

            if new_filters[index]["unknowns_field"] != old_filter.unknowns_field:
                return True
            if new_filters[index]["highlighted_field"] != old_filter.highlighted_field:
                return True
            if new_filters[index]["difficulty_field"] != old_filter.difficulty_field:
                return True

        return False

    def update_fields_cbox(
        self, field_cbox: QComboBox, note_type_cbox: QComboBox
    ) -> None:
        assert mw
        current_model_id = self.models[note_type_cbox.currentIndex()].id
        note_type = mw.col.models.get(NotetypeId(int(current_model_id)))
        assert note_type
        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)
        field_cbox.clear()
        field_cbox.addItems(fields)

    def tab_change(self, tab_index: int) -> None:
        """
        The extra fields settings are dependent on the note filters, so
        everytime the extra fields tab is opened we just re-populate it
        in case the note filters have changed.
        """
        if tab_index == 1:
            self._setup_extra_fields_table(self.config.filters)

    def warning_dialog(
        self, title: str, text: str, display_tooltip: bool = True
    ) -> bool:
        warning_box = QMessageBox(self)
        warning_box.setWindowTitle(title)
        warning_box.setIcon(QMessageBox.Icon.Warning)
        warning_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        warning_box.setText(text)
        warning_box.setTextFormat(Qt.TextFormat.MarkdownText)
        answer = warning_box.exec()
        if answer == QMessageBox.StandardButton.Yes:
            if display_tooltip:
                tooltip("Remember to save!", parent=mw)
            return True
        return False


def _get_cbox_index(items: Iterable[str], filter_field: str) -> Optional[int]:
    for index, field in enumerate(items):
        if field == filter_field:
            return index
    return None


def _get_model_cbox_index(
    items: Iterable[NotetypeNameId], filter_field: str
) -> Optional[int]:
    for index, model in enumerate(items):
        if model.name == filter_field:
            return index
    return None


def _get_cbox_widget(widget: Optional[QWidget]) -> QComboBox:
    assert isinstance(widget, QComboBox)
    return widget


def _get_checkbox_widget(widget: Optional[QWidget]) -> QCheckBox:
    assert isinstance(widget, QCheckBox)
    return widget


def _get_frequency_files() -> list[str]:
    assert mw is not None
    path_generator = Path(mw.pm.profileFolder(), "frequency-files").glob("*.csv")
    frequency_files = [file.name for file in path_generator if file.is_file()]
    return frequency_files
