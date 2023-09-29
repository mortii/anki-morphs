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

from ankimorphs.ui.preferences_dialog_ui import Ui_Dialog


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)


def main():
    mw.ankimorphs_preferences_dialog = PreferencesDialog(mw)
    mw.ankimorphs_preferences_dialog.exec()
