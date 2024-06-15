from __future__ import annotations

from aqt.qt import QDialog, Qt, QTreeWidgetItem  # pylint:disable=no-name-in-module

from .. import ankimorphs_globals, message_box_utils
from ..ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
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
        self._parent = parent
        self.ui = ui
        self._config = config
        self._default_config = default_config

        # hides the '1' number in the top left corner
        self.ui.extraFieldsTreeWidget.setHeaderHidden(True)

        self._extra_fields_names = [
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS,
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT,
            ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED,
            ankimorphs_globals.EXTRA_FIELD_SCORE,
            ankimorphs_globals.EXTRA_FIELD_SCORE_TERMS,
        ]

        self._note_filter_note_type_column: int = 0
        self._set_tree_item_state_programmatically = False
        self.ui.extraFieldsTreeWidget.itemChanged.connect(self._tree_item_changed)

    def update(self, selected_note_types: list[str]) -> None:
        print(f"update!! Selected: {selected_note_types}")
        self._update_extra_fields_tree_widget(selected_note_types)

    def populate(self) -> None:
        self.ui.unknownsFieldShowsInflectionsRadioButton.setChecked(
            self._config.recalc_unknowns_field_shows_inflections
        )
        self.ui.unknownsFieldShowsLemmasRadioButton.setChecked(
            self._config.recalc_unknowns_field_shows_lemmas
        )
        self._populate_extra_fields_tree_widget(self._config.filters)

    def _update_extra_fields_tree_widget(
        self,
        selected_note_types: list[str],
    ) -> None:
        self.ui.extraFieldsTreeWidget.clear()  # content might be outdated so we clear it

        config_filters = self._config.filters  # todo are these always up tp date?

        for note_type in selected_note_types:
            if note_type == ankimorphs_globals.NONE_OPTION:
                continue

            top_node = self._create_top_node(config_filters, note_type)
            self.ui.extraFieldsTreeWidget.addTopLevelItem(top_node)

    def _populate_extra_fields_tree_widget(
        self, config_filters: list[AnkiMorphsConfigFilter]
    ) -> None:
        for _filter in config_filters:
            # todo, are the stored config filter note types never "(none)"?
            top_node = self._create_top_node(config_filters, _filter.note_type)
            self.ui.extraFieldsTreeWidget.addTopLevelItem(top_node)

    def _create_top_node(  # pylint:disable=too-many-branches
        self, config_filters: list[AnkiMorphsConfigFilter], note_type: str
    ) -> QTreeWidgetItem:

        extra_score: bool = False
        extra_score_terms: bool = False
        extra_highlighted: bool = False
        extra_unknowns: bool = False
        extra_unknowns_count: bool = False

        for _filter in config_filters:
            if note_type == _filter.note_type:
                extra_score = _filter.extra_score
                extra_score_terms = _filter.extra_score_terms
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
            elif extra_field == ankimorphs_globals.EXTRA_FIELD_SCORE_TERMS:
                if extra_score_terms is True:
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

        return top_node

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

    def setup_buttons(self) -> None:
        self.ui.restoreExtraFieldsPushButton.setAutoDefault(False)
        self.ui.restoreExtraFieldsPushButton.clicked.connect(self.restore_defaults)

    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        if not skip_confirmation:
            title = "Confirmation"
            text = "Are you sure you want to restore default extra fields settings?"
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
        # self._setup_extra_fields_tree_widget(self._default_config.filters)
        # todo: enable this again

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        return {
            "recalc_unknowns_field_shows_inflections": self.ui.unknownsFieldShowsInflectionsRadioButton.isChecked(),
            "recalc_unknowns_field_shows_lemmas": self.ui.unknownsFieldShowsLemmasRadioButton.isChecked(),
        }
