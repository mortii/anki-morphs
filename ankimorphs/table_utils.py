from collections.abc import Iterable
from typing import Any, Optional

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
