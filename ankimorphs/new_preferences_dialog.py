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

from ankimorphs.preferences import get_preference, update_preferences
from ankimorphs.ui.preferences_dialog_ui import Ui_Dialog


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setup_table()

    def setup_table(self):
        # vbox = QVBoxLayout()
        # vbox.setContentsMargins(0, 20, 0, 0)
        # self.ui.tab.setLayout(vbox)

        self.note_filter_tab_widget = QWidget()
        self.ui.tabWidget.addTab(self.note_filter_tab_widget, "Note Filter")
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 20, 0, 0)
        self.note_filter_tab_widget.setLayout(vbox)

        self.table_model = QStandardItemModel(0, 6)
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_model.setHeaderData(0, Qt.Orientation.Horizontal, "Note type")
        self.table_model.setHeaderData(1, Qt.Orientation.Horizontal, "Tags")
        self.table_model.setHeaderData(2, Qt.Orientation.Horizontal, "Field")
        self.table_model.setHeaderData(3, Qt.Orientation.Horizontal, "Morphemizer")
        self.table_model.setHeaderData(4, Qt.Orientation.Horizontal, "Read")
        self.table_model.setHeaderData(5, Qt.Orientation.Horizontal, "Modify")

        row_data = get_preference("filters")
        self.table_model.setRowCount(len(row_data))
        self.row_gui = []
        for i, row in enumerate(row_data):
            print(f"row: {row}")
            self.set_table_row(i, row)

        label = QLabel(
            """
            Any card that has the given `Note type` and all of the given `Tags` will have its `Fields` analyzed with the specified `Morphemizer`.
            'A morphemizer specifies how words are extraced from a sentence. `Fields` and `Tags` are both comma-separated lists (e.x: "tag1, tag2, tag3"). 
            If `Tags` is empty, there are no tag restrictions.
            If `Modify` is deactivated, the note will only be analyzed.\n\nIf a note is matched multple times, only the first filter in this list will be used.
            """
        )
        label.setWordWrap(True)
        vbox.addWidget(label)
        vbox.addSpacing(20)
        vbox.addWidget(self.table_view)

        hbox = QHBoxLayout()
        vbox.addLayout(hbox)

    def set_table_row(self, row_index, data):
        assert row_index >= 0, "Negative row numbers? Really?"
        assert (
            len(self.row_gui) >= row_index
        ), "Row can't be appended because it would leave an empty row"

        row_gui = {}

        print(f"Data: {data}")

        model_combo_box = QComboBox()
        active = 0
        for i, model in enumerate(mw.col.models.all_names()):
            if model == data["type"]:
                active = i + 1
            model_combo_box.addItem(model)
        model_combo_box.setCurrentIndex(active)

        # morphemizer_combo_box = MorphemizerComboBox()
        # morphemizer_combo_box.set_morphemizers(get_all_morphemizers())
        # morphemizer_combo_box.set_current_by_name(data["Morphemizer"])

        read_item = QStandardItem()
        read_item.setCheckable(True)
        # read_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
        # print(f"alignment: {read_item.textAlignment()}")
        read_item.setCheckState(
            Qt.CheckState.Checked if data.get("Read", True) else Qt.CheckState.Unchecked
        )

        modify_item = QStandardItem()
        modify_item.setCheckable(True)
        modify_item.setCheckState(
            Qt.CheckState.Checked
            if data.get("Modify", True)
            else Qt.CheckState.Unchecked
        )

        row_gui["modelComboBox"] = model_combo_box
        row_gui["tagsEntry"] = QLineEdit(", ".join(data["tags"]))
        row_gui["fieldsEntry"] = QLineEdit(", ".join(data["field"]))
        row_gui["morphemizerComboBox"] = model_combo_box
        row_gui["readCheckBox"] = read_item
        row_gui["modifyCheckBox"] = modify_item

        def set_column(col, widget):
            self.table_view.setIndexWidget(
                self.table_model.index(row_index, col), widget
            )

        set_column(0, row_gui["modelComboBox"])
        set_column(1, row_gui["tagsEntry"])
        set_column(2, row_gui["fieldsEntry"])
        set_column(3, row_gui["morphemizerComboBox"])
        self.table_model.setItem(row_index, 4, read_item)
        self.table_model.setItem(row_index, 5, modify_item)

        if len(self.row_gui) == row_index:
            self.row_gui.append(row_gui)
        else:
            self.row_gui[row_index] = row_gui


def main():
    mw.ankimorphs_preferences_dialog = PreferencesDialog(mw)
    mw.ankimorphs_preferences_dialog.exec()
