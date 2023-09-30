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
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import tooltip

from ankimorphs.morphemizer import get_all_morphemizers
from ankimorphs.preferences import get_preference, update_preferences
from ankimorphs.ui.preferences_dialog_ui import Ui_Dialog


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setup_am_table()
        self.setup_buttons()

    def setup_buttons(self):
        self.ui.save_button.clicked.connect(self.save_to_config)
        self.ui.cancel_button.clicked.connect(self.close)

    def save_to_config(self):
        update_preferences({"whatisthis": True})

    def setup_am_table(self):
        self.ui.tableWidget.setColumnWidth(3, 200)
        # self.table_model = QStandardItemModel(0, 6)
        # self.table_view = QTableView()
        self.ui.tableWidget.setRowCount(2)
        self.ui.tableWidget.setRowHeight(1, 50)
        self.ui.tableWidget.alternatingRowColors()

        for row, am_filter in enumerate(get_preference("filters")):
            note_type_cbox = QComboBox(self.ui.tableWidget)
            note_type_cbox.addItems(mw.col.models.all_names())

            # model_combo_box.setCurrentIndex(active)

            morphemizer_cbox = QComboBox(self.ui.tableWidget)

            mizers = get_all_morphemizers()
            mizers = [mizer.get_description() for mizer in mizers]

            morphemizer_cbox.addItems(mizers)

            read_checkbox = QCheckBox()
            read_checkbox.setChecked(am_filter["read"])

            modify_checkbox = QCheckBox()
            modify_checkbox.setChecked(am_filter["read"])

            tags = ", ".join(am_filter["tags"])

            self.ui.tableWidget.setCellWidget(row, 0, note_type_cbox)
            self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(tags))
            self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(am_filter["field"]))
            self.ui.tableWidget.setCellWidget(row, 3, morphemizer_cbox)
            self.ui.tableWidget.setCellWidget(row, 4, read_checkbox)
            self.ui.tableWidget.setCellWidget(row, 5, modify_checkbox)


def main():
    mw.ankimorphs_preferences_dialog = PreferencesDialog(mw)
    mw.ankimorphs_preferences_dialog.exec()
