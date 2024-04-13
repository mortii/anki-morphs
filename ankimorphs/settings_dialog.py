from __future__ import annotations

import functools
import json
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import Callable

import aqt
from anki.models import NotetypeDict, NotetypeNameId
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QStyle,
    Qt,
    QTableWidgetItem,
    QTreeWidgetItem,
)
from aqt.utils import tooltip

from . import ankimorphs_config, ankimorphs_globals, table_utils
from .ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter, FilterTypeAlias
from .message_box_utils import show_warning_box
from .morphemizer import get_all_morphemizers
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
        self._note_type_models: Sequence[NotetypeNameId] = (
            mw.col.models.all_names_and_ids()
        )
        self.ui = Ui_SettingsDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.ui.note_filters_table.cellClicked.connect(self._tags_cell_clicked)
        self.ui.treeWidget.setHeaderHidden(  # hides the '1' number in the top left corner
            True
        )

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
        self._extra_fields_names = [
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS,
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT,
            ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED,
            ankimorphs_globals.EXTRA_FIELD_SCORE,
        ]
        self._config = AnkiMorphsConfig()
        self._default_config = AnkiMorphsConfig(is_default=True)
        self._setup_note_filters_table(self._config.filters)
        self._setup_extra_fields_tree_widget(self._config.filters)
        self._populate_tags_tab()
        self._populate_preprocess_tab()
        self._populate_skip_tab()
        self._populate_shortcuts_tab()
        self._populate_recalc_tab()
        self._setup_buttons()
        self.ui.treeWidget.itemChanged.connect(self._tree_item_changed)
        self.ui.tabWidget.currentChanged.connect(self._on_tab_changed)
        self._set_tree_item_state_programmatically = False

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
        self.ui.ankimorphs_version_label.setText(
            f"AnkiMorphs version: {ankimorphs_globals.__version__}"
        )

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
        note_types_string: list[str] = [ankimorphs_globals.NONE_OPTION] + [
            model.name for model in self._note_type_models
        ]
        note_type_cbox.addItems(note_types_string)
        note_type_name_index = table_utils.get_combobox_index(
            note_types_string, config_filter.note_type
        )
        note_type_cbox.setCurrentIndex(note_type_name_index)
        selected_note_type: str = note_type_cbox.itemText(note_type_cbox.currentIndex())

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

        # Fields are dependent on note-type
        note_type_cbox.currentIndexChanged.connect(
            partial(self._update_fields_cbox, field_cbox, note_type_cbox)
        )

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

        morph_priority_cbox = QComboBox(self.ui.note_filters_table)
        frequency_files: list[str] = [
            ankimorphs_globals.NONE_OPTION,
            ankimorphs_globals.COLLECTION_FREQUENCY_OPTION,
        ]
        frequency_files += self._get_frequency_files()
        morph_priority_cbox.addItems(frequency_files)
        morph_priority_cbox_index = table_utils.get_combobox_index(
            frequency_files, config_filter.morph_priority
        )
        if morph_priority_cbox_index is not None:
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

    def _setup_extra_fields_tree_widget(  # pylint:disable=too-many-locals, too-many-branches
        self, config_filters: list[AnkiMorphsConfigFilter]
    ) -> None:
        self.ui.treeWidget.clear()  # content might be outdated so we clear it
        active_note_types: set[str] = set()

        for row in range(self.ui.note_filters_table.rowCount()):
            note_filter_note_type_widget: QComboBox = table_utils.get_combobox_widget(
                self.ui.note_filters_table.cellWidget(
                    row, self._note_filter_note_type_column
                )
            )
            note_type = note_filter_note_type_widget.itemText(
                note_filter_note_type_widget.currentIndex()
            )
            if (
                note_type in active_note_types
                or note_type == ankimorphs_globals.NONE_OPTION
            ):
                continue

            active_note_types.add(note_type)

            extra_score: bool = False
            extra_highlighted: bool = False
            extra_unknowns: bool = False
            extra_unknowns_count: bool = False

            for _filter in config_filters:
                if note_type == _filter.note_type:
                    extra_score = _filter.extra_score
                    extra_highlighted = _filter.extra_highlighted
                    extra_unknowns = _filter.extra_unknowns
                    extra_unknowns_count = _filter.extra_unknowns_count
                    break

            top_node = QTreeWidgetItem()
            top_node.setText(0, note_type)
            top_node.setCheckState(0, Qt.CheckState.Unchecked)
            children_checked: int = 0

            for extra_field in self._extra_fields_names:
                child_item = QTreeWidgetItem(top_node)
                child_item.setText(0, extra_field)
                check_state: Qt.CheckState = Qt.CheckState.Unchecked

                if extra_field == ankimorphs_globals.EXTRA_FIELD_SCORE:
                    if extra_score is True:
                        check_state = Qt.CheckState.Checked
                        children_checked += 1
                elif extra_field == ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED:
                    if extra_highlighted is True:
                        check_state = Qt.CheckState.Checked
                        children_checked += 1
                elif extra_field == ankimorphs_globals.EXTRA_FIELD_UNKNOWNS:
                    if extra_unknowns is True:
                        check_state = Qt.CheckState.Checked
                        children_checked += 1
                elif extra_field == ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT:
                    if extra_unknowns_count is True:
                        check_state = Qt.CheckState.Checked
                        children_checked += 1

                child_item.setCheckState(0, check_state)

            if children_checked == len(self._extra_fields_names):
                top_node.setCheckState(0, Qt.CheckState.Checked)

            self.ui.treeWidget.addTopLevelItem(top_node)

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

    def _populate_preprocess_tab(self) -> None:
        self.ui.preprocessIgnoreSquareCheckBox.setChecked(
            self._config.preprocess_ignore_bracket_contents
        )
        self.ui.preprocessIgnoreRoundCheckBox.setChecked(
            self._config.preprocess_ignore_round_bracket_contents
        )
        self.ui.preprocessIgnoreSlimCheckBox.setChecked(
            self._config.preprocess_ignore_slim_round_bracket_contents
        )
        self.ui.preprocessIgnoreNamesMizerCheckBox.setChecked(
            self._config.preprocess_ignore_names_morphemizer
        )
        self.ui.preprocessIgnoreNamesFileCheckBox.setChecked(
            self._config.preprocess_ignore_names_textfile
        )
        self.ui.preprocessIgnoreSuspendedCheckBox.setChecked(
            self._config.preprocess_ignore_suspended_cards_content
        )

    def _restore_preprocess_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default preprocess settings?"
            confirmed = self._warning_dialog(title, text)

            if not confirmed:
                return

        self.ui.preprocessIgnoreSquareCheckBox.setChecked(
            self._default_config.preprocess_ignore_bracket_contents
        )
        self.ui.preprocessIgnoreRoundCheckBox.setChecked(
            self._default_config.preprocess_ignore_round_bracket_contents
        )
        self.ui.preprocessIgnoreSlimCheckBox.setChecked(
            self._default_config.preprocess_ignore_slim_round_bracket_contents
        )
        self.ui.preprocessIgnoreNamesMizerCheckBox.setChecked(
            self._default_config.preprocess_ignore_names_morphemizer
        )
        self.ui.preprocessIgnoreNamesFileCheckBox.setChecked(
            self._default_config.preprocess_ignore_names_textfile
        )
        self.ui.preprocessIgnoreSuspendedCheckBox.setChecked(
            self._default_config.preprocess_ignore_suspended_cards_content
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
        self.ui.shortcutBrowseReadyLemmaKeySequenceEdit.setKeySequence(
            self._config.shortcut_browse_ready_same_unknown_lemma.toString()
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
        self.ui.shortcutGeneratorsKeySequenceEdit.setKeySequence(
            self._config.shortcut_generators.toString()
        )
        self.ui.shortcutKnownMorphsExporterKeySequenceEdit.setKeySequence(
            self._config.shortcut_known_morphs_exporter.toString()
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
        self.ui.shortcutBrowseReadyLemmaKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_browse_ready_same_unknown_lemma.toString()
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
        self.ui.shortcutViewMorphsKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_view_morphemes.toString()
        )
        self.ui.shortcutKnownMorphsExporterKeySequenceEdit.setKeySequence(
            self._default_config.shortcut_known_morphs_exporter.toString()
        )

    def _populate_recalc_tab(self) -> None:
        self.ui.recalcIntervalSpinBox.setValue(self._config.recalc_interval_for_known)
        self.ui.dueOffsetSpinBox.setValue(self._config.recalc_due_offset)
        self.ui.offsetFirstMorphsSpinBox.setValue(
            self._config.recalc_number_of_morphs_to_offset
        )

        self.ui.recalcBeforeSyncCheckBox.setChecked(self._config.recalc_on_sync)
        self.ui.recalcSuspendKnownCheckBox.setChecked(
            self._config.recalc_suspend_known_new_cards
        )
        self.ui.recalcMoveKnownNewCardsToTheEndCheckBox.setChecked(
            self._config.recalc_move_known_new_cards_to_the_end
        )
        self.ui.recalcReadKnownMorphsFolderCheckBox.setChecked(
            self._config.recalc_read_known_morphs_folder
        )
        self.ui.toolbarStatsUseSeenRadioButton.setChecked(
            self._config.recalc_toolbar_stats_use_seen
        )
        self.ui.toolbarStatsUseKnownRadioButton.setChecked(
            self._config.recalc_toolbar_stats_use_known
        )
        self.ui.unknownsFieldShowsInflectionsRadioButton.setChecked(
            self._config.recalc_unknowns_field_shows_inflections
        )
        self.ui.unknownsFieldShowsLemmasRadioButton.setChecked(
            self._config.recalc_unknowns_field_shows_lemmas
        )
        self.ui.shiftNewCardsCheckBox.setChecked(self._config.recalc_offset_new_cards)

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
        self.ui.dueOffsetSpinBox.setValue(self._default_config.recalc_due_offset)
        self.ui.offsetFirstMorphsSpinBox.setValue(
            self._default_config.recalc_number_of_morphs_to_offset
        )

        self.ui.recalcBeforeSyncCheckBox.setChecked(self._default_config.recalc_on_sync)
        self.ui.recalcSuspendKnownCheckBox.setChecked(
            self._default_config.recalc_suspend_known_new_cards
        )
        self.ui.recalcMoveKnownNewCardsToTheEndCheckBox.setChecked(
            self._default_config.recalc_move_known_new_cards_to_the_end
        )
        self.ui.recalcReadKnownMorphsFolderCheckBox.setChecked(
            self._default_config.recalc_read_known_morphs_folder
        )
        self.ui.toolbarStatsUseSeenRadioButton.setChecked(
            self._default_config.recalc_toolbar_stats_use_seen
        )
        self.ui.toolbarStatsUseKnownRadioButton.setChecked(
            self._default_config.recalc_toolbar_stats_use_known
        )
        self.ui.unknownsFieldShowsInflectionsRadioButton.setChecked(
            self._default_config.recalc_unknowns_field_shows_inflections
        )
        self.ui.unknownsFieldShowsLemmasRadioButton.setChecked(
            self._default_config.recalc_unknowns_field_shows_lemmas
        )
        self.ui.shiftNewCardsCheckBox.setChecked(
            self._default_config.recalc_offset_new_cards
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
            self._setup_extra_fields_tree_widget(default_filters)
            self._restore_tags_defaults(skip_confirmation=True)
            self._restore_preprocess_defaults(skip_confirmation=True)
            self._restore_skip_defaults(skip_confirmation=True)
            self._restore_recalc_defaults(skip_confirmation=True)
            self._restore_shortcuts_defaults(skip_confirmation=True)

    def _setup_buttons(self) -> None:
        style: QStyle | None = self.style()
        assert style is not None

        save_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        self.ui.savePushButton.setIcon(save_icon)

        cancel_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        self.ui.cancelPushButton.setIcon(cancel_icon)

        self.ui.savePushButton.setAutoDefault(False)
        self.ui.cancelPushButton.setAutoDefault(False)
        self.ui.addNewRowPushButton.setAutoDefault(False)
        self.ui.deleteRowPushButton.setAutoDefault(False)
        self.ui.restoreTagsPushButton.setAutoDefault(False)
        self.ui.restoreRecalcPushButton.setAutoDefault(False)
        self.ui.restoreShortcutsPushButton.setAutoDefault(False)
        self.ui.restorePreprocessPushButton.setAutoDefault(False)
        self.ui.restoreSkipPushButton.setAutoDefault(False)
        self.ui.restoreAllDefaultsPushButton.setAutoDefault(False)

        self.ui.savePushButton.clicked.connect(self._save_to_config)
        self.ui.cancelPushButton.clicked.connect(self.close)

        self.ui.addNewRowPushButton.clicked.connect(self._add_new_row)
        self.ui.deleteRowPushButton.clicked.connect(self._delete_row)

        self.ui.restoreTagsPushButton.clicked.connect(self._restore_tags_defaults)
        self.ui.restoreRecalcPushButton.clicked.connect(self._restore_recalc_defaults)
        self.ui.restoreShortcutsPushButton.clicked.connect(
            self._restore_shortcuts_defaults
        )
        self.ui.restorePreprocessPushButton.clicked.connect(
            self._restore_preprocess_defaults
        )
        self.ui.restoreSkipPushButton.clicked.connect(self._restore_skip_defaults)
        self.ui.restoreAllDefaultsPushButton.clicked.connect(self._restore_all_defaults)

    def _delete_row(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to delete the selected row?"
        confirmed = self._warning_dialog(title, text)
        if confirmed:
            selected_row = self.ui.note_filters_table.currentRow()
            self.ui.note_filters_table.removeRow(selected_row)
            # we don't have to update the extra fields tree here
            # since filters are created based on note filter table,
            # so any obsolete extra fields configs are not used anyway

    def _add_new_row(self) -> None:
        self.ui.note_filters_table.setRowCount(
            self.ui.note_filters_table.rowCount() + 1
        )
        config_filter = self._default_config.filters[0]
        row = self.ui.note_filters_table.rowCount() - 1
        self._set_note_filters_table_row(row, config_filter)
        total_filters = self._config.filters + [config_filter]
        self._setup_extra_fields_tree_widget(total_filters)

    def _save_to_config(self) -> None:  # pylint:disable=too-many-locals
        new_config = {
            "tag_ready": self.ui.tagReadyLineEdit.text(),
            "tag_not_ready": self.ui.tagNotReadyLineEdit.text(),
            "tag_known_automatically": self.ui.tagKnownAutomaticallyLineEdit.text(),
            "tag_known_manually": self.ui.tagKnownManuallyLineEdit.text(),
            "tag_learn_card_now": self.ui.tagLearnCardNowLineEdit.text(),
            "shortcut_recalc": self.ui.shortcutRecalcKeySequenceEdit.keySequence().toString(),
            "shortcut_settings": self.ui.shortcutSettingsKeySequenceEdit.keySequence().toString(),
            "shortcut_browse_ready_same_unknown": self.ui.shortcutBrowseReadyKeySequenceEdit.keySequence().toString(),
            "shortcut_browse_all_same_unknown": self.ui.shortcutBrowseAllKeySequenceEdit.keySequence().toString(),
            "shortcut_browse_ready_same_unknown_lemma": self.ui.shortcutBrowseReadyLemmaKeySequenceEdit.keySequence().toString(),
            "shortcut_set_known_and_skip": self.ui.shortcutKnownAndSkipKeySequenceEdit.keySequence().toString(),
            "shortcut_learn_now": self.ui.shortcutLearnNowKeySequenceEdit.keySequence().toString(),
            "shortcut_view_morphemes": self.ui.shortcutViewMorphsKeySequenceEdit.keySequence().toString(),
            "shortcut_generators": self.ui.shortcutGeneratorsKeySequenceEdit.keySequence().toString(),
            "shortcut_known_morphs_exporter": self.ui.shortcutKnownMorphsExporterKeySequenceEdit.keySequence().toString(),
            "recalc_interval_for_known": self.ui.recalcIntervalSpinBox.value(),
            "recalc_on_sync": self.ui.recalcBeforeSyncCheckBox.isChecked(),
            "recalc_suspend_known_new_cards": self.ui.recalcSuspendKnownCheckBox.isChecked(),
            "recalc_move_known_new_cards_to_the_end": self.ui.recalcMoveKnownNewCardsToTheEndCheckBox.isChecked(),
            "recalc_read_known_morphs_folder": self.ui.recalcReadKnownMorphsFolderCheckBox.isChecked(),
            "recalc_toolbar_stats_use_seen": self.ui.toolbarStatsUseSeenRadioButton.isChecked(),
            "recalc_toolbar_stats_use_known": self.ui.toolbarStatsUseKnownRadioButton.isChecked(),
            "recalc_unknowns_field_shows_inflections": self.ui.unknownsFieldShowsInflectionsRadioButton.isChecked(),
            "recalc_unknowns_field_shows_lemmas": self.ui.unknownsFieldShowsLemmasRadioButton.isChecked(),
            "recalc_offset_new_cards": self.ui.shiftNewCardsCheckBox.isChecked(),
            "recalc_due_offset": self.ui.dueOffsetSpinBox.value(),
            "recalc_number_of_morphs_to_offset": self.ui.offsetFirstMorphsSpinBox.value(),
            "preprocess_ignore_bracket_contents": self.ui.preprocessIgnoreSquareCheckBox.isChecked(),
            "preprocess_ignore_round_bracket_contents": self.ui.preprocessIgnoreRoundCheckBox.isChecked(),
            "preprocess_ignore_slim_round_bracket_contents": self.ui.preprocessIgnoreSlimCheckBox.isChecked(),
            "preprocess_ignore_names_morphemizer": self.ui.preprocessIgnoreNamesMizerCheckBox.isChecked(),
            "preprocess_ignore_names_textfile": self.ui.preprocessIgnoreNamesFileCheckBox.isChecked(),
            "preprocess_ignore_suspended_cards_content": self.ui.preprocessIgnoreSuspendedCheckBox.isChecked(),
            "skip_only_known_morphs_cards": self.ui.skipKnownCheckBox.isChecked(),
            "skip_unknown_morph_seen_today_cards": self.ui.skipAlreadySeenCheckBox.isChecked(),
            "skip_show_num_of_skipped_cards": self.ui.skipNotificationsCheckBox.isChecked(),
        }

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
        for top_node_index in range(self.ui.treeWidget.topLevelItemCount()):
            top_node: QTreeWidgetItem | None = self.ui.treeWidget.topLevelItem(
                top_node_index
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
            self._setup_extra_fields_tree_widget(self._config.filters)

    def _tree_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._set_tree_item_state_programmatically is True:
            return

        self._set_tree_item_state_programmatically = True

        item_parent = item.parent()
        if item_parent is None:  # top level node
            # set all the children to the same check state as the parent
            if item.checkState(column) == Qt.CheckState.Checked:
                for child_index in range(item.childCount()):
                    child = item.child(child_index)
                    assert child is not None
                    child.setCheckState(0, Qt.CheckState.Checked)
            else:
                for child_index in range(item.childCount()):
                    child = item.child(child_index)
                    assert child is not None
                    child.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            if item.checkState(column) == Qt.CheckState.Unchecked:
                # if a child is unchecked then we want the parent to be unchecked too
                item_parent.setCheckState(column, Qt.CheckState.Unchecked)
            else:
                # if all children are checked, then we want the parent to be checked too
                all_children_checked = True
                for child_index in range(item_parent.childCount()):
                    child = item_parent.child(child_index)
                    assert child is not None
                    if child.checkState(column) == Qt.CheckState.Unchecked:
                        all_children_checked = False
                        break
                if all_children_checked:
                    item_parent.setCheckState(0, Qt.CheckState.Checked)

        self._set_tree_item_state_programmatically = False

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
        tooltip("Remember to save!", parent=self)

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

    @staticmethod
    def _get_frequency_files() -> list[str]:
        assert mw is not None
        path_generator = Path(
            mw.pm.profileFolder(), ankimorphs_globals.FREQUENCY_FILES_DIR_NAME
        ).glob("*.csv")
        frequency_files = [file.name for file in path_generator if file.is_file()]
        return frequency_files

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
        if answer is True:
            if display_tooltip:
                tooltip("Remember to save!", parent=self)
            return True
        return False
