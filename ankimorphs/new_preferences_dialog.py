import pprint
from functools import partial

from anki.models import FieldDict, NotetypeDict
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

from ankimorphs.config import get_config, update_configs
from ankimorphs.morphemizer import get_all_morphemizers
from ankimorphs.recalc import get_included_mids
from ankimorphs.ui.preferences_dialog_ui import Ui_Dialog


class PreferencesDialog(QDialog):
    """
    The UI comes from ankimorphs/ui/preferences_dialog.ui which is used in Qt Designer,
    which is then converted to ankimorphs/ui/preferences_dialog_ui.py,
    which is then imported here.

    Here we make the final adjustments that can't be made (or are hard to make) in
    the Qt Designer, like setting up tables and buttons.

    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.models = None
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setup_am_table()
        self.setup_buttons()

        # TODO MAKE EXTRA FIELDS A TABLE WITH COMBOBOXES

    def setup_buttons(self):
        self.ui.save_button.clicked.connect(self.save_to_config)
        self.ui.cancel_button.clicked.connect(self.close)

    def save_to_config(self):
        update_configs({"whatisthis": True})

    def setup_am_table(self):
        self.ui.tableWidget.setColumnWidth(3, 200)
        # self.ui.tableWidget.setColumnWidth(5, 75)  # modify-column
        self.ui.tableWidget.setRowCount(2)
        self.ui.tableWidget.setRowHeight(1, 50)
        self.ui.tableWidget.alternatingRowColors()
        # self.ui.horizontalLayout_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.models = mw.col.models.all_names_and_ids()

        for row, am_filter in enumerate(get_config("filters")):
            note_type_cbox = QComboBox(self.ui.tableWidget)
            note_type_cbox.addItems([model.name for model in self.models])
            note_type_cbox.setCurrentIndex(2)

            current_model_id = self.models[note_type_cbox.currentIndex()].id

            note_type = mw.col.models.get(current_model_id)

            # note_type: NotetypeDict = mw.col.models.get(note_type_cbox.currentIndex())
            # print(f"note_type: {note_type}")
            fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(
                note_type
            )

            field_cbox = QComboBox(self.ui.tableWidget)
            field_cbox.addItems(fields)

            note_type_cbox.currentIndexChanged.connect(
                partial(self.update_fields_cbox, field_cbox, note_type_cbox)
            )

            morphemizer_cbox = QComboBox(self.ui.tableWidget)
            morphemizers = get_all_morphemizers()
            morphemizers = [mizer.get_description() for mizer in morphemizers]
            morphemizer_cbox.addItems(morphemizers)

            read_checkbox = QCheckBox()
            read_checkbox.setChecked(am_filter["read"])
            read_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

            modify_checkbox = QCheckBox()
            modify_checkbox.setChecked(am_filter["read"])
            modify_checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")

            tags = ", ".join(am_filter["tags"])

            field_item = QTableWidgetItem(am_filter["field"])
            field_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.ui.tableWidget.setCellWidget(row, 0, note_type_cbox)
            self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(tags))
            self.ui.tableWidget.setCellWidget(row, 2, field_cbox)
            self.ui.tableWidget.setCellWidget(row, 3, morphemizer_cbox)
            self.ui.tableWidget.setCellWidget(row, 4, read_checkbox)
            self.ui.tableWidget.setCellWidget(row, 5, modify_checkbox)

    def update_fields_cbox(self, field_cbox, note_type_cbox):
        current_model_id = self.models[note_type_cbox.currentIndex()].id
        note_type = mw.col.models.get(current_model_id)
        fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)
        field_cbox.clear()
        field_cbox.addItems(fields)


def main():
    mw.ankimorphs_preferences_dialog = PreferencesDialog(mw)
    mw.ankimorphs_preferences_dialog.exec()
