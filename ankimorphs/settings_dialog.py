from collections.abc import Iterable, Sequence
from functools import partial
from typing import Optional, Union

from anki.models import FieldDict, NotetypeNameId
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QComboBox,
    QDialog,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
    QWidget,
)
from aqt.utils import tooltip

from ankimorphs.config import (
    AnkiMorphsConfig,
    get_all_default_configs,
    get_config,
    get_default_config,
    update_configs,
)
from ankimorphs.morphemizer import get_all_morphemizers
from ankimorphs.ui.settings_dialog_ui import Ui_SettingsDialog


def get_cbox_index(items: Iterable[str], filter_field: str) -> Optional[int]:
    for index, field in enumerate(items):
        if field == filter_field:
            return index
    return None


def get_model_cbox_index(
    items: Iterable[NotetypeNameId], filter_field: str
) -> Optional[int]:
    for index, model in enumerate(items):
        if model.name == filter_field:
            return index
    return None


class PreferencesDialog(QDialog):  # pylint:disable=too-many-public-methods
    """
    The UI comes from ankimorphs/ui/settings_dialog.ui which is used in Qt Designer,
    which is then converted to ankimorphs/ui/settings_dialog_ui.py,
    which is then imported here.

    Here we make the final adjustments that can't be made (or are hard to make) in
    Qt Designer, like setting up tables and widget-connections.
    """

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(parent)
        assert mw
        self.mw = parent  # pylint:disable=invalid-name
        self.models: Sequence[NotetypeNameId] = mw.col.models.all_names_and_ids()
        self.ui = Ui_SettingsDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore
        self.config_filters = get_config("filters")
        self.setup_note_filters_table(self.config_filters)
        self.setup_extra_fields_table(self.config_filters)
        self.populate_tags_tab()
        self.populate_parse_tab()
        self.populate_skip_tab()
        self.populate_shortcuts_tab()
        self.populate_recalc_tab()
        self.setup_buttons()
        self.ui.tabWidget.currentChanged.connect(self.tab_change)
        self.ui.ankimorphs_version_label.setText(
            f"AnkiMorphs version: {mw.ANKIMORPHS_VERSION}"  # type: ignore
        )

    def setup_note_filters_table(
        self, config_filters: dict[str, Union[str, int, bool, list[str]]]
    ) -> None:
        self.ui.note_filters_table.setColumnWidth(0, 150)
        self.ui.note_filters_table.setColumnWidth(3, 150)
        self.ui.note_filters_table.setRowCount(len(config_filters))
        self.ui.note_filters_table.setAlternatingRowColors(True)

        for row, am_filter in enumerate(config_filters):
            self.set_note_filters_table_row(row, am_filter)

    def set_note_filters_table_row(  # pylint:disable=too-many-locals
        self, row: int, config_filter: dict[str, Union[str, int, bool, list[str]]]
    ) -> None:
        assert mw

        self.ui.note_filters_table.setRowHeight(row, 35)

        note_type_cbox = QComboBox(self.ui.note_filters_table)
        note_type_cbox.addItems([model.name for model in self.models])
        note_type_name_index = get_model_cbox_index(
            self.models, config_filter["note_type"]
        )
        if note_type_name_index is not None:
            note_type_cbox.setCurrentIndex(note_type_name_index)

        current_model_id = self.models[note_type_cbox.currentIndex()].id
        note_type = mw.col.models.get(current_model_id)

        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)
        field_cbox = QComboBox(self.ui.note_filters_table)
        field_cbox.addItems(fields)
        field_cbox_index = get_cbox_index(fields, config_filter["field"])
        if field_cbox_index is not None:
            field_cbox.setCurrentIndex(field_cbox_index)

        # Fields are dependent on note-type
        note_type_cbox.currentIndexChanged.connect(
            partial(self.update_fields_cbox, field_cbox, note_type_cbox)
        )

        morphemizer_cbox = QComboBox(self.ui.note_filters_table)
        morphemizers = get_all_morphemizers()
        morphemizers = [mizer.get_description() for mizer in morphemizers]
        morphemizer_cbox.addItems(morphemizers)
        morphemizer_cbox_index = get_cbox_index(
            morphemizers, config_filter["morphemizer"]
        )
        if morphemizer_cbox_index is not None:
            morphemizer_cbox.setCurrentIndex(morphemizer_cbox_index)

        read_checkbox = QCheckBox()
        read_checkbox.setChecked(config_filter["read"])
        read_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

        modify_checkbox = QCheckBox()
        modify_checkbox.setChecked(config_filter["modify"])
        modify_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

        tags = ", ".join(config_filter["tags"])

        self.ui.note_filters_table.setCellWidget(row, 0, note_type_cbox)
        self.ui.note_filters_table.setItem(row, 1, QTableWidgetItem(tags))
        self.ui.note_filters_table.setCellWidget(row, 2, field_cbox)
        self.ui.note_filters_table.setCellWidget(row, 3, morphemizer_cbox)
        self.ui.note_filters_table.setCellWidget(row, 4, read_checkbox)
        self.ui.note_filters_table.setCellWidget(row, 5, modify_checkbox)

    def setup_extra_fields_table(
        self, config_filters: dict[str, Union[str, int, bool, list[str]]]
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
        self, row: int, config_filters: dict[str, Union[str, int, bool, list[str]]]
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
        note_type = mw.col.models.get(current_model_id)

        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)

        matching_filter = None
        for config_filter in config_filters:
            if note_type_text == config_filter["note_type"]:
                matching_filter = config_filter
                break

        focus_morph_cbox = QComboBox(self.ui.extra_fields_table)
        focus_morph_cbox.addItems(["(none)"])
        focus_morph_cbox.addItems(fields)

        if matching_filter is not None:
            focus_morph_cbox_index = get_cbox_index(
                fields, matching_filter["focus_morph"]
            )
            if focus_morph_cbox_index is not None:
                focus_morph_cbox_index += 1  # to offset the added (none) item
                focus_morph_cbox.setCurrentIndex(focus_morph_cbox_index)

        highlighted_cbox = QComboBox(self.ui.extra_fields_table)
        highlighted_cbox.addItems(["(none)"])
        highlighted_cbox.addItems(fields)

        if matching_filter is not None:
            highlighted_cbox_cbox_index = get_cbox_index(
                fields, matching_filter["highlighted"]
            )
            if highlighted_cbox_cbox_index is not None:
                highlighted_cbox_cbox_index += 1  # to offset the added (none) item
                highlighted_cbox.setCurrentIndex(highlighted_cbox_cbox_index)

        difficulty_cbox = QComboBox(self.ui.extra_fields_table)
        difficulty_cbox.addItems(["(none)"])
        difficulty_cbox.addItems(fields)

        if matching_filter is not None:
            difficulty_cbox_cbox_index = get_cbox_index(
                fields, matching_filter["difficulty"]
            )
            if difficulty_cbox_cbox_index is not None:
                difficulty_cbox_cbox_index += 1  # to offset the added (none) item
                difficulty_cbox.setCurrentIndex(difficulty_cbox_cbox_index)

        self.ui.extra_fields_table.setItem(row, 0, QTableWidgetItem(note_type_text))
        self.ui.extra_fields_table.setCellWidget(row, 1, focus_morph_cbox)
        self.ui.extra_fields_table.setCellWidget(row, 2, highlighted_cbox)
        self.ui.extra_fields_table.setCellWidget(row, 3, difficulty_cbox)

    def populate_tags_tab(self) -> None:
        am_config = AnkiMorphsConfig()

        self.ui.ripe_tag_input.setText(am_config.tag_ripe)
        self.ui.budding_tag_input.setText(am_config.tag_budding)
        self.ui.stale_tag_input.setText(am_config.tag_stale)

    def restore_tags_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default tags settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.ripe_tag_input.setText(get_default_config("tag_ripe"))
        self.ui.budding_tag_input.setText(get_default_config("tag_budding"))
        self.ui.stale_tag_input.setText(get_default_config("tag_stale"))

    def populate_parse_tab(self) -> None:
        am_config = AnkiMorphsConfig()

        self.ui.parse_ignore_bracket_contents_input.setChecked(
            am_config.parse_ignore_bracket_contents
        )
        self.ui.parse_ignore_round_bracket_contents_input.setChecked(
            am_config.parse_ignore_round_bracket_contents
        )
        self.ui.parse_ignore_slim_round_bracket_contents_input.setChecked(
            am_config.parse_ignore_slim_round_bracket_contents
        )
        self.ui.parse_ignore_proper_nouns_input.setChecked(
            am_config.parse_ignore_proper_nouns
        )
        self.ui.parse_ignore_suspended_cards_content_input.setChecked(
            am_config.parse_ignore_suspended_cards_content
        )

    def populate_shortcuts_tab(self) -> None:
        am_config = AnkiMorphsConfig()

        self.ui.shortcut_browse_same_ripe_input.setText(
            am_config.shortcut_browse_same_unknown_ripe.toString()
        )
        self.ui.shortcut_browse_same_ripe_budding_input.setText(
            am_config.shortcut_browse_same_unknown_ripe_budding.toString()
        )
        self.ui.shortcut_known_and_skip_input.setText(
            am_config.shortcut_set_known_and_skip.toString()
        )
        self.ui.shortcut_learn_now_input.setText(
            am_config.shortcut_learn_now.toString()
        )
        self.ui.shortcut_view_morphs_input.setText(
            am_config.shortcut_view_morphemes.toString()
        )

    def restore_parse_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default parse settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.parse_ignore_bracket_contents_input.setChecked(
            get_default_config("parse_ignore_bracket_contents")
        )
        self.ui.parse_ignore_round_bracket_contents_input.setChecked(
            get_default_config("parse_ignore_round_bracket_contents")
        )
        self.ui.parse_ignore_slim_round_bracket_contents_input.setChecked(
            get_default_config("parse_ignore_slim_round_bracket_contents")
        )
        self.ui.parse_ignore_proper_nouns_input.setChecked(
            get_default_config("parse_ignore_proper_nouns")
        )
        self.ui.parse_ignore_suspended_cards_content_input.setChecked(
            get_default_config("parse_ignore_suspended_cards_content")
        )

    def restore_shortcuts_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default shortcuts settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.shortcut_browse_same_ripe_input.setText(
            get_default_config("shortcut_browse_same_unknown_ripe")
        )
        self.ui.shortcut_browse_same_ripe_budding_input.setText(
            get_default_config("shortcut_browse_same_unknown_ripe_budding")
        )
        self.ui.shortcut_known_and_skip_input.setText(
            get_default_config("shortcut_set_known_and_skip")
        )
        self.ui.shortcut_learn_now_input.setText(
            get_default_config("shortcut_learn_now")
        )
        self.ui.shortcut_view_morphs_input.setText(
            get_default_config("shortcut_view_morphemes")
        )

    def populate_recalc_tab(self) -> None:
        am_config = AnkiMorphsConfig()

        self.ui.preferred_sentence_length_input.setValue(
            am_config.recalc_preferred_sentence_length
        )
        self.ui.recalc_unknown_morphs_count_input.setValue(
            am_config.recalc_unknown_morphs_count
        )
        self.ui.recalc_before_sync_input.setChecked(am_config.recalc_before_sync)
        self.ui.recalc_prioritize_collection_input.setChecked(
            am_config.recalc_prioritize_collection
        )
        self.ui.recalc_prioritize_textfile_input.setChecked(
            am_config.recalc_prioritize_textfile
        )

    def restore_recalc_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default recalc settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.preferred_sentence_length_input.setValue(
            get_default_config("recalc_preferred_sentence_length")
        )
        self.ui.recalc_unknown_morphs_count_input.setValue(
            get_default_config("recalc_unknown_morphs_count")
        )
        self.ui.recalc_before_sync_input.setChecked(
            get_default_config("recalc_before_sync")
        )
        self.ui.recalc_prioritize_collection_input.setChecked(
            get_default_config("recalc_prioritize_collection")
        )
        self.ui.recalc_prioritize_textfile_input.setChecked(
            get_default_config("recalc_prioritize_textfile")
        )

    def populate_skip_tab(self) -> None:
        am_config = AnkiMorphsConfig()

        self.ui.skip_stale_cards_input.setChecked(am_config.skip_stale_cards)
        self.ui.skip_unknown_morph_seen_today_cards_input.setChecked(
            am_config.skip_unknown_morph_seen_today_cards
        )
        self.ui.skip_show_num_of_skipped_cards_input.setChecked(
            am_config.skip_show_num_of_skipped_cards
        )

    def restore_skip_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default skip settings?"
            confirmed = self.warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.skip_stale_cards_input.setChecked(
            get_default_config("skip_stale_cards")
        )
        self.ui.skip_unknown_morph_seen_today_cards_input.setChecked(
            get_default_config("skip_unknown_morph_seen_today_cards")
        )
        self.ui.skip_show_num_of_skipped_cards_input.setChecked(
            get_default_config("skip_show_num_of_skipped_cards")
        )

    def restore_all_defaults(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to restore <b>all</b> default settings?"
        confirmed = self.warning_dialog(title, text)

        if confirmed:
            default_configs = get_all_default_configs()
            assert default_configs
            default_filters = default_configs["filters"]
            self.setup_note_filters_table(default_filters)
            self.setup_extra_fields_table(default_filters)
            self.restore_tags_defaults(skip_confirmation=True)
            self.restore_parse_defaults(skip_confirmation=True)
            self.restore_skip_defaults(skip_confirmation=True)
            self.restore_recalc_defaults(skip_confirmation=True)
            self.restore_shortcuts_defaults(skip_confirmation=True)

    def setup_buttons(self) -> None:
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
        selected_row = self.ui.note_filters_table.currentRow()
        self.ui.note_filters_table.removeRow(selected_row)

    def add_new_row(self) -> None:
        self.ui.note_filters_table.setRowCount(
            self.ui.note_filters_table.rowCount() + 1
        )
        config_filter = get_default_config("filters")[0]
        row = self.ui.note_filters_table.rowCount() - 1
        self.set_note_filters_table_row(row, config_filter)

    def save_to_config(self) -> None:  # pylint:disable=too-many-locals
        new_config = {
            "tag_ripe": self.ui.ripe_tag_input.text(),
            "tag_budding": self.ui.budding_tag_input.text(),
            "tag_stale": self.ui.stale_tag_input.text(),
            "shortcut_browse_same_unknown_ripe": self.ui.shortcut_browse_same_ripe_input.text(),
            "shortcut_browse_same_unknown_ripe_budding": self.ui.shortcut_browse_same_ripe_budding_input.text(),
            "shortcut_set_known_and_skip": self.ui.shortcut_known_and_skip_input.text(),
            "shortcut_learn_now": self.ui.shortcut_learn_now_input.text(),
            "shortcut_view_morphemes": self.ui.shortcut_view_morphs_input.text(),
            "recalc_preferred_sentence_length": self.ui.preferred_sentence_length_input.value(),
            "recalc_unknown_morphs_count": self.ui.recalc_unknown_morphs_count_input.value(),
            "recalc_before_sync": self.ui.recalc_before_sync_input.isChecked(),
            "recalc_prioritize_collection": self.ui.recalc_prioritize_collection_input.isChecked(),
            "recalc_prioritize_textfile": self.ui.recalc_prioritize_textfile_input.isChecked(),
            "parse_ignore_bracket_contents": self.ui.parse_ignore_bracket_contents_input.isChecked(),
            "parse_ignore_round_bracket_contents": self.ui.parse_ignore_round_bracket_contents_input.isChecked(),
            "parse_ignore_slim_round_bracket_contents": self.ui.parse_ignore_slim_round_bracket_contents_input.isChecked(),
            "parse_ignore_proper_nouns": self.ui.parse_ignore_proper_nouns_input.isChecked(),
            "parse_ignore_suspended_cards_content": self.ui.parse_ignore_suspended_cards_content_input.isChecked(),
            "skip_stale_cards": self.ui.skip_stale_cards_input.isChecked(),
            "skip_unknown_morph_seen_today_cards": self.ui.skip_unknown_morph_seen_today_cards_input.isChecked(),
            "skip_show_num_of_skipped_cards": self.ui.skip_show_num_of_skipped_cards_input.isChecked(),
        }

        filters = []
        rows = self.ui.note_filters_table.rowCount()
        for row in range(rows):
            note_type_widget: Optional[QWidget] = self.ui.note_filters_table.cellWidget(
                row, 0
            )
            assert isinstance(note_type_widget, QComboBox)
            note_type_cbox: QComboBox = note_type_widget

            tags_widget: Optional[QTableWidgetItem] = self.ui.note_filters_table.item(
                row, 1
            )
            assert tags_widget

            field_general_widget: Optional[
                QWidget
            ] = self.ui.note_filters_table.cellWidget(row, 2)
            assert isinstance(field_general_widget, QComboBox)
            field_cbox: QComboBox = field_general_widget

            morphemizer_general_widget: Optional[
                QWidget
            ] = self.ui.note_filters_table.cellWidget(row, 3)
            assert isinstance(morphemizer_general_widget, QComboBox)
            morphemizer_widget: QComboBox = morphemizer_general_widget

            read_general_widget: Optional[
                QWidget
            ] = self.ui.note_filters_table.cellWidget(row, 4)
            assert isinstance(read_general_widget, QCheckBox)
            read_widget: QCheckBox = read_general_widget

            modify_general_widget: Optional[
                QWidget
            ] = self.ui.note_filters_table.cellWidget(row, 5)
            assert isinstance(modify_general_widget, QCheckBox)
            modify_widget: QCheckBox = modify_general_widget

            focus_morph_general_widget: Optional[
                QWidget
            ] = self.ui.extra_fields_table.cellWidget(row, 1)
            assert isinstance(focus_morph_general_widget, QComboBox)
            focus_morph_widget: QComboBox = focus_morph_general_widget

            highlighted_general_widget: Optional[
                QWidget
            ] = self.ui.extra_fields_table.cellWidget(row, 2)
            assert isinstance(highlighted_general_widget, QComboBox)
            highlighted_widget: QComboBox = highlighted_general_widget

            difficulty_general_widget: Optional[
                QWidget
            ] = self.ui.extra_fields_table.cellWidget(row, 3)
            assert isinstance(difficulty_general_widget, QComboBox)
            difficulty_widget: QComboBox = difficulty_general_widget

            assert difficulty_widget

            tags = tags_widget.text().split(",")
            tags = [tag.strip() for tag in tags]

            _filter = {
                "note_type": note_type_cbox.itemText(note_type_cbox.currentIndex()),
                "note_type_id": self.models[note_type_cbox.currentIndex()].id,
                "tags": tags,
                "field": field_cbox.itemText(field_cbox.currentIndex()),
                "morphemizer": morphemizer_widget.itemText(
                    morphemizer_widget.currentIndex()
                ),
                "read": read_widget.isChecked(),
                "modify": modify_widget.isChecked(),
                "focus_morph": focus_morph_widget.itemText(
                    focus_morph_widget.currentIndex()
                ),
                "highlighted": highlighted_widget.itemText(
                    highlighted_widget.currentIndex()
                ),
                "difficulty": difficulty_widget.itemText(
                    difficulty_widget.currentIndex()
                ),
            }
            filters.append(_filter)
        new_config["filters"] = filters
        update_configs(new_config)
        self.config_filters = get_config("filters")
        tooltip("Please recalc to avoid unexpected behaviour", parent=mw)

    def update_fields_cbox(
        self, field_cbox: QComboBox, note_type_cbox: QComboBox
    ) -> None:
        assert mw
        current_model_id = self.models[note_type_cbox.currentIndex()].id
        note_type = mw.col.models.get(current_model_id)
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
            self.setup_extra_fields_table(self.config_filters)

    def warning_dialog(self, title: str, text: str) -> bool:
        warning_box = QMessageBox(self)
        warning_box.setWindowTitle(title)
        warning_box.setIcon(QMessageBox.Icon.Warning)
        warning_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        warning_box.setText(text)
        answer = warning_box.exec()
        if answer == QMessageBox.StandardButton.Yes:
            tooltip("Remember to save!", parent=mw)
            return True
        return False


def main() -> None:
    mw.ankimorphs_preferences_dialog = PreferencesDialog(mw)  # type: ignore
    mw.ankimorphs_preferences_dialog.exec()  # type: ignore
