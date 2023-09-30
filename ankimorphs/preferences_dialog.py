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

from ankimorphs.config import get_config, update_configs
from ankimorphs.morphemizer import get_all_morphemizers

# from ankimorphs.ui import MorphemizerComboBox


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.bool_option_list = None
        self.general_tab_widget = None
        self.checkbox_set_not_required_tags = None
        self.tag_entry_list = None
        self.tags_group_box = None
        self.field_entry_list = None
        self.extra_fields_tab_widget = None
        self.down = None
        self.up = None
        self.delete = None
        self.clone = None
        self.table_view = None
        self.table_model = None
        self.note_filter_tab_widget = None
        self.setModal(True)
        self.row_gui = []
        self.resize(950, 600)

        self.setWindowTitle("AnkiMorph Preferences")
        self.vbox = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        self.vbox.addWidget(self.tab_widget)

        self.create_note_filter_tab()
        self.create_extra_fields_tab()
        self.create_tags_tab()
        self.create_buttons()
        self.create_general_tab()

        self.setLayout(self.vbox)

    def create_note_filter_tab(self):
        self.note_filter_tab_widget = QWidget()
        self.tab_widget.addTab(self.note_filter_tab_widget, "Note Filter")
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

        row_data = get_config("Filter")
        self.table_model.setRowCount(len(row_data))
        self.row_gui = []
        for i, row in enumerate(row_data):
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

        self.clone = make_button("Clone", self.on_clone, hbox)
        self.delete = make_button("Delete", self.on_delete, hbox)
        self.up = make_button("Up", self.on_up, hbox)
        self.down = make_button("Down", self.on_down, hbox)

    def create_extra_fields_tab(self):
        self.extra_fields_tab_widget = QWidget()
        self.tab_widget.addTab(self.extra_fields_tab_widget, "Extra Fields")
        vbox = QVBoxLayout()
        self.extra_fields_tab_widget.setLayout(vbox)
        vbox.setContentsMargins(0, 20, 0, 0)

        label = QLabel(
            """
            This addon will attempt to change the data in the following fields. 
            Every field that has a (*) is REQUIRED IN EVERY NOTE for MorphMan to work correctly. 
            The other fields are optional. Hover your mouse over text entries to see tooltip info.
            """
        )
        label.setWordWrap(True)
        vbox.addWidget(label)
        vbox.addSpacing(50)

        grid = QGridLayout()
        vbox.addLayout(grid)
        number_of_columns = 2
        fields_list = [
            (
                "Focus morph (*):",
                "Field_FocusMorph",
                "Stores the unknown morpheme for sentences with one unmature word.\nGets cleared as soon as all works are mature.",
            ),
            (
                "MorphMan Index:",
                "Field_MorphManIndex",
                "Difficulty of card. This will be set to `due` time of card.",
            ),
            ("Unmatures", "Field_Unmatures", "Comma-separated list of unmature words."),
            (
                "Unmatures count:",
                "Field_UnmatureMorphCount",
                "Number of unmature words on this note.",
            ),
            (
                "Unknowns:",
                "Field_Unknowns",
                "Comma-separated list of unknown morphemes.",
            ),
            (
                "Unknown count:",
                "Field_UnknownMorphCount",
                "Number of unknown morphemes on this note.",
            ),
            (
                "Unknown frequency:",
                "Field_UnknownFreq",
                "Average of how many times the unknowns appear in your collection.",
            ),
            (
                "Focus morph POS:",
                "Field_FocusMorphPos",
                "The part of speech of the focus morph",
            ),
        ]
        self.field_entry_list = []
        for i, (name, key, tooltipInfo) in enumerate(fields_list):
            entry = QLineEdit(get_config(key))
            entry.setToolTip(tooltipInfo)
            self.field_entry_list.append((key, entry))

            grid.addWidget(
                QLabel(name), i // number_of_columns, (i % number_of_columns) * 2 + 0
            )
            grid.addWidget(
                entry, i // number_of_columns, (i % number_of_columns) * 2 + 1
            )

        vbox.addStretch()

    def create_tags_tab(self):
        self.tags_group_box = QGroupBox("Tags")
        self.tab_widget.addTab(self.tags_group_box, "Tags")
        vbox = QVBoxLayout()
        self.tags_group_box.setLayout(vbox)
        vbox.setContentsMargins(0, 20, 0, 0)

        label = QLabel(
            """
            This addon will add and delete following tags from your matched notes. Hover your mouse over text entries to see tooltip info.
            """
        )
        label.setWordWrap(True)
        vbox.addWidget(label)
        vbox.addSpacing(50)

        grid = QGridLayout()
        vbox.addLayout(grid)
        tag_list = [
            (
                "Vocab note:",
                "Tag_Vocab",
                "Note that is optimal to learn (one unknown word.)",
            ),
            (
                "Compehension note:",
                "Tag_Comprehension",
                "Note that only has mature words (optimal for sentence learning).",
            ),
            (
                "Fresh vocab note:",
                "Tag_Fresh",
                "Note that does not contain unknown words, but one or\nmore unmature (card with recently learned morphmes).",
            ),
            ("Not ready:", "Tag_NotReady", "Note that has two or more unknown words."),
            (
                "Already known:",
                "Tag_AlreadyKnown",
                "You can add this tag to a note.\nAfter a recalc of the database, all in this sentence words are marked as known.\nPress 'K' while reviewing to tag current card.",
            ),
            ("Priority:", "Tag_Priority", "Morpheme is in priority.db."),
            ("Too Short:", "Tag_TooShort", "Sentence is too short."),
            ("Too Long:", "Tag_TooLong", "Sentence is too long."),
            ("Frequency:", "Tag_Frequency", "Morpheme is in frequency.txt"),
        ]
        self.tag_entry_list = []
        number_of_columns = 2
        for i, (name, key, tooltipInfo) in enumerate(tag_list):
            entry = QLineEdit(get_config(key))
            entry.setToolTip(tooltipInfo)
            self.tag_entry_list.append((key, entry))

            grid.addWidget(
                QLabel(name), i // number_of_columns, (i % number_of_columns) * 2 + 0
            )
            grid.addWidget(
                entry, i // number_of_columns, (i % number_of_columns) * 2 + 1
            )

        vbox.addSpacing(50)

        self.checkbox_set_not_required_tags = QCheckBox("Add tags even if not required")
        self.checkbox_set_not_required_tags.setCheckState(
            Qt.CheckState.Checked
            if get_config("Option_SetNotRequiredTags")
            else Qt.CheckState.Unchecked
        )
        vbox.addWidget(self.checkbox_set_not_required_tags)

        vbox.addStretch()

    def create_general_tab(self):
        self.general_tab_widget = QGroupBox()
        self.tab_widget.addTab(self.general_tab_widget, "General")
        vbox = QVBoxLayout()
        self.general_tab_widget.setLayout(vbox)
        vbox.setContentsMargins(10, 10, 10, 10)

        hbox = QHBoxLayout()
        vbox.addLayout(hbox)

        reviews_group = QGroupBox("Review Preferences")
        hbox.addWidget(reviews_group)
        reviews_grid = QVBoxLayout()
        reviews_group.setLayout(reviews_grid)

        parsing_group = QGroupBox("Parsing Preferences")
        hbox.addWidget(parsing_group)
        parsing_grid = QVBoxLayout()
        parsing_group.setLayout(parsing_grid)

        label = QLabel(
            "MorphMan will reorder the cards so that the easiest cards are at the front. To avoid getting "
            "new cards that are too easy, MorphMan will skip certain new cards. You can customize the skip "
            "behavior here:"
        )
        label.setWordWrap(True)
        reviews_grid.addWidget(label)

        option_list = [
            (
                reviews_grid,
                "Skip comprehension cards",
                "Option_SkipComprehensionCards",
                "Note that only has mature words (optimal for sentence learning but not for acquiring new vocabulary).",
            ),
            (
                reviews_grid,
                "Skip cards with fresh vocabulary",
                "Option_SkipFreshVocabCards",
                "Note that does not contain unknown words, but one or more unmature (card with recently learned morphmes).\n"
                "Enable to skip to first card that has unknown vocabulary.",
            ),
            (
                reviews_grid,
                "Skip card if focus morph was already seen today",
                "Option_SkipFocusMorphSeenToday",
                "This improves the 'new cards'-queue without having to recalculate the databases.",
            ),
            (
                reviews_grid,
                "Always prioritize cards with morphs in the frequency list",
                "Option_AlwaysPrioritizeFrequencyMorphs",
                "This setting makes cards with morphemes in your frequency.txt or priority.db show first, even if they're not i+1.",
            ),
            (
                parsing_grid,
                "Treat proper nouns as known",
                "Option_ProperNounsAlreadyKnown",
                "Treat proper nouns as already known when scoring cards (currently only works for Japanese).",
            ),
            (
                parsing_grid,
                "Ignore grammar position",
                "Option_IgnoreGrammarPosition",
                "Use this option to ignore morpheme grammar types (noun, verb, helper, etc.).",
            ),
            (
                parsing_grid,
                "Ignore suspended leeches",
                "Option_IgnoreSuspendedLeeches",
                "Ignore cards that are suspended and have the tag 'leech'.",
            ),
            (
                parsing_grid,
                "Ignore everything contained within [ ] brackets",
                "Option_IgnoreBracketContents",
                "Use this option to ignore content such as furigana readings and pitch.",
            ),
            (
                parsing_grid,
                "Ignore everything contained within ( ) brackets",
                "Option_IgnoreSlimRoundBracketContents",
                "Use this option to ignore content such as character names and readings in scripts.",
            ),
            (
                parsing_grid,
                "Ignore everything contained within Japanese wide （ ） brackets",
                "Option_IgnoreRoundBracketContents",
                "Use this option to ignore content such as character names and readings in Japanese scripts.",
            ),
        ]

        self.bool_option_list = []
        for i, (layout, name, key, tooltipInfo) in enumerate(option_list):
            check_box = QCheckBox(name)
            check_box.setCheckState(
                Qt.CheckState.Checked if get_config(key) else Qt.CheckState.Unchecked
            )
            check_box.setToolTip(tooltipInfo)
            check_box.setMinimumSize(0, 30)
            self.bool_option_list.append((key, check_box))
            layout.addWidget(check_box)

        reviews_grid.addStretch()
        parsing_grid.addStretch()
        vbox.addStretch()

    def create_buttons(self):
        hbox = QHBoxLayout()
        self.vbox.addLayout(hbox)
        button_cancel = QPushButton("&Cancel")
        hbox.addWidget(button_cancel, 1, Qt.AlignmentFlag.AlignRight)
        button_cancel.setMaximumWidth(150)
        button_cancel.clicked.connect(self.on_cancel)

        button_okay = QPushButton("&Apply")
        hbox.addWidget(button_okay)
        button_okay.setMaximumWidth(150)
        button_okay.clicked.connect(self.on_okay)

    # see preferences.jcfg_default()['Filter'] for type of data
    def set_table_row(self, row_index, data):
        assert row_index >= 0, "Negative row numbers? Really?"
        assert (
            len(self.row_gui) >= row_index
        ), "Row can't be appended because it would leave an empty row"

        row_gui = {}

        model_combo_box = QComboBox()
        active = 0
        for i, model in enumerate(mw.col.models.all_names()):
            if model == data["Type"]:
                active = i + 1
            model_combo_box.addItem(model)
        model_combo_box.setCurrentIndex(active)

        morphemizer_combo_box = MorphemizerComboBox()
        morphemizer_combo_box.set_morphemizers(get_all_morphemizers())
        morphemizer_combo_box.set_current_by_name(data["Morphemizer"])

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
        row_gui["tagsEntry"] = QLineEdit(", ".join(data["Tags"]))
        row_gui["fieldsEntry"] = QLineEdit(", ".join(data["Fields"]))
        row_gui["morphemizerComboBox"] = morphemizer_combo_box
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

    def row_index_to_filter(self, row_index):
        return self.row_gui_to_filter(self.row_gui[row_index])

    @staticmethod
    def row_gui_to_filter(row_gui):
        _filter = {}

        if row_gui["modelComboBox"].currentIndex() == 0:
            _filter["Type"] = None  # no filter "All note types"
        else:
            _filter["Type"] = row_gui["modelComboBox"].currentText()

        _filter["Tags"] = [x for x in row_gui["tagsEntry"].text().split(", ") if x]
        _filter["Fields"] = [x for x in row_gui["fieldsEntry"].text().split(", ") if x]

        _filter["Morphemizer"] = row_gui["morphemizerComboBox"].get_current().get_name()
        _filter["Read"] = (
            row_gui["readCheckBox"].checkState() != Qt.CheckState.Unchecked
        )
        _filter["Modify"] = (
            row_gui["modifyCheckBox"].checkState() != Qt.CheckState.Unchecked
        )

        return _filter

    def read_config_from_gui(self):
        cfg = {}
        for key, entry in self.field_entry_list:
            cfg[key] = entry.text()
        for key, entry in self.tag_entry_list:
            cfg[key] = entry.text()
        for key, checkBox in self.bool_option_list:
            cfg[key] = checkBox.checkState() == Qt.CheckState.Checked

        cfg["Filter"] = []
        for i, rowGui in enumerate(self.row_gui):
            cfg["Filter"].append(self.row_gui_to_filter(rowGui))

        cfg["Option_SetNotRequiredTags"] = (
            self.checkbox_set_not_required_tags.checkState() != Qt.CheckState.Unchecked
        )

        return cfg

    def on_cancel(self):
        self.close()

    def on_okay(self):
        update_configs(self.read_config_from_gui())
        self.close()
        tooltip(_("Please recalculate your database to avoid unexpected behaviour."))

    def get_current_row(self):
        indexes = self.table_view.selectedIndexes()
        return 0 if len(indexes) == 0 else indexes[0].row()

    def append_row_data(self, data):
        self.table_model.setRowCount(len(self.row_gui) + 1)
        self.set_table_row(len(self.row_gui), data)

    def on_clone(self):
        row = self.get_current_row()
        data = self.row_index_to_filter(row)
        self.append_row_data(data)

    def on_delete(self):
        # do not allow to delete the last row
        if len(self.row_gui) == 1:
            return
        row_to_delete = self.get_current_row()
        self.table_model.removeRow(row_to_delete)
        self.row_gui.pop(row_to_delete)

    def move_row_up(self, row):
        # type: (int) -> None
        if not 0 < row < len(self.row_gui):  #
            return

        data1 = self.row_index_to_filter(row - 1)
        data2 = self.row_index_to_filter(row - 0)
        self.set_table_row(row - 1, data2)
        self.set_table_row(row - 0, data1)

    def on_up(self):
        row = self.get_current_row()
        self.move_row_up(row)
        self.table_view.selectRow(row - 1)

    def on_down(self):
        # moving a row down means moving the next row up
        row = self.get_current_row()
        self.move_row_up(row + 1)
        self.table_view.selectRow(row + 1)


def make_button(text, _function, parent):
    _btn = QPushButton(text)
    _btn.clicked.connect(_function)
    parent.addWidget(_btn)
    return _btn


def main():
    mw.ankimorphs_preferences = PreferencesDialog(mw)
    mw.ankimorphs_preferences.show()
