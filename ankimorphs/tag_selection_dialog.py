import json
import re
from re import Match
from typing import Callable, Optional

import aqt
from anki.tags import TagManager
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QColor,
    QDialog,
    QHeaderView,
    QMessageBox,
    QStyle,
    Qt,
    QTableWidgetItem,
)

from . import ankimorphs_constants
from .message_box_utils import show_error_box, show_warning_box
from .table_utils import get_checkbox_widget, get_table_item
from .ui.tag_selection_ui import Ui_TagSelectionDialog

user_changed_check_state: bool = True


class TagSelectionDialog(QDialog):  # pylint:disable=too-many-instance-attributes
    # The UI comes from ankimorphs/ui/tag_selection.ui which is used in Qt Designer,
    # which is then converted to ankimorphs/ui/tag_selection_ui.py,
    # which is then imported here.
    #
    # Here we make the final adjustments that can't be made (or are hard to make) in
    # Qt Designer, like setting up tables and widget-connections.

    def __init__(
        self,
    ) -> None:
        super().__init__(parent=None)  # no parent makes the dialog modeless
        self.selected_tags: str = ""

        self.ui = Ui_TagSelectionDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.ui.tableWidget.setAlternatingRowColors(True)

        vertical_header: Optional[QHeaderView] = self.ui.tableWidget.verticalHeader()
        assert vertical_header is not None
        vertical_header.hide()

        self.current_note_filter_row: int = -1
        self._exclude_column: int = 0
        self._include_column: int = 1
        self._tag_column: int = 2

        self.ui.tableWidget.setColumnWidth(self._tag_column, 180)

        self.ui.searchLineEdit.returnPressed.connect(self._on_search)
        self._setup_buttons()

    def set_selected_tags_and_row(self, selected_tags: str, row: int) -> None:
        assert mw is not None
        global user_changed_check_state
        user_changed_check_state = False

        all_tags: list[str] = TagManager(mw.col).all()
        self.ui.tableWidget.setRowCount(len(all_tags))
        self._populate_tags_list(all_tags)

        self.current_note_filter_row = row
        tag_object = json.loads(selected_tags)
        excluded: list[str] = tag_object["exclude"]
        included: list[str] = tag_object["include"]

        for tag in excluded:
            _row = self._find_row_with_tag(tag)
            _exclude_checkbox: QCheckBox = get_checkbox_widget(
                self.ui.tableWidget.cellWidget(_row, self._exclude_column)
            )
            _tag_item_exclude: QTableWidgetItem = get_table_item(
                self.ui.tableWidget.item(_row, self._tag_column)
            )
            _exclude_checkbox.setChecked(True)
            _tag_item_exclude.setForeground(QColor("white"))
            _tag_item_exclude.setBackground(QColor("red"))

        for tag in included:
            _row = self._find_row_with_tag(tag)
            _include_checkbox: QCheckBox = get_checkbox_widget(
                self.ui.tableWidget.cellWidget(_row, self._include_column)
            )
            _tag_item_include: QTableWidgetItem = get_table_item(
                self.ui.tableWidget.item(_row, self._tag_column)
            )
            _include_checkbox.setChecked(True)
            _tag_item_include.setForeground(QColor("white"))
            _tag_item_include.setBackground(QColor("green"))

        self.view_selected_tags()
        user_changed_check_state = True

    def _find_row_with_tag(self, tag: str) -> int:
        for _row in range(self.ui.tableWidget.rowCount()):
            _tag_item: QTableWidgetItem = get_table_item(
                self.ui.tableWidget.item(_row, self._tag_column)
            )
            if _tag_item.text() == tag:
                return _row

        # this should never be reached
        return -1

    def _populate_tags_list(self, all_tags: list[str]) -> None:
        assert mw is not None

        global user_changed_check_state
        user_changed_check_state = False

        for row, tag in enumerate(all_tags):
            tag_item: QTableWidgetItem = QTableWidgetItem(tag)

            exclude_checkbox: QCheckBox = QCheckBox()
            include_checkbox: QCheckBox = QCheckBox()

            exclude_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")
            include_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

            exclude_checkbox.stateChanged.connect(self.on_state_changed)
            include_checkbox.stateChanged.connect(self.on_state_changed)

            self.ui.tableWidget.setCellWidget(
                row, self._exclude_column, exclude_checkbox
            )
            self.ui.tableWidget.setCellWidget(
                row, self._include_column, include_checkbox
            )
            self.ui.tableWidget.setItem(row, self._tag_column, tag_item)

        user_changed_check_state = True

    def on_state_changed(self) -> None:
        global user_changed_check_state

        if not user_changed_check_state:
            return
        user_changed_check_state = False

        current_row: int = self.ui.tableWidget.currentRow()
        current_column: int = self.ui.tableWidget.currentColumn()

        if current_column == -1 or current_row == -1:
            # this can happen if the 'Unselect All' button is clicked
            return

        _exclude_checkbox: QCheckBox = get_checkbox_widget(
            self.ui.tableWidget.cellWidget(current_row, self._exclude_column)
        )
        _include_checkbox: QCheckBox = get_checkbox_widget(
            self.ui.tableWidget.cellWidget(current_row, self._include_column)
        )
        _tag_item: QTableWidgetItem = get_table_item(
            self.ui.tableWidget.item(current_row, self._tag_column)
        )

        if current_column == self._exclude_column:
            if _exclude_checkbox.isChecked():
                _include_checkbox.setChecked(False)
                _tag_item.setForeground(QColor("white"))
                _tag_item.setBackground(QColor("red"))
            else:
                # remove font and background colors by resetting the data roles
                _tag_item.setData(Qt.ItemDataRole.ForegroundRole, None)
                _tag_item.setData(Qt.ItemDataRole.BackgroundRole, None)
        elif current_column == self._include_column:
            if _include_checkbox.isChecked():
                _exclude_checkbox.setChecked(False)
                _tag_item.setForeground(QColor("white"))
                _tag_item.setBackground(QColor("green"))
            else:
                # remove font and background colors by resetting the data roles
                _tag_item.setData(Qt.ItemDataRole.ForegroundRole, None)
                _tag_item.setData(Qt.ItemDataRole.BackgroundRole, None)

        user_changed_check_state = True

    def _setup_buttons(self) -> None:
        style: Optional[QStyle] = self.style()
        assert style is not None

        apply_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        self.ui.applyButton.setIcon(apply_icon)

        self.ui.unselectAllButton.setAutoDefault(False)
        self.ui.applyButton.setAutoDefault(False)
        self.ui.viewAllTagsPushButton.setAutoDefault(False)
        self.ui.viewSelectedTagsPushButton.setAutoDefault(False)

        self.ui.unselectAllButton.clicked.connect(self._unselect_all_items)
        self.ui.applyButton.clicked.connect(self._save_selected_tags)
        self.ui.viewAllTagsPushButton.clicked.connect(self.view_all_tags)
        self.ui.viewSelectedTagsPushButton.clicked.connect(self.view_selected_tags)

    def view_selected_tags(self) -> None:
        for _row in range(self.ui.tableWidget.rowCount()):
            _exclude_checkbox: QCheckBox = get_checkbox_widget(
                self.ui.tableWidget.cellWidget(_row, self._exclude_column)
            )
            _include_checkbox: QCheckBox = get_checkbox_widget(
                self.ui.tableWidget.cellWidget(_row, self._include_column)
            )

            if _exclude_checkbox.isChecked() or _include_checkbox.isChecked():
                self.ui.tableWidget.showRow(_row)
            else:
                self.ui.tableWidget.hideRow(_row)

    def view_all_tags(self) -> None:
        for _row in range(self.ui.tableWidget.rowCount()):
            self.ui.tableWidget.showRow(_row)

    def _unselect_all_items(self) -> None:
        title = "Confirmation"
        text = "Are you sure you want to unselect all tags?"
        answer = show_warning_box(title, text, parent=self)

        if answer != QMessageBox.StandardButton.Yes:
            return

        global user_changed_check_state
        user_changed_check_state = False

        for _row in range(self.ui.tableWidget.rowCount()):
            _exclude_checkbox: QCheckBox = get_checkbox_widget(
                self.ui.tableWidget.cellWidget(_row, self._exclude_column)
            )
            _include_checkbox: QCheckBox = get_checkbox_widget(
                self.ui.tableWidget.cellWidget(_row, self._include_column)
            )
            _tag_item: QTableWidgetItem = get_table_item(
                self.ui.tableWidget.item(_row, self._tag_column)
            )
            _exclude_checkbox.setChecked(False)
            _include_checkbox.setChecked(False)

            # remove font and background colors by resetting the data roles
            _tag_item.setData(Qt.ItemDataRole.ForegroundRole, None)
            _tag_item.setData(Qt.ItemDataRole.BackgroundRole, None)

        user_changed_check_state = True

    def _save_selected_tags(self) -> None:
        excluded_tags = []
        included_tags = []

        for _row in range(self.ui.tableWidget.rowCount()):
            _exclude_checkbox: QCheckBox = get_checkbox_widget(
                self.ui.tableWidget.cellWidget(_row, self._exclude_column)
            )
            _include_checkbox: QCheckBox = get_checkbox_widget(
                self.ui.tableWidget.cellWidget(_row, self._include_column)
            )
            _tag_item: QTableWidgetItem = get_table_item(
                self.ui.tableWidget.item(_row, self._tag_column)
            )

            if _exclude_checkbox.isChecked():
                excluded_tags.append(_tag_item.text())
            elif _include_checkbox.isChecked():
                included_tags.append(_tag_item.text())

        tags_object = {"exclude": excluded_tags, "include": included_tags}
        self.selected_tags = json.dumps(tags_object)
        self.accept()

    def _on_search(self) -> None:
        search_text: str = self.ui.searchLineEdit.text()

        try:
            re.compile(search_text)
        except re.error as error:
            show_error_box(title="Regex Error", body=f"{error}", parent=self)
            return

        for _row in range(self.ui.tableWidget.rowCount()):
            tag_item: QTableWidgetItem = get_table_item(
                self.ui.tableWidget.item(_row, self._tag_column)
            )

            _match: Optional[Match[str]] = re.search(search_text, tag_item.text())
            if _match:
                self.ui.tableWidget.showRow(_row)
            else:
                self.ui.tableWidget.hideRow(_row)

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.close()
        aqt.dialogs.markClosed(ankimorphs_constants.TAG_SELECTOR_DIALOG_NAME)
        callback()
