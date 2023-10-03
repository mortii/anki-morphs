import pprint
from functools import partial

from anki.models import FieldDict
from aqt import mw
from aqt.qt import QCheckBox, QComboBox, QDialog, QMessageBox, QTableWidgetItem
from aqt.utils import tooltip

from ankimorphs.config import get_config, get_default_configs, update_configs
from ankimorphs.morphemizer import get_all_morphemizers
from ankimorphs.ui.preferences_dialog_ui import Ui_Dialog


class PreferencesDialog(QDialog):
    """
    The UI comes from ankimorphs/ui/preferences_dialog.ui which is used in Qt Designer,
    which is then converted to ankimorphs/ui/preferences_dialog_ui.py,
    which is then imported here.

    Here we make the final adjustments that can't be made (or are hard to make) in
    the Qt Designer, like setting up tables and widget-connections.

    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.models = None
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.ankimorphs_version_label.setText(
            f"AnkiMorphs version: {mw.ANKIMORPHS_VERSION}"
        )
        self.setup_note_filters_table()
        self.setup_extra_fields_table()
        self.setup_buttons()

        self.ui.tabWidget.currentChanged.connect(
            lambda x: self.setup_extra_fields_table() if x == 1 else None
        )

        self.populate_tags_tab()
        self.populate_shortcuts_tab()
        self.populate_recalc_tab()

    def setup_buttons(self):
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

    def restore_tags_defaults(self):
        self.ui.ripe_tag_input.setText(get_default_configs("tag_ripe"))
        self.ui.budding_tag_input.setText(get_default_configs("tag_budding"))
        self.ui.stale_tag_input.setText(get_default_configs("tag_stale"))

    def populate_tags_tab(self):
        self.ui.ripe_tag_input.setText(get_config("tag_ripe"))
        self.ui.budding_tag_input.setText(get_config("tag_budding"))
        self.ui.stale_tag_input.setText(get_config("tag_stale"))

    def delete_row(self):
        selected_row = self.ui.note_filters_table.currentRow()
        self.ui.note_filters_table.removeRow(selected_row)

    def set_note_filters_table_row(self, row, am_filter):
        self.ui.note_filters_table.setRowHeight(row, 35)

        note_type_cbox = QComboBox(self.ui.note_filters_table)
        note_type_cbox.addItems([model.name for model in self.models])
        note_type_cbox.setCurrentIndex(2)

        current_model_id = self.models[note_type_cbox.currentIndex()].id

        note_type = mw.col.models.get(current_model_id)

        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)
        field_cbox = QComboBox(self.ui.note_filters_table)
        field_cbox.addItems(fields)

        note_type_cbox.currentIndexChanged.connect(
            partial(self.update_fields_cbox, field_cbox, note_type_cbox)
        )

        morphemizer_cbox = QComboBox(self.ui.note_filters_table)
        morphemizers = get_all_morphemizers()
        morphemizers = [mizer.get_description() for mizer in morphemizers]
        morphemizer_cbox.addItems(morphemizers)

        read_checkbox = QCheckBox()
        read_checkbox.setChecked(am_filter["read"])
        read_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

        modify_checkbox = QCheckBox()
        modify_checkbox.setChecked(am_filter["modify"])
        modify_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

        tags = ", ".join(am_filter["tags"])

        self.ui.note_filters_table.setCellWidget(row, 0, note_type_cbox)
        self.ui.note_filters_table.setItem(row, 1, QTableWidgetItem(tags))
        self.ui.note_filters_table.setCellWidget(row, 2, field_cbox)
        self.ui.note_filters_table.setCellWidget(row, 3, morphemizer_cbox)
        self.ui.note_filters_table.setCellWidget(row, 4, read_checkbox)
        self.ui.note_filters_table.setCellWidget(row, 5, modify_checkbox)

    def add_new_row(self):
        self.ui.note_filters_table.setRowCount(
            self.ui.note_filters_table.rowCount() + 1
        )
        am_filter = get_config("filters")[0]  # TODO get from config.json, not meta.json
        row = self.ui.note_filters_table.rowCount() - 1
        self.set_note_filters_table_row(row, am_filter)

    def save_to_config(self):
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
        }

        update_configs(new_config)
        tooltip("Please recalc to avoid unexpected behaviour", parent=mw)

    def setup_note_filters_table(self):
        self.ui.note_filters_table.setColumnWidth(0, 150)
        self.ui.note_filters_table.setColumnWidth(3, 150)
        self.ui.note_filters_table.setRowCount(1)
        self.ui.note_filters_table.setAlternatingRowColors(True)
        self.models = mw.col.models.all_names_and_ids()

        for row, am_filter in enumerate(get_config("filters")):
            self.set_note_filters_table_row(row, am_filter)

    def update_fields_cbox(self, field_cbox, note_type_cbox):
        current_model_id = self.models[note_type_cbox.currentIndex()].id
        note_type = mw.col.models.get(current_model_id)
        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)
        field_cbox.clear()
        field_cbox.addItems(fields)

    def setup_extra_fields_table(self):
        self.ui.extra_fields_table.setColumnWidth(0, 150)
        self.ui.extra_fields_table.setColumnWidth(1, 120)
        self.ui.extra_fields_table.setColumnWidth(2, 120)
        self.ui.extra_fields_table.setRowCount(1)
        self.ui.extra_fields_table.setAlternatingRowColors(True)

        note_filters_table_rows = self.ui.note_filters_table.rowCount()

        self.ui.extra_fields_table.setRowCount(note_filters_table_rows)

        print(f"note_filters_table_rows, {note_filters_table_rows}")
        for row in range(note_filters_table_rows):
            self.set_extra_fields_table_row(row)

    def set_extra_fields_table_row(self, row):
        self.ui.extra_fields_table.setRowHeight(row, 35)

        note_type_widget = self.ui.note_filters_table.cellWidget(row, 0)
        item_text = note_type_widget.itemText(note_type_widget.currentIndex())

        current_model_id = self.models[note_type_widget.currentIndex()].id

        note_type = mw.col.models.get(current_model_id)

        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)

        focus_morph_cbox = QComboBox(self.ui.extra_fields_table)
        focus_morph_cbox.addItems(["(none)"])
        focus_morph_cbox.addItems(fields)

        highlighted_cbox = QComboBox(self.ui.extra_fields_table)
        highlighted_cbox.addItems(["(none)"])
        highlighted_cbox.addItems(fields)

        # difficulty_field = am_filter["difficulty"]
        difficulty_cbox = QComboBox(self.ui.extra_fields_table)
        difficulty_cbox.addItems(["(none)"])
        difficulty_cbox.addItems(fields)

        self.ui.extra_fields_table.setItem(row, 0, QTableWidgetItem(item_text))
        self.ui.extra_fields_table.setCellWidget(row, 1, focus_morph_cbox)
        self.ui.extra_fields_table.setCellWidget(row, 2, highlighted_cbox)
        self.ui.extra_fields_table.setCellWidget(row, 3, difficulty_cbox)

    def populate_shortcuts_tab(self):
        self.ui.shortcut_browse_same_ripe_input.setText(
            get_config("shortcut_browse_same_unknown_ripe")
        )
        self.ui.shortcut_browse_same_ripe_budding_input.setText(
            get_config("shortcut_browse_same_unknown_ripe_budding")
        )
        self.ui.shortcut_known_and_skip_input.setText(
            get_config("shortcut_set_known_and_skip")
        )
        self.ui.shortcut_learn_now_input.setText(get_config("shortcut_learn_now"))
        self.ui.shortcut_view_morphs_input.setText(
            get_config("shortcut_view_morphemes")
        )

    def warning_dialog(self, title, text) -> bool:
        answer = QMessageBox.warning(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            return True
        return False

    def restore_shortcuts_defaults(self):
        title = "Confirmation"
        text = "Are you sure you want to restore default shortcut settings?"
        confirmed = self.warning_dialog(title, text)

        if confirmed:
            self.ui.shortcut_browse_same_ripe_input.setText(
                get_default_configs("shortcut_browse_same_unknown_ripe")
            )
            self.ui.shortcut_browse_same_ripe_budding_input.setText(
                get_default_configs("shortcut_browse_same_unknown_ripe_budding")
            )
            self.ui.shortcut_known_and_skip_input.setText(
                get_default_configs("shortcut_set_known_and_skip")
            )
            self.ui.shortcut_learn_now_input.setText(
                get_default_configs("shortcut_learn_now")
            )
            self.ui.shortcut_view_morphs_input.setText(
                get_default_configs("shortcut_view_morphemes")
                # self.close()
            )

    def populate_recalc_tab(self):
        self.ui.preferred_sentence_length_input.setValue(
            get_config("recalc_preferred_sentence_length")
        )
        self.ui.recalc_unknown_morphs_count_input.setValue(
            get_config("recalc_unknown_morphs_count")
        )
        self.ui.recalc_before_sync_input.setChecked(get_config("recalc_before_sync"))
        self.ui.recalc_prioritize_collection_input.setChecked(
            get_config("recalc_prioritize_collection")
        )
        self.ui.recalc_prioritize_textfile_input.setChecked(
            get_config("recalc_prioritize_textfile")
        )

    def restore_recalc_defaults(self):
        self.ui.preferred_sentence_length_input.setValue(
            get_default_configs("recalc_preferred_sentence_length")
        )
        self.ui.recalc_unknown_morphs_count_input.setValue(
            get_default_configs("recalc_unknown_morphs_count")
        )
        self.ui.recalc_before_sync_input.setChecked(
            get_default_configs("recalc_before_sync")
        )
        self.ui.recalc_prioritize_collection_input.setChecked(
            get_default_configs("recalc_prioritize_collection")
        )
        self.ui.recalc_prioritize_textfile_input.setChecked(
            get_default_configs("recalc_prioritize_textfile")
        )


def main():
    mw.ankimorphs_preferences_dialog = PreferencesDialog(mw)
    mw.ankimorphs_preferences_dialog.exec()
