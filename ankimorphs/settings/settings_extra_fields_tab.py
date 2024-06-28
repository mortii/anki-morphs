from __future__ import annotations

from aqt.qt import (  # pylint:disable=no-name-in-module
    QDialog,
    QRadioButton,
    Qt,
    QTreeWidgetItem,
)

from .. import ankimorphs_globals, message_box_utils
from ..ankimorphs_config import (
    AnkiMorphsConfig,
    FilterTypeAlias,
    RawConfigFilterKeys,
    RawConfigKeys,
)
from ..ui.settings_dialog_ui import Ui_SettingsDialog
from .data_extractor import DataExtractor
from .data_provider import DataProvider
from .data_subscriber import DataSubscriber
from .settings_tab import SettingsTab


class ExtraFieldsTab(SettingsTab, DataSubscriber, DataExtractor):

    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ) -> None:
        SettingsTab.__init__(self, parent, ui, config, default_config)
        DataExtractor.__init__(self)

        self._raw_config_key_to_radio_button: dict[str, QRadioButton] = {
            RawConfigKeys.EXTRA_FIELDS_DISPLAY_INFLECTIONS: self.ui.unknownsFieldShowsInflectionsRadioButton,
            RawConfigKeys.EXTRA_FIELDS_DISPLAY_LEMMAS: self.ui.unknownsFieldShowsLemmasRadioButton,
        }

        self._extra_fields_names = [
            ankimorphs_globals.EXTRA_ALL_MORPHS,
            ankimorphs_globals.EXTRA_ALL_MORPHS_COUNT,
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

    def add_data_provider(self, data_provider: DataProvider) -> None:
        self.data_provider = data_provider
        self.update_previous_state()

    def update(self, selected_note_types: list[str]) -> None:
        self._selected_note_types = selected_note_types
        self._populate_tree()

    def populate(self, use_default_config: bool = False) -> None:
        super().populate(use_default_config)
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

    def get_selected_extra_fields_from_config(
        self, note_type: str, restore_defaults: bool = False
    ) -> dict[str, bool]:
        """
        Sets all extra fields to 'false' is `restore_defaults` == True
        """

        extra_all_morphs: bool = False
        extra_all_morphs_count: bool = False
        extra_score: bool = False
        extra_score_terms: bool = False
        extra_highlighted: bool = False
        extra_unknowns: bool = False
        extra_unknowns_count: bool = False

        if restore_defaults is False:
            for _filter in self._config.filters:
                if note_type == _filter.note_type:
                    extra_all_morphs = _filter.extra_all_morphs
                    extra_all_morphs_count = _filter.extra_all_morphs_count
                    extra_score = _filter.extra_score
                    extra_score_terms = _filter.extra_score_terms
                    extra_highlighted = _filter.extra_highlighted
                    extra_unknowns = _filter.extra_unknowns
                    extra_unknowns_count = _filter.extra_unknowns_count
                    break

        selected_extra_fields: dict[str, bool] = {
            ankimorphs_globals.EXTRA_ALL_MORPHS: extra_all_morphs,
            ankimorphs_globals.EXTRA_ALL_MORPHS_COUNT: extra_all_morphs_count,
            ankimorphs_globals.EXTRA_FIELD_SCORE: extra_score,
            ankimorphs_globals.EXTRA_FIELD_SCORE_TERMS: extra_score_terms,
            ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED: extra_highlighted,
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS: extra_unknowns,
            ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT: extra_unknowns_count,
        }
        print(f"selected_extra_fields: {selected_extra_fields}")
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

        for (
            config_attribute,
            radio_button,
        ) in self._raw_config_key_to_radio_button.items():
            is_checked = getattr(self._default_config, config_attribute)
            radio_button.setChecked(is_checked)

        self._populate_tree(restore_defaults=True)

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

        # fmt: off
        extra_all_morphs = ankimorphs_globals.EXTRA_ALL_MORPHS in selected_fields
        extra_all_morphs_count = ankimorphs_globals.EXTRA_ALL_MORPHS_COUNT in selected_fields
        extra_score = ankimorphs_globals.EXTRA_FIELD_SCORE in selected_fields
        extra_score_terms = ankimorphs_globals.EXTRA_FIELD_SCORE_TERMS in selected_fields
        extra_highlighted = ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED in selected_fields
        extra_unknowns = ankimorphs_globals.EXTRA_FIELD_UNKNOWNS in selected_fields
        extra_unknowns_count = ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT in selected_fields
        # fmt: on

        return {
            RawConfigFilterKeys.EXTRA_ALL_MORPHS: extra_all_morphs,
            RawConfigFilterKeys.EXTRA_ALL_MORPHS_COUNT: extra_all_morphs_count,
            RawConfigFilterKeys.EXTRA_SCORE: extra_score,
            RawConfigFilterKeys.EXTRA_SCORE_TERMS: extra_score_terms,
            RawConfigFilterKeys.EXTRA_HIGHLIGHTED: extra_highlighted,
            RawConfigFilterKeys.EXTRA_UNKNOWNS: extra_unknowns,
            RawConfigFilterKeys.EXTRA_UNKNOWNS_COUNT: extra_unknowns_count,
        }

    def get_confirmation_text(self) -> str:
        return "Are you sure you want to restore default extra fields settings?"

    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        assert self.data_provider is not None

        filters: list[FilterTypeAlias] = self.data_provider.get_data()

        for _filter in filters:
            note_type_name = _filter[RawConfigFilterKeys.NOTE_TYPE]
            assert isinstance(note_type_name, str)
            extra_fields_dict: dict[str, bool] = self.get_selected_extra_fields(
                note_type_name=note_type_name
            )
            _filter.update(extra_fields_dict)

        settings_dict: dict[str, str | int | bool | object] = {
            RawConfigKeys.FILTERS: filters
        }

        radio_button_settings = {
            config_key: radio_button.isChecked()
            for config_key, radio_button in self._raw_config_key_to_radio_button.items()
        }

        settings_dict.update(radio_button_settings)

        # print("post filters:")
        # pprint.pp(settings_dict)

        return settings_dict
