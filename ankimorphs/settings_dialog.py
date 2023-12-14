import json
from collections.abc import Iterable, Sequence
from functools import partial
from pathlib import Path
from typing import Callable, Optional

import aqt
from anki.models import FieldDict, NotetypeId, NotetypeNameId
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QMessageBox,
    QStyle,
    QTableWidgetItem,
)
from aqt.utils import tooltip

from . import ankimorphs_globals
from .config import (
    AnkiMorphsConfig,
    AnkiMorphsConfigFilter,
    FilterTypeAlias,
    update_configs,
)
from .message_box_utils import show_warning_box
from .morphemizer import get_all_morphemizers
from .table_utils import (
    get_checkbox_widget,
    get_combobox_index,
    get_combobox_widget,
    get_table_item,
)
from .tag_selection_dialog import TagSelectionDialog
from .ui.settings_dialog_ui import Ui_SettingsDialog


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
        self.models: Sequence[NotetypeNameId] = mw.col.models.all_names_and_ids()
        self.ui = Ui_SettingsDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.ui.note_filters_table.cellClicked.connect(self._tags_cell_clicked)

        # disables manual editing of in note filter table
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
        self._config = AnkiMorphsConfig()
        self._default_config = AnkiMorphsConfig(is_default=True)
        self._setup_note_filters_table(self._config.filters)
        self._populate_extra_fields_tab()
        self._populate_tags_tab()
        self._populate_parse_tab()
        self._populate_skip_tab()
        self._populate_shortcuts_tab()
        self._populate_recalc_tab()
        self._setup_buttons()

        # the tag selector dialog is spawned from the settings dialog,
        # so it makes the most sense to store it here instead of __init__.py
        self.tag_selector = TagSelectionDialog()
        self.tag_selector.ui.applyButton.clicked.connect(self._update_note_filter_tags)
        # close the tag selector dialog when the settings dialog closes
        self.finished.connect(self.tag_selector.close)

        # Have the Anki dialog manager handle the tag selector dialog
        aqt.dialogs.register_dialog(
            name=ankimorphs_globals.TAG_SELECTOR_DIALOG_NAME,
            creator=self.tag_selector.show,
        )

        # Semantic Versioning https://semver.org/
        self.ui.ankimorphs_version_label.setText("AnkiMorphs version: 0.9.0-alpha")

        self.show()

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

    def _set_note_filters_table_row(  # pylint:disable=too-many-locals
        self, row: int, config_filter: AnkiMorphsConfigFilter
    ) -> None:
        assert mw
        self.ui.note_filters_table.setRowHeight(row, 35)

        note_type_cbox = QComboBox(self.ui.note_filters_table)
        note_type_cbox.addItems([model.name for model in self.models])
        note_type_name_index = self._get_model_combobox_index(
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
        field_cbox_index = get_combobox_index(fields, config_filter.field)
        if field_cbox_index is not None:
            field_cbox.setCurrentIndex(field_cbox_index)

        # Fields are dependent on note-type
        note_type_cbox.currentIndexChanged.connect(
            partial(self._update_fields_cbox, field_cbox, note_type_cbox)
        )

        morphemizer_cbox = QComboBox(self.ui.note_filters_table)
        morphemizers = [mizer.get_description() for mizer in self._morphemizers]
        morphemizer_cbox.addItems(morphemizers)
        morphemizer_cbox_index = get_combobox_index(
            morphemizers, config_filter.morphemizer_description
        )
        if morphemizer_cbox_index is not None:
            morphemizer_cbox.setCurrentIndex(morphemizer_cbox_index)

        morph_priority_cbox = QComboBox(self.ui.note_filters_table)
        frequency_files: list[str] = self._get_frequency_files()
        morph_priority_cbox.addItems(["Collection frequency"])
        morph_priority_cbox.addItems(frequency_files)
        morph_priority_cbox_index = get_combobox_index(
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

    def _populate_extra_fields_tab(self) -> None:
        self.ui.extraUnknownsCheckBox.setChecked(self._config.extra_unknowns)
        self.ui.extraUnknownsCountCheckBox.setChecked(self._config.extra_unknowns_count)
        self.ui.extraHighlightedCheckBox.setChecked(self._config.extra_highlighted)
        self.ui.extraDifficultyCheckBox.setChecked(self._config.extra_difficulty)

    def _restore_extra_fields_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default extra fields settings?"
            confirmed = self._warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.extraUnknownsCheckBox.setChecked(self._default_config.extra_unknowns)
        self.ui.extraUnknownsCountCheckBox.setChecked(
            self._default_config.extra_unknowns_count
        )
        self.ui.extraHighlightedCheckBox.setChecked(
            self._default_config.extra_highlighted
        )
        self.ui.extraDifficultyCheckBox.setChecked(
            self._default_config.extra_difficulty
        )

    def _populate_tags_tab(self) -> None:
        self.ui.tagReadyLineEdit.setText(self._config.tag_ready)
        self.ui.tagNotReadyLineEdit.setText(self._config.tag_not_ready)
        self.ui.tagKnownAutomaticallyLineEdit.setText(
            self._config.tag_known_automatically
        )
        self.ui.tagKnownManuallyLineEdit.setText(self._config.tag_known_manually)
        self.ui.tagLearnCardNowLineEdit.setText(self._config.tag_learn_card_now)

    def _restore_tags_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default tags settings?"
            confirmed = self._warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.tagReadyLineEdit.setText(self._default_config.tag_ready)
        self.ui.tagNotReadyLineEdit.setText(self._default_config.tag_not_ready)
        self.ui.tagKnownAutomaticallyLineEdit.setText(
            self._default_config.tag_known_automatically
        )
        self.ui.tagKnownManuallyLineEdit.setText(
            self._default_config.tag_known_manually
        )
        self.ui.tagLearnCardNowLineEdit.setText(self._default_config.tag_learn_card_now)

    def _populate_parse_tab(self) -> None:
        self.ui.parseIgnoreSquareCheckBox.setChecked(
            self._config.parse_ignore_bracket_contents
        )
        self.ui.parseIgnoreRoundCheckBox.setChecked(
            self._config.parse_ignore_round_bracket_contents
        )
        self.ui.parseIgnoreSlimCheckBox.setChecked(
            self._config.parse_ignore_slim_round_bracket_contents
        )
        self.ui.parseIgnoreNamesMizerCheckBox.setChecked(
            self._config.parse_ignore_names_morphemizer
        )
        self.ui.parseIgnoreNamesFileCheckBox.setChecked(
            self._config.parse_ignore_names_textfile
        )
        self.ui.parseIgnoreSuspendedCheckBox.setChecked(
            self._config.parse_ignore_suspended_cards_content
        )

    def _populate_shortcuts_tab(self) -> None:
        self.ui.shortcutRecalcKeySequenceEdit.setKeySequence(
            self._config.shortcut_recalc
        )
        self.ui.shortcutSettingsKeySequenceEdit.setKeySequence(
            self._config.shortcut_settings
        )
        self.ui.shortcutBrowseReadyKeySequenceEdit.setKeySequence(
            self._config.shortcut_browse_ready_same_unknown.toString()
        )
        self.ui.shortcutBrowseAllKeySequenceEdit.setKeySequence(
            self._config.shortcut_browse_all_same_unknown.toString()
        )
        self.ui.shortcutKnownAndSkipKeySequenceEdit.setKeySequence(
            self._config.shortcut_set_known_and_skip.toString()
        )
        self.ui.shortcutLearnNowKeySequenceEdit.setKeySequence(
            self._config.shortcut_learn_now.toString()
        )
        self.ui.shortcutViewMorphsKeySequenceEdit.setKeySequence(
            self._config.shortcut_view_morphemes.toString()
        )

    def _restore_parse_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default parse settings?"
            confirmed = self._warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.parseIgnoreSquareCheckBox.setChecked(
            self._default_config.parse_ignore_bracket_contents
        )
        self.ui.parseIgnoreRoundCheckBox.setChecked(
            self._default_config.parse_ignore_round_bracket_contents
        )
        self.ui.parseIgnoreSlimCheckBox.setChecked(
            self._default_config.parse_ignore_slim_round_bracket_contents
        )
        self.ui.parseIgnoreNamesMizerCheckBox.setChecked(
            self._default_config.parse_ignore_names_morphemizer
        )
        self.ui.parseIgnoreNamesFileCheckBox.setChecked(
            self._default_config.parse_ignore_names_textfile
        )
        self.ui.parseIgnoreSuspendedCheckBox.setChecked(
            self._default_config.parse_ignore_suspended_cards_content
        )

    def _restore_shortcuts_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default shortcuts settings?"
            confirmed = self._warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.shortcutRecalcKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_recalc
        )
        self.ui.shortcutSettingsKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_settings
        )
        self.ui.shortcutBrowseReadyKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_browse_ready_same_unknown
        )
        self.ui.shortcutBrowseAllKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_browse_all_same_unknown
        )
        self.ui.shortcutKnownAndSkipKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_set_known_and_skip
        )
        self.ui.shortcutLearnNowKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_learn_now
        )
        self.ui.shortcutViewMorphsKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_view_morphemes
        )

    def _populate_recalc_tab(self) -> None:
        self.ui.recalcIntervalSpinBox.setValue(self._config.recalc_interval_for_known)
        self.ui.recalcBeforeSyncCheckBox.setChecked(self._config.recalc_on_sync)
        self.ui.recalcSuspendKnownCheckBox.setChecked(
            self._config.recalc_suspend_known_new_cards
        )

    def _restore_recalc_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default recalc settings?"
            confirmed = self._warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.recalcIntervalSpinBox.setValue(
            self._default_config.recalc_interval_for_known
        )
        self.ui.recalcBeforeSyncCheckBox.setChecked(self._default_config.recalc_on_sync)
        self.ui.recalcSuspendKnownCheckBox.setChecked(
            self._default_config.recalc_suspend_known_new_cards
        )

    def _populate_skip_tab(self) -> None:
        self.ui.skipKnownCheckBox.setChecked(self._config.skip_only_known_morphs_cards)
        self.ui.skipAlreadySeenCheckBox.setChecked(
            self._config.skip_unknown_morph_seen_today_cards
        )
        self.ui.skipNotificationsCheckBox.setChecked(
            self._config.skip_show_num_of_skipped_cards
        )

    def _restore_skip_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default skip settings?"
            confirmed = self._warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.skipKnownCheckBox.setChecked(
            self._default_config.skip_only_known_morphs_cards
        )
        self.ui.skipAlreadySeenCheckBox.setChecked(
            self._default_config.skip_unknown_morph_seen_today_cards
        )
        self.ui.skipNotificationsCheckBox.setChecked(
            self._default_config.skip_show_num_of_skipped_cards
        )

    def _restore_all_defaults(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to restore <b>all</b> default settings?"
        confirmed = self._warning_dialog(title, text)

        if confirmed:
            default_filters = self._default_config.filters
            self._setup_note_filters_table(default_filters)
            self._restore_extra_fields_defaults(skip_confirmation=True)
            self._restore_tags_defaults(skip_confirmation=True)
            self._restore_parse_defaults(skip_confirmation=True)
            self._restore_skip_defaults(skip_confirmation=True)
            self._restore_recalc_defaults(skip_confirmation=True)
            self._restore_shortcuts_defaults(skip_confirmation=True)

    def _setup_buttons(self) -> None:
        style: Optional[QStyle] = self.style()
        assert style is not None

        save_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        self.ui.savePushButton.setIcon(save_icon)

        cancel_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        self.ui.cancelPushButton.setIcon(cancel_icon)

        self.ui.savePushButton.setAutoDefault(False)
        self.ui.cancelPushButton.setAutoDefault(False)
        self.ui.addNewRowPushButton.setAutoDefault(False)
        self.ui.deleteRowPushButton.setAutoDefault(False)
        self.ui.restoreExtraFieldsPushButton.setAutoDefault(False)
        self.ui.restoreTagsPushButton.setAutoDefault(False)
        self.ui.restoreRecalcPushButton.setAutoDefault(False)
        self.ui.restoreShortcutsPushButton.setAutoDefault(False)
        self.ui.restoreParsePushButton.setAutoDefault(False)
        self.ui.restoreSkipPushButton.setAutoDefault(False)
        self.ui.restoreAllDefaultsPushButton.setAutoDefault(False)

        self.ui.savePushButton.clicked.connect(self._save_to_config)
        self.ui.cancelPushButton.clicked.connect(self.close)
        self.ui.addNewRowPushButton.clicked.connect(self._add_new_row)
        self.ui.deleteRowPushButton.clicked.connect(self._delete_row)
        self.ui.restoreExtraFieldsPushButton.clicked.connect(
            self._restore_extra_fields_defaults
        )
        self.ui.restoreTagsPushButton.clicked.connect(self._restore_tags_defaults)
        self.ui.restoreRecalcPushButton.clicked.connect(self._restore_recalc_defaults)
        self.ui.restoreShortcutsPushButton.clicked.connect(
            self._restore_shortcuts_defaults
        )
        self.ui.restoreParsePushButton.clicked.connect(self._restore_parse_defaults)
        self.ui.restoreSkipPushButton.clicked.connect(self._restore_skip_defaults)
        self.ui.restoreAllDefaultsPushButton.clicked.connect(self._restore_all_defaults)

    def _delete_row(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to delete the selected row?"
        confirmed = self._warning_dialog(title, text)
        if confirmed:
            selected_row = self.ui.note_filters_table.currentRow()
            self.ui.note_filters_table.removeRow(selected_row)

    def _add_new_row(self) -> None:
        self.ui.note_filters_table.setRowCount(
            self.ui.note_filters_table.rowCount() + 1
        )
        config_filter = self._default_config.filters[0]
        row = self.ui.note_filters_table.rowCount() - 1
        self._set_note_filters_table_row(row, config_filter)

    def _save_to_config(self) -> None:  # pylint:disable=too-many-locals
        new_config = {
            "extra_difficulty": self.ui.extraDifficultyCheckBox.isChecked(),
            "extra_highlighted": self.ui.extraHighlightedCheckBox.isChecked(),
            "extra_unknowns": self.ui.extraUnknownsCheckBox.isChecked(),
            "extra_unknowns_count": self.ui.extraUnknownsCountCheckBox.isChecked(),
            "tag_ready": self.ui.tagReadyLineEdit.text(),
            "tag_not_ready": self.ui.tagNotReadyLineEdit.text(),
            "tag_known_automatically": self.ui.tagKnownAutomaticallyLineEdit.text(),
            "tag_known_manually": self.ui.tagKnownManuallyLineEdit.text(),
            "tag_learn_card_now": self.ui.tagLearnCardNowLineEdit.text(),
            "shortcut_recalc": self.ui.shortcutRecalcKeySequenceEdit.keySequence().toString(),
            "shortcut_settings": self.ui.shortcutSettingsKeySequenceEdit.keySequence().toString(),
            "shortcut_browse_ready_same_unknown": self.ui.shortcutBrowseReadyKeySequenceEdit.keySequence().toString(),
            "shortcut_browse_all_same_unknown": self.ui.shortcutBrowseAllKeySequenceEdit.keySequence().toString(),
            "shortcut_set_known_and_skip": self.ui.shortcutKnownAndSkipKeySequenceEdit.keySequence().toString(),
            "shortcut_learn_now": self.ui.shortcutLearnNowKeySequenceEdit.keySequence().toString(),
            "shortcut_view_morphemes": self.ui.shortcutViewMorphsKeySequenceEdit.keySequence().toString(),
            "recalc_interval_for_known": self.ui.recalcIntervalSpinBox.value(),
            "recalc_on_sync": self.ui.recalcBeforeSyncCheckBox.isChecked(),
            "recalc_suspend_known_new_cards": self.ui.recalcSuspendKnownCheckBox.isChecked(),
            "parse_ignore_bracket_contents": self.ui.parseIgnoreSquareCheckBox.isChecked(),
            "parse_ignore_round_bracket_contents": self.ui.parseIgnoreRoundCheckBox.isChecked(),
            "parse_ignore_slim_round_bracket_contents": self.ui.parseIgnoreSlimCheckBox.isChecked(),
            "parse_ignore_names_morphemizer": self.ui.parseIgnoreNamesMizerCheckBox.isChecked(),
            "parse_ignore_names_textfile": self.ui.parseIgnoreNamesFileCheckBox.isChecked(),
            "parse_ignore_suspended_cards_content": self.ui.parseIgnoreSuspendedCheckBox.isChecked(),
            "skip_only_known_morphs_cards": self.ui.skipKnownCheckBox.isChecked(),
            "skip_unknown_morph_seen_today_cards": self.ui.skipAlreadySeenCheckBox.isChecked(),
            "skip_show_num_of_skipped_cards": self.ui.skipNotificationsCheckBox.isChecked(),
        }

        filters: list[FilterTypeAlias] = []
        for row in range(self.ui.note_filters_table.rowCount()):
            note_type_cbox: QComboBox = get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_note_type_column
                )
            )
            tags_widget: QTableWidgetItem = get_table_item(
                self.ui.note_filters_table.item(row, self._note_filter_tags_column)
            )
            field_cbox: QComboBox = get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_field_column
                )
            )
            morphemizer_widget: QComboBox = get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_morphemizer_column
                )
            )
            morph_priority_widget: QComboBox = get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_morph_priority_column
                )
            )
            read_widget: QCheckBox = get_checkbox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_read_column
                )
            )
            modify_widget: QCheckBox = get_checkbox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_modify_column
                )
            )

            _filter: FilterTypeAlias = {
                "note_type": note_type_cbox.itemText(note_type_cbox.currentIndex()),
                "note_type_id": self.models[note_type_cbox.currentIndex()].id,
                "tags": json.loads(tags_widget.text()),
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
            }
            filters.append(_filter)
        new_config["filters"] = filters

        update_configs(new_config)
        self._config = AnkiMorphsConfig()
        tooltip("Please recalc to avoid unexpected behaviour", parent=self)

    def _update_fields_cbox(
        self, field_cbox: QComboBox, note_type_cbox: QComboBox
    ) -> None:
        assert mw
        current_model_id = self.models[note_type_cbox.currentIndex()].id
        note_type = mw.col.models.get(NotetypeId(int(current_model_id)))
        assert note_type
        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)
        field_cbox.clear()
        field_cbox.addItems(fields)

    def _tags_cell_clicked(self, row: int, column: int) -> None:
        if column != 1:
            # tags cells are in column 1
            return

        tags_widget: QTableWidgetItem = get_table_item(
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
        tooltip("Remember to save!", parent=self)

    @staticmethod
    def _get_frequency_files() -> list[str]:
        assert mw is not None
        path_generator = Path(mw.pm.profileFolder(), "frequency-files").glob("*.csv")
        frequency_files = [file.name for file in path_generator if file.is_file()]
        return frequency_files

    @staticmethod
    def _get_model_combobox_index(
        items: Iterable[NotetypeNameId], filter_field: str
    ) -> Optional[int]:
        for index, model in enumerate(items):
            if model.name == filter_field:
                return index
        return None

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

    def _warning_dialog(
        self, title: str, text: str, display_tooltip: bool = True
    ) -> bool:
        answer = show_warning_box(title, text, parent=self)
        if answer == QMessageBox.StandardButton.Yes:
            if display_tooltip:
                tooltip("Remember to save!", parent=self)
            return True
        return False
