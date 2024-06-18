from __future__ import annotations

import functools

from aqt.qt import (  # pylint:disable=no-name-in-module
    QDialog,
    QRadioButton,
    Qt,
    QTreeWidgetItem,
)

from .. import ankimorphs_globals, message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig, RawConfigFilterKeys, RawConfigKeys
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .settings_abstract_tab import AbstractSettingsTab


class ExtraFieldsTab(AbstractSettingsTab):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        super().__init__(parent, ui, config, default_config)

        self._raw_config_key_to_radio_button: dict[str, QRadioButton] = {
            RawConfigKeys.RECALC_UNKNOWNS_FIELD_SHOWS_INFLECTIONS: self.ui.unknownsFieldShowsInflectionsRadioButton,
            RawConfigKeys.RECALC_UNKNOWNS_FIELD_SHOWS_LEMMAS: self.ui.unknownsFieldShowsLemmasRadioButton,
        }

        self._extra_fields_names = [
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS,
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT,
            ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED,
            ankimorphs_globals.EXTRA_FIELD_SCORE,
            ankimorphs_globals.EXTRA_FIELD_SCORE_TERMS,
        ]

        # hides the '1' number in the top left corner
        self.ui.extraFieldsTreeWidget.setHeaderHidden(True)

        self.ui.extraFieldsTreeWidget.itemChanged.connect(self._tree_item_changed)

        self._selected_note_types: list[str] = [
            _filter.note_type for _filter in self._config.filters
        ]

        self.populate()
        self.setup_buttons()
        self.update_previous_state()

    def update(self, selected_note_types: list[str]) -> None:
        self._selected_note_types = selected_note_types
        self._populate_tree()

    def populate(self) -> None:
        super().populate()
        self._populate_tree()

    def _populate_tree(self, restore_defaults: bool = False) -> None:
        self.ui.extraFieldsTreeWidget.clear()  # content might be outdated so we clear it
        self.ui.extraFieldsTreeWidget.blockSignals(True)

        for note_type in self._selected_note_types:
            if note_type == ankimorphs_globals.NONE_OPTION:
                continue

            top_node = self._create_top_node(note_type, restore_defaults)
            self.ui.extraFieldsTreeWidget.addTopLevelItem(top_node)

        self.ui.extraFieldsTreeWidget.blockSignals(False)

    def _create_top_node(
        self, note_type: str, restore_defaults: bool = False
    ) -> QTreeWidgetItem:
        selected_extra_fields_in_config: dict[str, bool] = (
            self.get_selected_extra_fields_from_config(note_type, restore_defaults)
        )

        top_node = QTreeWidgetItem()
        top_node.setText(0, note_type)
        top_node.setCheckState(0, Qt.CheckState.Unchecked)
        has_children_checked: bool = False

        for extra_field in self._extra_fields_names:
            child_item = QTreeWidgetItem(top_node)
            child_item.setText(0, extra_field)
            check_state = Qt.CheckState.Unchecked

            if selected_extra_fields_in_config[extra_field] is True:
                check_state = Qt.CheckState.Checked
                has_children_checked = True

            child_item.setCheckState(0, check_state)

        if has_children_checked:
            top_node.setCheckState(0, Qt.CheckState.Checked)
        else:
            self._uncheck_and_disable_all_children(top_node)

        return top_node

    # the cache needs to have a max size to maintain garbage collection
    @functools.lru_cache(maxsize=131072)
    def get_selected_extra_fields_from_config(
        self, note_type: str, restore_defaults: bool = False
    ) -> dict[str, bool]:
        """
        Sets all extra fields to 'false' is `restore_defaults` == True
        """

        extra_score: bool = False
        extra_score_terms: bool = False
        extra_highlighted: bool = False
        extra_unknowns: bool = False
        extra_unknowns_count: bool = False

        if restore_defaults is False:
            for _filter in self._config.filters:
                if note_type == _filter.note_type:
                    extra_score = _filter.extra_score
                    extra_score_terms = _filter.extra_score_terms
                    extra_highlighted = _filter.extra_highlighted
                    extra_unknowns = _filter.extra_unknowns
                    extra_unknowns_count = _filter.extra_unknowns_count
                    break

        selected_extra_fields: dict[str, bool] = {
            ankimorphs_globals.EXTRA_FIELD_SCORE: extra_score,
            ankimorphs_globals.EXTRA_FIELD_SCORE_TERMS: extra_score_terms,
            ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED: extra_highlighted,
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS: extra_unknowns,
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT: extra_unknowns_count,
        }
        return selected_extra_fields

    def _tree_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        self.ui.extraFieldsTreeWidget.blockSignals(True)

        item_parent = item.parent()
        if item_parent is None:
            top_node = item
            # if parent is checked, enable all children
            if top_node.checkState(column) == Qt.CheckState.Checked:
                for child_index in range(top_node.childCount()):
                    child = top_node.child(child_index)
                    assert child is not None
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    child.setDisabled(False)
            else:
                self._uncheck_and_disable_all_children(top_node)

        self.ui.extraFieldsTreeWidget.blockSignals(False)

    @staticmethod
    def _uncheck_and_disable_all_children(top_node: QTreeWidgetItem) -> None:
        for child_index in range(top_node.childCount()):
            child = top_node.child(child_index)
            assert child is not None
            child.setCheckState(0, Qt.CheckState.Unchecked)
            child.setDisabled(True)

    def setup_buttons(self) -> None:
        self.ui.restoreExtraFieldsPushButton.setAutoDefault(False)
        self.ui.restoreExtraFieldsPushButton.clicked.connect(self.restore_defaults)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = self.get_confirmation_text()
            confirmed = message_box_utils.warning_dialog(
                title, text, parent=self._parent
            )

            if not confirmed:
                return

        self.ui.unknownsFieldShowsInflectionsRadioButton.setChecked(
            self._default_config.recalc_unknowns_field_shows_inflections
        )
        self.ui.unknownsFieldShowsLemmasRadioButton.setChecked(
            self._default_config.recalc_unknowns_field_shows_lemmas
        )

        self._populate_tree(restore_defaults=True)

    def restore_to_config_state(self) -> None:
        # todo...
        pass

    def get_selected_extra_fields(self, note_type_name: str) -> dict[str, bool]:
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

        extra_score = ankimorphs_globals.EXTRA_FIELD_SCORE in selected_fields
        extra_score_terms = (
            ankimorphs_globals.EXTRA_FIELD_SCORE_TERMS in selected_fields
        )
        extra_highlighted = (
            ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED in selected_fields
        )
        extra_unknowns = ankimorphs_globals.EXTRA_FIELD_UNKNOWNS in selected_fields
        extra_unknowns_count = (
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT in selected_fields
        )

        return {
            RawConfigFilterKeys.EXTRA_SCORE: extra_score,
            RawConfigFilterKeys.EXTRA_SCORE_TERMS: extra_score_terms,
            RawConfigFilterKeys.EXTRA_HIGHLIGHTED: extra_highlighted,
            RawConfigFilterKeys.EXTRA_UNKNOWNS: extra_unknowns,
            RawConfigFilterKeys.EXTRA_UNKNOWNS_COUNT: extra_unknowns_count,
        }

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default extra fields settings?"
