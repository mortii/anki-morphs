from __future__ import annotations

from typing import Any

from aqt.qt import (  # pylint:disable=no-name-in-module
    QCheckBox,
    QComboBox,
    QRadioButton,
    QTableWidgetItem,
    QWidget,
)

from . import ankimorphs_globals


def get_combobox_widget(widget: QWidget | None) -> QComboBox:
    assert isinstance(widget, QComboBox)
    return widget


def get_checkbox_widget(widget: QWidget | None) -> QCheckBox:
    assert isinstance(widget, QCheckBox)
    return widget


def get_radiobutton_widget(widget: QWidget | None) -> QRadioButton:
    assert isinstance(widget, QRadioButton)
    return widget


def get_table_item(item: QTableWidgetItem | None) -> QTableWidgetItem:
    assert isinstance(item, QTableWidgetItem)
    return item


def get_combobox_index(items: list[str], filter_field: str) -> int:
    """
    Returns the index if found, otherwise returns the index of the "(none)" option
    """
    index: int
    try:
        index = items.index(filter_field)
    except ValueError:
        index = items.index(ankimorphs_globals.NONE_OPTION)
    return index


class QTableWidgetIntegerItem(QTableWidgetItem):
    """
    Has to be used when sorting QTableWidget columns with integer values,
    otherwise the sorting happens by string value, which gives wrong results

    Read more here:
    https://linux.m2osw.com/sorting-any-numeric-column-qtablewidget
    """

    def __init__(self, value: int, *__args: Any) -> None:
        super().__init__(str(value))  # displayed in the table
        self.value = value

    def __lt__(self, *args: Any, **kwargs: Any) -> bool:
        other_object = args[0]
        assert isinstance(other_object, QTableWidgetIntegerItem)
        if self.value < other_object.value:
            return True
        return False


class QTableWidgetPercentItem(QTableWidgetItem):
    """
    Has to be used when sorting QTableWidget columns with percent values,
    otherwise the sorting happens by string value, which gives wrong results

    Read more here:
    https://linux.m2osw.com/sorting-any-numeric-column-qtablewidget
    """

    def __init__(self, number: float, *__args: Any) -> None:
        super().__init__(f"{number} %")  # displayed in the table
        self.number = number

    def __lt__(self, *args: Any, **kwargs: Any) -> bool:
        other_object = args[0]
        assert isinstance(other_object, QTableWidgetPercentItem)
        if self.number < other_object.number:
            return True
        return False
