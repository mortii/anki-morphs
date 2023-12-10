from collections.abc import Iterable
from typing import Optional

from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QComboBox,
    QRadioButton,
    QTableWidgetItem,
    QWidget,
)


def get_combobox_widget(widget: Optional[QWidget]) -> QComboBox:
    assert isinstance(widget, QComboBox)
    return widget


def get_checkbox_widget(widget: Optional[QWidget]) -> QCheckBox:
    assert isinstance(widget, QCheckBox)
    return widget


def get_radiobutton_widget(widget: Optional[QWidget]) -> QRadioButton:
    assert isinstance(widget, QRadioButton)
    return widget


def get_table_item(item: Optional[QTableWidgetItem]) -> QTableWidgetItem:
    assert isinstance(item, QTableWidgetItem)
    return item


def get_combobox_index(items: Iterable[str], filter_field: str) -> Optional[int]:
    for index, field in enumerate(items):
        if field == filter_field:
            return index
    return None
