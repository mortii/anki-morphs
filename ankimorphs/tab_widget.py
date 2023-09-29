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
from ankimorphs.ui.tab_widget_ui import Ui_Dialog


class AnalyzerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.mw = parent
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)


def main():
    mw.ankimorphs_preferences = AnalyzerDialog(mw)
    mw.ankimorphs_preferences.exec()
