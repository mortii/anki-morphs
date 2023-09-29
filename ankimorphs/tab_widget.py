from aqt import mw
from aqt.qt import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QStandardItem,
    QStandardItemModel,
    Qt,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import tooltip

from ankimorphs.morphemizer import get_all_morphemizers
from ankimorphs.preferences import get_preference, update_preferences
from ankimorphs.ui import MorphemizerComboBox
from ankimorphs.ui.tab_widget_ui import Ui_Form


def main():
    mw.ankimorphs_preferences = Ui_Form()
    mw.ankimorphs_preferences.show()
